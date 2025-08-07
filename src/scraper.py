"""
Scraper untuk Mahkamah Agung RI dengan error handling yang comprehensive
Compatible dengan urllib3 2.0+ dan memiliki fallback strategies
"""

import requests
import urllib3
import time
import random
import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
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


class MahkamahAgungScraper:
    """
    Scraper untuk website Mahkamah Agung dengan multiple fallback strategies
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
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
        
        # Initialize sessions
        self._setup_requests_session()
        
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
        """Get content menggunakan requests session"""
        try:
            self.logger.debug(f"Attempting to fetch {url} using requests")
            
            # Random delay
            self._random_delay()
            
            # Rotate user agent occasionally
            if random.random() < 0.1:  # 10% chance
                self._rotate_user_agent()
            
            response = self.session.get(
                url,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=True,
                verify=True  # Enable SSL verification
            )
            
            # Handle different status codes
            if response.status_code == 200:
                self.logger.debug(f"Successfully fetched {url}")
                
                # Save debug HTML jika diperlukan
                if self.debug:
                    self._save_debug_html(url, response.text)
                
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
    
    def _get_content_selenium(self, url: str) -> Optional[str]:
        """Get content menggunakan Selenium sebagai fallback"""
        if not self.driver:
            if not self._setup_selenium_driver():
                raise Exception("Failed to setup Selenium driver")
        
        try:
            self.logger.debug(f"Attempting to fetch {url} using Selenium")
            
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(random.uniform(2, 4))
            
            content = self.driver.page_source
            
            if self.debug:
                self._save_debug_html(url, content, method='selenium')
            
            self.logger.debug(f"Successfully fetched {url} using Selenium")
            return content
            
        except Exception as e:
            self.logger.warning(f"Selenium failed for {url}: {e}")
            raise Exception(f"Selenium error: {e}")
    
    def _save_debug_html(self, url: str, content: str, method: str = 'requests'):
        """Save HTML content untuk debugging"""
        try:
            debug_dir = "logs/html_debug"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Create safe filename
            filename = urlparse(url).path.replace('/', '_').replace('\\', '_')
            if not filename:
                filename = 'index'
            filename = f"{method}_{filename}_{int(time.time())}.html"
            
            filepath = os.path.join(debug_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.logger.debug(f"Debug HTML saved: {filepath}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save debug HTML: {e}")
    
    def parse_putusan_list(self, html_content: str) -> List[Dict]:
        """Parse HTML content untuk extract data putusan"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            putusan_list = []
            
            # Basic implementation - perlu disesuaikan dengan struktur HTML aktual
            # Ini adalah template yang bisa disesuaikan
            
            # Cari tabel atau container yang berisi daftar putusan
            # Contoh selector - perlu disesuaikan
            rows = soup.find_all('tr') or soup.find_all('div', class_='putusan-item')
            
            for row in rows:
                try:
                    # Extract data - sesuaikan dengan struktur HTML
                    nomor = self._extract_text(row, ['nomor', 'number', 'no'])
                    tanggal = self._extract_text(row, ['tanggal', 'date', 'tgl'])
                    jenis = self._extract_text(row, ['jenis', 'type', 'kategori'])
                    
                    if nomor and tanggal and jenis:
                        putusan_data = {
                            'nomor': clean_text(nomor),
                            'tanggal': clean_text(tanggal),
                            'jenis': clean_text(jenis),
                            'scraped_at': datetime.now().isoformat()
                        }
                        
                        # Extract link jika ada
                        link_elem = row.find('a')
                        if link_elem and link_elem.get('href'):
                            putusan_data['link'] = normalize_url(link_elem['href'], BASE_URL)
                        
                        # Validasi data
                        if validate_data(putusan_data):
                            putusan_list.append(putusan_data)
                        
                except Exception as e:
                    self.logger.warning(f"Error parsing row: {e}")
                    continue
            
            self.logger.info(f"Parsed {len(putusan_list)} putusan from page")
            return putusan_list
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML content: {e}")
            return []
    
    def _extract_text(self, element, possible_selectors: List[str]) -> Optional[str]:
        """Extract text dari element dengan multiple possible selectors"""
        for selector in possible_selectors:
            # Try class
            found = element.find(class_=selector)
            if found:
                return found.get_text(strip=True)
            
            # Try attribute
            found = element.find(attrs={selector: True})
            if found:
                return found.get_text(strip=True)
            
            # Try data attribute
            found = element.find(attrs={f'data-{selector}': True})
            if found:
                return found.get_text(strip=True)
        
        return None
    
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


def main():
    """Main function untuk testing scraper"""
    scraper = MahkamahAgungScraper(debug=True)
    
    try:
        # Test basic connectivity
        test_url = BASE_URL
        content = scraper.get_page_content(test_url)
        
        if content:
            print(f"✓ Successfully connected to {test_url}")
            print(f"✓ Content length: {len(content)} characters")
        else:
            print(f"✗ Failed to connect to {test_url}")
            return
        
        # Test scraping a few pages
        print("\nStarting scraping test...")
        data = scraper.scrape_pages(start_page=1, max_pages=3)
        
        print(f"\n✓ Scraped {len(data)} records")
        print("✓ Stats:", scraper.get_stats())
        
        if data:
            scraper.save_data("test_run")
            print("✓ Data saved successfully")
        
    except Exception as e:
        print(f"✗ Error during scraping: {e}")
        scraper.logger.error(f"Main function error: {e}")
    
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main()
