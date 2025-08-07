"""
Scraper untuk Mahkamah Agung RI dengan error handling yang comprehensive
Compatible dengan urllib3 2.0+ dan memiliki fallback strategies
Enhanced with debugging capabilities and content analysis
"""

import requests
import urllib3
import time
import random
import logging
import json
import os
import re
import zipfile
import mimetypes
from datetime import datetime
from typing import List, Dict, Optional, Union, Any, Tuple
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

# Import konfigurasi dan utilities
try:
    from config import *
    from utils import *
except ImportError:
    # Handle case when running from different directory
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from config import *
    from utils import *


class HTMLAnalyzer:
    """Analyze HTML content to understand structure and find potential selectors"""
    
    @staticmethod
    def analyze_html_structure(html_content: str, save_analysis: bool = True) -> Dict:
        """Analyze HTML structure and suggest possible selectors"""
        soup = BeautifulSoup(html_content, 'lxml')
        
        analysis = {
            'total_elements': len(soup.find_all()),
            'tables': [],
            'forms': [],
            'divs_with_classes': [],
            'potential_data_containers': [],
            'links': [],
            'scripts': [],
            'meta_info': {},
            'possible_selectors': []
        }
        
        # Analyze tables
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            analysis['tables'].append({
                'index': i,
                'rows': len(rows),
                'columns': len(rows[0].find_all(['td', 'th'])) if rows else 0,
                'classes': table.get('class', []),
                'id': table.get('id', ''),
                'sample_text': table.get_text(strip=True)[:100] if table else ''
            })
        
        # Analyze forms
        forms = soup.find_all('form')
        for i, form in enumerate(forms):
            analysis['forms'].append({
                'index': i,
                'action': form.get('action', ''),
                'method': form.get('method', ''),
                'inputs': len(form.find_all('input')),
                'classes': form.get('class', [])
            })
        
        # Analyze divs with classes
        divs = soup.find_all('div', class_=True)
        class_counts = {}
        for div in divs:
            classes = div.get('class', [])
            for cls in classes:
                class_counts[cls] = class_counts.get(cls, 0) + 1
        
        analysis['divs_with_classes'] = sorted(
            class_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:20]  # Top 20 most common classes
        
        # Look for potential data containers
        data_indicators = ['data', 'list', 'item', 'row', 'content', 'result', 'putusan', 'document']
        for indicator in data_indicators:
            elements = soup.find_all(attrs={'class': re.compile(indicator, re.I)})
            elements.extend(soup.find_all(attrs={'id': re.compile(indicator, re.I)}))
            
            if elements:
                analysis['potential_data_containers'].append({
                    'indicator': indicator,
                    'count': len(elements),
                    'sample_elements': [
                        {
                            'tag': elem.name,
                            'classes': elem.get('class', []),
                            'id': elem.get('id', ''),
                            'text_preview': elem.get_text(strip=True)[:100]
                        } for elem in elements[:3]
                    ]
                })
        
        # Analyze links
        links = soup.find_all('a', href=True)
        analysis['links'] = {
            'total': len(links),
            'internal': len([l for l in links if not l['href'].startswith('http')]),
            'external': len([l for l in links if l['href'].startswith('http')]),
            'sample_hrefs': [l['href'] for l in links[:10]]
        }
        
        # Analyze scripts
        scripts = soup.find_all('script')
        analysis['scripts'] = {
            'total': len(scripts),
            'external': len([s for s in scripts if s.get('src')]),
            'inline': len([s for s in scripts if not s.get('src')]),
            'ajax_indicators': []
        }
        
        # Check for AJAX indicators
        page_text = soup.get_text().lower()
        ajax_keywords = ['ajax', 'fetch', 'xmlhttprequest', 'api', 'json', 'async']
        for keyword in ajax_keywords:
            if keyword in page_text:
                analysis['scripts']['ajax_indicators'].append(keyword)
        
        # Meta information
        analysis['meta_info'] = {
            'title': soup.title.string if soup.title else '',
            'charset': soup.find('meta', {'charset': True}),
            'viewport': soup.find('meta', {'name': 'viewport'}),
            'generator': soup.find('meta', {'name': 'generator'})
        }
        
        # Generate possible selectors
        analysis['possible_selectors'] = HTMLAnalyzer._generate_selector_suggestions(soup)
        
        if save_analysis:
            HTMLAnalyzer._save_analysis(analysis)
        
        return analysis
    
    @staticmethod
    def _generate_selector_suggestions(soup: BeautifulSoup) -> List[Dict]:
        """Generate possible selector suggestions based on content analysis"""
        suggestions = []
        
        # Common patterns for court decisions
        decision_patterns = [
            # Table-based layouts
            {'type': 'table_rows', 'selector': 'table tr', 'description': 'All table rows'},
            {'type': 'table_rows', 'selector': 'table tbody tr', 'description': 'Table body rows'},
            {'type': 'table_data', 'selector': 'table td', 'description': 'Table cells'},
            
            # List-based layouts
            {'type': 'list_items', 'selector': 'ul li', 'description': 'Unordered list items'},
            {'type': 'list_items', 'selector': 'ol li', 'description': 'Ordered list items'},
            
            # Div-based layouts
            {'type': 'div_containers', 'selector': 'div[class*="putusan"]', 'description': 'Divs containing "putusan"'},
            {'type': 'div_containers', 'selector': 'div[class*="decision"]', 'description': 'Divs containing "decision"'},
            {'type': 'div_containers', 'selector': 'div[class*="item"]', 'description': 'Divs containing "item"'},
            {'type': 'div_containers', 'selector': 'div[class*="row"]', 'description': 'Divs containing "row"'},
            {'type': 'div_containers', 'selector': 'div[class*="list"]', 'description': 'Divs containing "list"'},
            
            # Article-based layouts
            {'type': 'article', 'selector': 'article', 'description': 'Article elements'},
            {'type': 'section', 'selector': 'section', 'description': 'Section elements'},
            
            # Card-based layouts
            {'type': 'cards', 'selector': 'div[class*="card"]', 'description': 'Card-style containers'},
            {'type': 'cards', 'selector': 'div[class*="box"]', 'description': 'Box-style containers'},
        ]
        
        for pattern in decision_patterns:
            elements = soup.select(pattern['selector'])
            if elements:
                suggestions.append({
                    **pattern,
                    'found_count': len(elements),
                    'sample_text': elements[0].get_text(strip=True)[:100] if elements else ''
                })
        
        return suggestions
    
    @staticmethod
    def _save_analysis(analysis: Dict):
        """Save HTML analysis to file"""
        try:
            analysis_dir = "logs/html_analysis"
            os.makedirs(analysis_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(analysis_dir, f"html_analysis_{timestamp}.json")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"📊 HTML analysis saved to: {filepath}")
            
        except Exception as e:
            print(f"❌ Failed to save HTML analysis: {e}")


class NetworkDebugger:
    """Debug network requests and responses"""
    
    @staticmethod
    def analyze_response(response: requests.Response, save_debug: bool = True) -> Dict:
        """Analyze HTTP response for debugging"""
        analysis = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'content_length': len(response.content),
            'content_type': response.headers.get('content-type', ''),
            'encoding': response.encoding,
            'url': response.url,
            'history': [r.url for r in response.history],
            'cookies': dict(response.cookies),
            'elapsed': str(response.elapsed),
            'content_analysis': {}
        }
        
        # Analyze content
        if response.content:
            content_text = response.text[:1000]  # First 1000 chars
            analysis['content_analysis'] = {
                'starts_with': content_text[:100],
                'contains_html': '<html' in content_text.lower(),
                'contains_json': content_text.strip().startswith('{'),
                'contains_xml': content_text.strip().startswith('<?xml'),
                'charset_declaration': 'charset=' in content_text,
                'javascript_present': '<script' in content_text.lower(),
                'form_present': '<form' in content_text.lower(),
                'table_present': '<table' in content_text.lower()
            }
        
        if save_debug:
            NetworkDebugger._save_response_debug(analysis, response)
        
        return analysis
    
    @staticmethod
    def _save_response_debug(analysis: Dict, response: requests.Response):
        """Save response debug information"""
        try:
            debug_dir = "logs/network_debug"
            os.makedirs(debug_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save analysis
            analysis_file = os.path.join(debug_dir, f"response_analysis_{timestamp}.json")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
            
            # Save raw response
            response_file = os.path.join(debug_dir, f"response_content_{timestamp}.html")
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"🔍 Network debug saved: {analysis_file}")
            
        except Exception as e:
            print(f"❌ Failed to save network debug: {e}")


class MahkamahAgungScraper:
    """
    Enhanced scraper with comprehensive debugging capabilities
    """
    
    def __init__(self, debug: bool = False, interactive_debug: bool = False):
        self.debug = debug
        self.interactive_debug = interactive_debug
        self.session = None
        self.driver = None
        self.scraped_data = []
        self.failed_urls = []
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'method_used': {},
            'errors': []
        }
        
        # Setup logging
        self._setup_logging()
        
        # Setup direktori
        setup_directories()
        
        # Enhanced debugging tools
        self.html_analyzer = HTMLAnalyzer()
        self.network_debugger = NetworkDebugger()
        
        # Initialize sessions
        self._setup_requests_session()
        
        # Add download directory
        self.download_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Download stats
        self.download_stats = {
            'pdf_downloads': 0,
            'zip_downloads': 0,
            'failed_downloads': 0,
            'total_size': 0
        }
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Ensure log directory exists
        os.makedirs(LOG_DIR, exist_ok=True)
        log_file = os.path.join(LOG_DIR, f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL),
            format=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
            # Set debug level for urllib3 and requests
            logging.getLogger("urllib3").setLevel(logging.DEBUG)
            logging.getLogger("requests").setLevel(logging.DEBUG)
        else:
            # Disable urllib3 warnings for cleaner output
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
    def _setup_requests_session(self):
        """Setup requests session dengan retry strategy yang modern"""
        self.session = requests.Session()
        
        # Modern retry strategy untuk urllib3 2.0+
        retry_strategy = Retry(
            total=MAX_RETRIES,
            status_forcelist=[429, 500, 502, 503, 504],
            # Menggunakan allowed_methods bukan method_whitelist (deprecated)
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
            raise_on_redirect=False,
            raise_on_status=False
        )
        
        # Setup adapter dengan retry strategy
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.logger.info("Requests session initialized with modern retry strategy")
        
    def _setup_selenium_driver(self) -> bool:
        """Setup selenium driver sebagai fallback"""
        try:
            chrome_options = Options()
            
            if SELENIUM_CONFIG['headless']:
                chrome_options.add_argument('--headless')
                
            chrome_options.add_argument(f'--window-size={SELENIUM_CONFIG["window_size"][0]},{SELENIUM_CONFIG["window_size"][1]}')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Set user agent
            chrome_options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
            
            # Install dan setup driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(SELENIUM_CONFIG['page_load_timeout'])
            self.driver.implicitly_wait(SELENIUM_CONFIG['implicit_wait'])
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("Selenium driver initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup Selenium driver: {e}")
            return False
    
    def _rotate_user_agent(self):
        """Rotate user agent untuk menghindari detection"""
        if self.session:
            self.session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
            
    def _random_delay(self, delay_range: tuple = DELAY_RANGE):
        """Add random delay between requests"""
        delay = random.uniform(delay_range[0], delay_range[1])
        time.sleep(delay)
        
    def _handle_rate_limit(self, response: requests.Response) -> bool:
        """Handle rate limiting dengan exponential backoff"""
        if response.status_code == 429:
            self.logger.warning("Rate limited detected, implementing backoff strategy")
            
            # Check for Retry-After header
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    wait_time = int(retry_after)
                    self.logger.info(f"Retry-After header found, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    return True
                except ValueError:
                    pass
            
            # Exponential backoff
            for attempt in range(3):
                wait_time = random.uniform(
                    RATE_LIMIT_DELAY_RANGE[0] * (2 ** attempt),
                    RATE_LIMIT_DELAY_RANGE[1] * (2 ** attempt)
                )
                self.logger.info(f"Rate limit backoff attempt {attempt + 1}, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                
                # Rotate user agent
                self._rotate_user_agent()
                
                # Retry request
                try:
                    retry_response = self.session.get(response.url, timeout=DEFAULT_TIMEOUT)
                    if retry_response.status_code != 429:
                        return True
                except Exception as e:
                    self.logger.warning(f"Retry attempt {attempt + 1} failed: {e}")
                    
            return False
        return True
    
    def get_page_content(self, url: str, method: str = 'requests') -> Optional[str]:
        """
        Get page content dengan multiple fallback methods
        
        Args:
            url: URL to scrape
            method: 'requests', 'selenium', atau 'auto' untuk fallback otomatis
        
        Returns:
            HTML content atau None jika gagal
        """
        self.stats['total_requests'] += 1
        
        # Method 1: Requests
        if method in ['requests', 'auto']:
            try:
                content = self._get_content_requests(url)
                if content:
                    self.stats['successful_requests'] += 1
                    self.stats['method_used']['requests'] = self.stats['method_used'].get('requests', 0) + 1
                    return content
                elif method == 'requests':
                    self.stats['failed_requests'] += 1
                    return None
            except Exception as e:
                self.logger.warning(f"Requests method failed for {url}: {e}")
                if method == 'requests':
                    self.stats['failed_requests'] += 1
                    return None
        
        # Method 2: Selenium (fallback)
        if method in ['selenium', 'auto']:
            try:
                content = self._get_content_selenium(url)
                if content:
                    self.stats['successful_requests'] += 1
                    self.stats['method_used']['selenium'] = self.stats['method_used'].get('selenium', 0) + 1
                    return content
            except Exception as e:
                self.logger.warning(f"Selenium method failed for {url}: {e}")
        
        # All methods failed
        self.stats['failed_requests'] += 1
        self.failed_urls.append({
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'error': 'All methods failed'
        })
        return None
    
    def _get_content_requests(self, url: str) -> Optional[str]:
        """Enhanced get content with comprehensive debugging"""
        try:
            self.logger.debug(f"Attempting to fetch {url} using requests")
            
            # Random delay
            self._random_delay()
            
            # Rotate user agent occasionally
            if random.random() < 0.1:  # 10% chance
                self._rotate_user_agent()
            
            # Log request details
            self.logger.debug(f"Request headers: {dict(self.session.headers)}")
            
            response = self.session.get(
                url,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=True,
                verify=True
            )
            
            # Enhanced response analysis
            if self.debug:
                analysis = self.network_debugger.analyze_response(response)
                self.logger.debug(f"Response analysis: {analysis}")
                
                # Interactive debugging
                if self.interactive_debug:
                    self._interactive_response_debug(response, analysis)
            
            # Handle different status codes
            if response.status_code == 200:
                self.logger.debug(f"Successfully fetched {url}")
                
                # Enhanced content validation
                if not self._validate_response_content(response):
                    self.logger.warning(f"Response content validation failed for {url}")
                    return None
                
                # Save debug HTML with analysis
                if self.debug:
                    self._save_debug_html(url, response.text)
                    # Analyze HTML structure
                    html_analysis = self.html_analyzer.analyze_html_structure(response.text)
                    self.logger.debug(f"HTML analysis: Found {html_analysis['total_elements']} elements")
                
                return response.text
            
            elif response.status_code == 429:
                self.logger.warning(f"Rate limited for {url}")
                if self._handle_rate_limit(response):
                    # Retry after handling rate limit
                    retry_response = self.session.get(url, timeout=DEFAULT_TIMEOUT)
                    if retry_response.status_code == 200:
                        return retry_response.text
                
            elif response.status_code in [403, 406]:
                self.logger.warning(f"Access forbidden for {url}, might be blocked")
                raise Exception(f"Access forbidden (HTTP {response.status_code})")
                
            elif response.status_code >= 500:
                self.logger.warning(f"Server error for {url}: HTTP {response.status_code}")
                raise Exception(f"Server error (HTTP {response.status_code})")
                
            else:
                self.logger.warning(f"Unexpected status code {response.status_code} for {url}")
                raise Exception(f"HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout for {url}")
            raise Exception("Request timeout")
            
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"Connection error for {url}")
            raise Exception("Connection error")
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Request exception for {url}: {e}")
            raise Exception(f"Request exception: {e}")
            
        return None
    
    def _validate_response_content(self, response: requests.Response) -> bool:
        """Validate that response contains expected content"""
        content = response.text.lower()
        
        # Check for common error indicators
        error_indicators = [
            'error 404',
            'page not found',
            'access denied',
            'forbidden',
            'blocked',
            'captcha',
            'robot'
        ]
        
        for indicator in error_indicators:
            if indicator in content:
                self.logger.warning(f"Error indicator found in content: {indicator}")
                return False
        
        # Check for minimal content length
        if len(content) < 100:
            self.logger.warning(f"Content too short: {len(content)} characters")
            return False
        
        # Check for HTML structure
        if not any(tag in content for tag in ['<html', '<body', '<div', '<table']):
            self.logger.warning("No HTML structure found in content")
            return False
        
        return True
    
    def _interactive_response_debug(self, response: requests.Response, analysis: Dict):
        """Interactive debugging mode"""
        print("\n" + "="*50)
        print("🔍 INTERACTIVE DEBUG MODE")
        print("="*50)
        print(f"URL: {response.url}")
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"Content Length: {len(response.content)} bytes")
        print(f"Encoding: {response.encoding}")
        
        if response.history:
            print(f"Redirects: {len(response.history)}")
            for i, redirect in enumerate(response.history):
                print(f"  {i+1}. {redirect.url} -> {redirect.status_code}")
        
        print("\nContent Analysis:")
        for key, value in analysis['content_analysis'].items():
            print(f"  {key}: {value}")
        
        print("\nAvailable actions:")
        print("1. View response headers")
        print("2. View first 500 characters of content")
        print("3. Save full response to file")
        print("4. Analyze HTML structure")
        print("5. Test selectors")
        print("6. Continue")
        
        while True:
            try:
                choice = input("\nEnter choice (1-6): ").strip()
                
                if choice == '1':
                    print("\nResponse Headers:")
                    for key, value in response.headers.items():
                        print(f"  {key}: {value}")
                
                elif choice == '2':
                    print("\nFirst 500 characters:")
                    print("-" * 50)
                    print(response.text[:500])
                    print("-" * 50)
                
                elif choice == '3':
                    filename = f"debug_response_{int(time.time())}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"Response saved to: {filename}")
                
                elif choice == '4':
                    html_analysis = self.html_analyzer.analyze_html_structure(response.text)
                    print(f"\nHTML Analysis:")
                    print(f"  Total elements: {html_analysis['total_elements']}")
                    print(f"  Tables: {len(html_analysis['tables'])}")
                    print(f"  Forms: {len(html_analysis['forms'])}")
                    print(f"  Potential data containers: {len(html_analysis['potential_data_containers'])}")
                    
                    if html_analysis['possible_selectors']:
                        print("\nSuggested selectors:")
                        for selector in html_analysis['possible_selectors'][:5]:
                            print(f"  {selector['selector']} -> {selector['found_count']} elements")
                
                elif choice == '5':
                    self._test_selectors_interactive(response.text)
                
                elif choice == '6':
                    break
                
                else:
                    print("Invalid choice. Please enter 1-6.")
                    
            except KeyboardInterrupt:
                print("\nExiting interactive debug...")
                break
            except Exception as e:
                print(f"Error in interactive debug: {e}")
    
    def _test_selectors_interactive(self, html_content: str):
        """Test CSS selectors interactively"""
        soup = BeautifulSoup(html_content, 'lxml')
        
        print("\n🎯 SELECTOR TESTING MODE")
        print("Enter CSS selectors to test (or 'back' to return)")
        print("Examples: 'table tr', 'div.putusan', '#content', etc.")
        
        while True:
            try:
                selector = input("\nEnter selector: ").strip()
                
                if selector.lower() == 'back':
                    break
                
                if not selector:
                    continue
                
                elements = soup.select(selector)
                print(f"\nFound {len(elements)} elements with selector '{selector}'")
                
                if elements:
                    print("First 3 elements:")
                    for i, elem in enumerate(elements[:3]):
                        print(f"  {i+1}. Tag: {elem.name}")
                        print(f"     Classes: {elem.get('class', [])}")
                        print(f"     ID: {elem.get('id', 'None')}")
                        text_preview = elem.get_text(strip=True)[:100]
                        print(f"     Text: {text_preview}...")
                        print()
                
            except Exception as e:
                print(f"Error testing selector: {e}")
    
    def parse_putusan_list(self, html_content: str) -> List[Dict]:
        """Parse putusan list based on actual HTML structure from Mahkamah Agung"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            putusan_list = []
            
            # Based on the HTML structure, putusan data is in div.spost elements
            putusan_elements = soup.select('div.spost')
            
            if not putusan_elements:
                self.logger.warning("No putusan elements found with div.spost selector")
                # Try alternative selectors based on the HTML structure
                alternative_selectors = [
                    '#popular-post-list-sidebar div.spost',
                    '.spost',
                    'div[class*="spost"]'
                ]
                
                for selector in alternative_selectors:
                    putusan_elements = soup.select(selector)
                    if putusan_elements:
                        self.logger.info(f"Found {len(putusan_elements)} elements with selector: {selector}")
                        break
            
            if not putusan_elements:
                self.logger.warning("No putusan elements found with any selector")
                return []
            
            self.logger.info(f"Found {len(putusan_elements)} putusan elements")
            
            for element in putusan_elements:
                try:
                    putusan_data = self._extract_putusan_from_spost(element)
                    if putusan_data:
                        putusan_list.append(putusan_data)
                except Exception as e:
                    self.logger.warning(f"Error extracting data from element: {e}")
                    continue
            
            self.logger.info(f"Successfully parsed {len(putusan_list)} putusan records")
            return putusan_list
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML content: {e}")
            return []
    
    def _extract_putusan_from_spost(self, element) -> Optional[Dict]:
        """Extract putusan data from spost element based on actual HTML structure"""
        try:
            putusan_data = {}
            
            # Extract breadcrumb/category path
            small_divs = element.select('div.small')
            if small_divs:
                breadcrumb_text = small_divs[0].get_text(strip=True)
                putusan_data['breadcrumb'] = clean_text(breadcrumb_text)
                
                # Parse category from breadcrumb
                if 'Pengadilan' in breadcrumb_text:
                    parts = [part.strip() for part in breadcrumb_text.split('>')[-3:]]
                    if len(parts) >= 2:
                        putusan_data['pengadilan'] = clean_text(parts[0])
                        putusan_data['kategori'] = clean_text(parts[1])
                        if len(parts) >= 3:
                            putusan_data['sub_kategori'] = clean_text(parts[2])
            
            # Extract dates (Register, Putus, Upload)
            if len(small_divs) > 1:
                date_text = small_divs[1].get_text(strip=True)
                dates = self._parse_dates_from_text(date_text)
                putusan_data.update(dates)
            
            # Extract main title/link
            title_link = element.select('strong a')
            if title_link:
                putusan_data['title'] = clean_text(title_link[0].get_text(strip=True))
                putusan_data['link'] = normalize_url(title_link[0].get('href', ''), BASE_URL)
                
                # Extract nomor putusan from title
                nomor_match = re.search(r'Nomor\s+([^<\n]+)', putusan_data['title'])
                if nomor_match:
                    putusan_data['nomor'] = clean_text(nomor_match.group(1))
            
            # Extract case details
            case_info_divs = element.select('div')
            for div in case_info_divs:
                text = div.get_text(strip=True)
                if '—' in text and any(keyword in text for keyword in ['Tanggal', 'VS', 'vs']):
                    putusan_data['case_details'] = clean_text(text)
                    
                    # Extract parties
                    if ' VS ' in text or ' vs ' in text:
                        parts = re.split(r'\s+(?:VS|vs)\s+', text)
                        if len(parts) >= 2:
                            putusan_data['penggugat'] = clean_text(parts[0].split('—')[-1])
                            putusan_data['tergugat'] = clean_text(parts[1])
            
            # Extract view and download counts
            icon_elements = element.select('i.icon-eye, i.icon-download')
            for icon in icon_elements:
                next_strong = icon.find_next_sibling('strong')
                if next_strong:
                    count_text = next_strong.get_text(strip=True)
                    try:
                        count = int(count_text)
                        if 'icon-eye' in icon.get('class', []):
                            putusan_data['view_count'] = count
                        elif 'icon-download' in icon.get('class', []):
                            putusan_data['download_count'] = count
                    except ValueError:
                        pass
            
            # Check for final status
            if 'Berkekuatan Hukum Tetap' in element.get_text():
                putusan_data['status'] = 'Berkekuatan Hukum Tetap'
            
            # Check for unpublish status
            if 'Unpublish' in element.get_text():
                putusan_data['status'] = 'Unpublish'
            
            # Extract abstract if available
            abstract_div = element.select('div.putusan_container')
            if abstract_div:
                abstract_text = abstract_div[0].get_text(strip=True)
                if abstract_text:
                    putusan_data['abstract'] = clean_text(abstract_text)
            
            # Add metadata
            putusan_data['scraped_at'] = datetime.now().isoformat()
            putusan_data['source'] = 'mahkamahagung.go.id'
            
            return putusan_data if putusan_data else None
            
        except Exception as e:
            self.logger.debug(f"Error extracting putusan data: {e}")
            return None
    
    def _parse_dates_from_text(self, date_text: str) -> Dict:
        """Parse dates from text like 'Register : 17-04-2025 — Putus : 13-06-2025 — Upload : 06-08-2025'"""
        dates = {}
        
        # Patterns for different date types
        date_patterns = {
            'tanggal_register': r'Register\s*:\s*([0-9\-/]+)',
            'tanggal_putus': r'Putus\s*:\s*([0-9\-/]+)',
            'tanggal_upload': r'Upload\s*:\s*([0-9\-/]+)'
        }
        
        for field, pattern in date_patterns.items():
            match = re.search(pattern, date_text)
            if match:
                date_str = match.group(1)
                dates[field] = clean_text(date_str)
                
                # Try to parse and normalize date
                try:
                    parsed_date = self._parse_date_string(date_str)
                    if parsed_date:
                        dates[f'{field}_parsed'] = parsed_date.isoformat()
                except:
                    pass
        
        return dates
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        date_formats = [
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%d-%m-%y',
            '%d/%m/%y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def download_putusan_file(self, putusan_data: Dict, download_pdf: bool = True) -> Dict:
        """Download PDF/ZIP file for a putusan"""
        if 'link' not in putusan_data:
            self.logger.warning("No link found in putusan data")
            return putusan_data
        
        try:
            # Get the detailed page first
            detail_url = putusan_data['link']
            detail_content = self.get_page_content(detail_url)
            
            if not detail_content:
                self.logger.warning(f"Failed to get detail page: {detail_url}")
                return putusan_data
            
            # Parse detail page to find download links
            detail_soup = BeautifulSoup(detail_content, 'lxml')
            download_links = self._extract_download_links(detail_soup)
            
            if not download_links:
                self.logger.info(f"No download links found for {putusan_data.get('nomor', 'unknown')}")
                return putusan_data
            
            # Download files
            for link_info in download_links:
                if download_pdf or link_info['type'] != 'pdf':
                    file_path = self._download_file(link_info, putusan_data)
                    if file_path:
                        if 'downloaded_files' not in putusan_data:
                            putusan_data['downloaded_files'] = []
                        putusan_data['downloaded_files'].append({
                            'type': link_info['type'],
                            'url': link_info['url'],
                            'file_path': file_path,
                            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                        })
            
        except Exception as e:
            self.logger.error(f"Error downloading files for putusan: {e}")
        
        return putusan_data
    
    def _extract_download_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract download links from detail page"""
        download_links = []
        
        # Look for download buttons/links
        download_selectors = [
            'a[href*=".pdf"]',
            'a[href*=".zip"]',
            'a[href*="download"]',
            'button[onclick*="download"]',
            '.download-btn',
            '.btn-download'
        ]
        
        for selector in download_selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get('href')
                onclick = element.get('onclick', '')
                
                # Extract URL from href or onclick
                download_url = None
                if href and (href.endswith('.pdf') or href.endswith('.zip') or 'download' in href):
                    download_url = normalize_url(href, BASE_URL)
                elif onclick:
                    # Extract URL from onclick javascript
                    url_match = re.search(r'["\']([^"\']*\.(?:pdf|zip)[^"\']*)["\']', onclick)
                    if url_match:
                        download_url = normalize_url(url_match.group(1), BASE_URL)
                
                if download_url:
                    file_type = 'pdf' if '.pdf' in download_url.lower() else 'zip'
                    download_links.append({
                        'url': download_url,
                        'type': file_type,
                        'text': element.get_text(strip=True)
                    })
        
        # Remove duplicates
        seen_urls = set()
        unique_links = []
        for link in download_links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)
        
        return unique_links
    
    def _download_file(self, link_info: Dict, putusan_data: Dict) -> Optional[str]:
        """Download a single file (PDF or ZIP)"""
        try:
            url = link_info['url']
            file_type = link_info['type']
            
            # Create filename
            nomor = putusan_data.get('nomor', 'unknown')
            # Clean nomor for filename
            safe_nomor = re.sub(r'[^\w\-_.]', '_', nomor)
            filename = f"{safe_nomor}.{file_type}"
            
            # Create subdirectory based on type
            type_dir = os.path.join(self.download_dir, file_type)
            os.makedirs(type_dir, exist_ok=True)
            
            file_path = os.path.join(type_dir, filename)
            
            # Skip if file already exists
            if os.path.exists(file_path):
                self.logger.info(f"File already exists: {file_path}")
                return file_path
            
            # Download file
            self.logger.info(f"Downloading {file_type.upper()}: {url}")
            
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if file_type == 'pdf' and 'pdf' not in content_type:
                self.logger.warning(f"Expected PDF but got content-type: {content_type}")
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            
            with open(file_path, 'wb') as f:
                if total_size > 0:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Downloading {filename}") as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                else:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            # Verify download
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                file_size = os.path.getsize(file_path)
                self.logger.info(f"Successfully downloaded {filename} ({file_size} bytes)")
                
                # Update stats
                if file_type == 'pdf':
                    self.download_stats['pdf_downloads'] += 1
                elif file_type == 'zip':
                    self.download_stats['zip_downloads'] += 1
                self.download_stats['total_size'] += file_size
                
                # Verify file integrity
                if file_type == 'zip':
                    self._verify_zip_file(file_path)
                elif file_type == 'pdf':
                    self._verify_pdf_file(file_path)
                
                return file_path
            else:
                self.logger.error(f"Downloaded file is empty or missing: {file_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error downloading file {url}: {e}")
            self.download_stats['failed_downloads'] += 1
            return None
    
    def _verify_zip_file(self, file_path: str) -> bool:
        """Verify ZIP file integrity"""
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Test the ZIP file
                bad_file = zip_ref.testzip()
                if bad_file:
                    self.logger.warning(f"Corrupt file in ZIP: {bad_file}")
                    return False
                
                # List contents
                file_list = zip_ref.namelist()
                self.logger.debug(f"ZIP contains {len(file_list)} files: {file_list[:5]}")
                return True
                
        except zipfile.BadZipFile:
            self.logger.error(f"Invalid ZIP file: {file_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error verifying ZIP file {file_path}: {e}")
            return False
    
    def _verify_pdf_file(self, file_path: str) -> bool:
        """Verify PDF file integrity"""
        try:
            # Basic PDF header check
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    self.logger.warning(f"File does not appear to be a PDF: {file_path}")
                    return False
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # Less than 1KB is suspicious
                self.logger.warning(f"PDF file suspiciously small: {file_size} bytes")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying PDF file {file_path}: {e}")
            return False
    
    def scrape_with_downloads(self, start_page: int = 1, max_pages: Optional[int] = None,
                             download_files: bool = True, download_pdf_only: bool = True) -> List[Dict]:
        """Scrape pages and download associated files"""
        
        # First scrape the data
        scraped_data = self.scrape_pages(start_page, max_pages)
        
        if not scraped_data or not download_files:
            return scraped_data
        
        # Download files for each putusan
        self.logger.info(f"Starting file downloads for {len(scraped_data)} putusan...")
        
        with tqdm(desc="Downloading files", total=len(scraped_data)) as pbar:
            for i, putusan in enumerate(scraped_data):
                try:
                    updated_putusan = self.download_putusan_file(putusan, download_pdf_only)
                    scraped_data[i] = updated_putusan
                    
                    pbar.set_postfix({
                        'PDF': self.download_stats['pdf_downloads'],
                        'ZIP': self.download_stats['zip_downloads'],
                        'Failed': self.download_stats['failed_downloads']
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error processing putusan {i}: {e}")
                
                pbar.update(1)
                
                # Rate limiting for downloads
                self._random_delay((1, 3))
        
        # Log download statistics
        self.logger.info(f"Download completed. Stats: {self.download_stats}")
        
        return scraped_data
    
    def get_download_stats(self) -> Dict:
        """Get download statistics"""
        total_downloads = self.download_stats['pdf_downloads'] + self.download_stats['zip_downloads']
        return {
            **self.download_stats,
            'total_downloads': total_downloads,
            'success_rate': (total_downloads / max(total_downloads + self.download_stats['failed_downloads'], 1)) * 100,
            'average_file_size': self.download_stats['total_size'] / max(total_downloads, 1)
        }
    
    def scrape_pages(self, start_page: int = 1, max_pages: Optional[int] = None, 
                    resume_from_checkpoint: bool = True) -> List[Dict]:
        """
        Scrape multiple pages dengan progress tracking dan checkpoint
        """
        # Load checkpoint jika diminta
        if resume_from_checkpoint:
            checkpoint = load_checkpoint()
            if checkpoint:
                self.logger.info(f"Resuming from checkpoint: page {checkpoint['last_page']}")
                start_page = checkpoint['last_page'] + 1
                self.scraped_data = checkpoint.get('data', [])
        
        progress_tracker = ProgressTracker(max_pages or 100)
        current_page = start_page
        
        try:
            with tqdm(desc="Scraping pages", unit="page") as pbar:
                while True:
                    if max_pages and current_page > max_pages:
                        break
                    
                    # Construct URL
                    page_url = f"{DIREKTORI_URL}?page={current_page}"
                    self.logger.info(f"Scraping page {current_page}: {page_url}")
                    
                    # Get page content
                    content = self.get_page_content(page_url, method='auto')
                    if not content:
                        self.logger.warning(f"Failed to get content for page {current_page}")
                        current_page += 1
                        continue
                    
                    # Parse content
                    page_data = self.parse_putusan_list(content)
                    
                    if not page_data:
                        self.logger.info(f"No data found on page {current_page}, might be end of pages")
                        break
                    
                    # Add to scraped data
                    self.scraped_data.extend(page_data)
                    
                    # Update progress
                    progress_tracker.update(current_page, len(self.scraped_data))
                    stats = progress_tracker.get_stats()
                    
                    # Update progress bar
                    pbar.update(1)
                    pbar.set_postfix({
                        'Data': len(self.scraped_data),
                        'Errors': self.stats['failed_requests'],
                        'ETA': stats['estimated_remaining']
                    })
                    
                    # Save checkpoint setiap 10 halaman
                    if current_page % 10 == 0:
                        save_checkpoint(self.scraped_data, current_page, max_pages or current_page + 100)
                        self.logger.info(f"Checkpoint saved at page {current_page}")
                    
                    current_page += 1
                    
                    # Rate limiting delay
                    self._random_delay()
        
        except KeyboardInterrupt:
            self.logger.info("Scraping interrupted by user")
            save_checkpoint(self.scraped_data, current_page - 1, max_pages or current_page + 100)
        
        except Exception as e:
            self.logger.error(f"Unexpected error during scraping: {e}")
            save_checkpoint(self.scraped_data, current_page - 1, max_pages or current_page + 100)
        
        finally:
            # Final cleanup
            self.cleanup()
        
        # Deduplicate data
        self.scraped_data = deduplicate_data(self.scraped_data)
        
        self.logger.info(f"Scraping completed. Total data: {len(self.scraped_data)}")
        return self.scraped_data
    
    def save_data(self, filename: str = None, format: str = 'json'):
        """Save scraped data dalam berbagai format"""
        if not self.scraped_data:
            self.logger.warning("No data to save")
            return
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"putusan_ma_{timestamp}"
        
        if format == 'json':
            filepath = os.path.join(PROCESSED_DATA_DIR, f"{filename}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.scraped_data, f, indent=JSON_INDENT, ensure_ascii=False)
        
        elif format == 'csv':
            import pandas as pd
            filepath = os.path.join(PROCESSED_DATA_DIR, f"{filename}.csv")
            df = pd.DataFrame(self.scraped_data)
            df.to_csv(filepath, index=False, encoding=CSV_ENCODING)
        
        elif format == 'excel':
            import pandas as pd
            filepath = os.path.join(PROCESSED_DATA_DIR, f"{filename}.xlsx")
            df = pd.DataFrame(self.scraped_data)
            df.to_excel(filepath, index=False)
        
        self.logger.info(f"Data saved to {filepath}")
        
        # Save stats
        stats_file = os.path.join(PROCESSED_DATA_DIR, f"{filename}_stats.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
    
    def get_stats(self) -> Dict:
        """Get scraping statistics"""
        return {
            **self.stats,
            'data_count': len(self.scraped_data),
            'failed_urls_count': len(self.failed_urls),
            'success_rate': (self.stats['successful_requests'] / max(self.stats['total_requests'], 1)) * 100
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.session:
            self.session.close()
        
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.warning(f"Error closing driver: {e}")


def debug_site_structure(url: str = None):
    """Standalone function to debug website structure"""
    if not url:
        url = BASE_URL
    
    print("🔍 Starting website structure analysis...")
    
    scraper = MahkamahAgungScraper(debug=True, interactive_debug=True)
    
    try:
        content = scraper.get_page_content(url)
        
        if content:
            print("✅ Successfully retrieved content")
            
            # Analyze HTML structure
            analyzer = HTMLAnalyzer()
            analysis = analyzer.analyze_html_structure(content)
            
            print(f"\n📊 Structure Analysis:")
            print(f"  Total elements: {analysis['total_elements']}")
            print(f"  Tables: {len(analysis['tables'])}")
            print(f"  Forms: {len(analysis['forms'])}")
            print(f"  Links: {analysis['links']['total']}")
            
            if analysis['possible_selectors']:
                print(f"\n🎯 Suggested selectors:")
                for selector in analysis['possible_selectors'][:10]:
                    print(f"  {selector['selector']} -> {selector['found_count']} elements")
            
            # Test parsing
            print(f"\n🧪 Testing data extraction...")
            data = scraper.parse_putusan_list(content)
            print(f"  Extracted {len(data)} records")
            
            if data:
                print(f"  Sample record: {data[0]}")
            
        else:
            print("❌ Failed to retrieve content")
    
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    
    finally:
        scraper.cleanup()


def main():
    """Enhanced main function with download options"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mahkamah Agung Scraper with Download Capability')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--interactive', action='store_true', help='Enable interactive debug mode')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze site structure')
    parser.add_argument('--url', help='Specific URL to analyze')
    parser.add_argument('--pages', type=int, default=3, help='Number of pages to scrape (default: 3)')
    parser.add_argument('--download', action='store_true', help='Download PDF/ZIP files')
    parser.add_argument('--download-all', action='store_true', help='Download both PDF and ZIP files')
    parser.add_argument('--no-pdf', action='store_true', help='Skip PDF downloads (only ZIP)')
    
    args = parser.parse_args()
    
    if args.analyze_only:
        debug_site_structure(args.url)
        return
    
    scraper = MahkamahAgungScraper(debug=args.debug, interactive_debug=args.interactive)
    
    try:
        # Test basic connectivity
        test_url = args.url or BASE_URL
        content = scraper.get_page_content(test_url)
        
        if content:
            print(f"✅ Successfully connected to {test_url}")
            print(f"✅ Content length: {len(content)} characters")
        else:
            print(f"❌ Failed to connect to {test_url}")
            return
        
        # Start scraping
        print(f"\n🚀 Starting scraping...")
        
        if args.download or args.download_all:
            download_pdf_only = not args.no_pdf and not args.download_all
            data = scraper.scrape_with_downloads(
                start_page=1, 
                max_pages=args.pages,
                download_files=True,
                download_pdf_only=download_pdf_only
            )
            
            print(f"\n📁 Download Stats:")
            download_stats = scraper.get_download_stats()
            for key, value in download_stats.items():
                print(f"  {key}: {value}")
        else:
            data = scraper.scrape_pages(start_page=1, max_pages=args.pages)
        
        print(f"\n📊 Results:")
        print(f"  Scraped: {len(data)} records")
        print(f"  Stats: {scraper.get_stats()}")
        
        if data:
            scraper.save_data("debug_run")
            print("✅ Data saved successfully")
            
            # Show sample data
            print(f"\n📋 Sample records:")
            for i, record in enumerate(data[:2]):
                print(f"  {i+1}. {record.get('title', 'No title')}")
                if 'downloaded_files' in record:
                    print(f"     Downloaded: {len(record['downloaded_files'])} files")
        else:
            print("⚠️  No data extracted - check debug logs for details")
    
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        scraper.logger.error(f"Main function error: {e}")
    
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main()
