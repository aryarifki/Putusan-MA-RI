"""
Debugging tools for web scraping - inspect websites and test selectors
"""

import requests
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

def inspect_website(url: str):
    """
    Comprehensive website inspection tool
    """
    print(f"🔍 Inspecting: {url}")
    print("=" * 60)
    
    try:
        # Make request
        response = requests.get(url, timeout=30)
        
        print(f"📊 Response Info:")
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"  Content-Length: {len(response.content)} bytes")
        print(f"  Encoding: {response.encoding}")
        
        if response.history:
            print(f"  Redirects: {len(response.history)}")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'lxml')
        
        print(f"\n🏗️  HTML Structure:")
        print(f"  Title: {soup.title.string if soup.title else 'No title'}")
        print(f"  Total elements: {len(soup.find_all())}")
        print(f"  Tables: {len(soup.find_all('table'))}")
        print(f"  Forms: {len(soup.find_all('form'))}")
        print(f"  Links: {len(soup.find_all('a'))}")
        print(f"  Scripts: {len(soup.find_all('script'))}")
        
        # Check for potential data containers
        print(f"\n📦 Potential Data Containers:")
        containers = [
            ('Tables', soup.find_all('table')),
            ('Lists (ul)', soup.find_all('ul')),
            ('Lists (ol)', soup.find_all('ol')),
            ('Articles', soup.find_all('article')),
            ('Sections', soup.find_all('section')),
        ]
        
        for name, elements in containers:
            if elements:
                print(f"  {name}: {len(elements)} found")
                for i, elem in enumerate(elements[:3]):
                    preview = elem.get_text(strip=True)[:100]
                    print(f"    {i+1}. {preview}...")
        
        # Check for common class patterns
        print(f"\n🎨 Common CSS Classes:")
        all_classes = []
        for elem in soup.find_all(class_=True):
            all_classes.extend(elem.get('class', []))
        
        class_counts = {}
        for cls in all_classes:
            class_counts[cls] = class_counts.get(cls, 0) + 1
        
        # Show top 10 most common classes
        for cls, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  .{cls}: {count} elements")
        
        # Check for AJAX/JavaScript indicators
        print(f"\n⚡ Dynamic Content Indicators:")
        page_text = response.text.lower()
        js_indicators = ['ajax', 'fetch', 'xmlhttprequest', 'api', 'json', 'async', 'spa']
        found_indicators = [indicator for indicator in js_indicators if indicator in page_text]
        
        if found_indicators:
            print(f"  Found: {', '.join(found_indicators)}")
        else:
            print("  No common AJAX indicators found")
        
        # Save for manual inspection
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\n💾 Full HTML saved to: debug_page.html")
        
        return soup
        
    except Exception as e:
        print(f"❌ Error inspecting website: {e}")
        return None

def test_selectors(html_file: str = None, url: str = None):
    """
    Interactive selector testing tool
    """
    if html_file and os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        print(f"📄 Loaded HTML from: {html_file}")
    elif url:
        response = requests.get(url)
        html_content = response.text
        print(f"🌐 Loaded HTML from: {url}")
    else:
        print("❌ Please provide either html_file or url parameter")
        return
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    print("\n🎯 CSS Selector Testing Tool")
    print("Enter CSS selectors to test (or 'quit' to exit)")
    print("Examples: 'table tr', 'div.content', '#main', etc.")
    
    while True:
        try:
            selector = input("\nSelector: ").strip()
            
            if selector.lower() in ['quit', 'exit', 'q']:
                break
            
            if not selector:
                continue
            
            elements = soup.select(selector)
            print(f"\n✅ Found {len(elements)} elements")
            
            if elements:
                print("📋 Sample elements:")
                for i, elem in enumerate(elements[:5]):
                    print(f"  {i+1}. Tag: <{elem.name}>")
                    if elem.get('class'):
                        print(f"     Classes: {' '.join(elem.get('class'))}")
                    if elem.get('id'):
                        print(f"     ID: {elem.get('id')}")
                    
                    text = elem.get_text(strip=True)
                    if text:
                        preview = text[:100] + "..." if len(text) > 100 else text
                        print(f"     Text: {preview}")
                    print()
                
                # Show attributes of first element
                if elements[0].attrs:
                    print("🏷️  First element attributes:")
                    for attr, value in elements[0].attrs.items():
                        print(f"     {attr}: {value}")
            
        except Exception as e:
            print(f"❌ Error with selector: {e}")

def generate_test_selectors(soup: BeautifulSoup) -> list:
    """
    Generate potential selectors for testing
    """
    selectors = []
    
    # Table-based selectors
    if soup.find_all('table'):
        selectors.extend([
            'table',
            'table tr',
            'table tbody tr',
            'table tr:not(:first-child)',
            'table td',
            'table th'
        ])
    
    # List-based selectors
    if soup.find_all(['ul', 'ol']):
        selectors.extend([
            'ul li',
            'ol li',
            'li'
        ])
    
    # Common container patterns
    common_patterns = [
        'div[class*="content"]',
        'div[class*="item"]',
        'div[class*="row"]',
        'div[class*="card"]',
        'div[class*="list"]',
        'div[class*="data"]',
        'article',
        'section',
        '.main',
        '#main',
        '.content',
        '#content'
    ]
    
    selectors.extend(common_patterns)
    
    return selectors

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python debug_tools.py inspect <url>")
        print("  python debug_tools.py test <url_or_file>")
        print("  python debug_tools.py selectors <url_or_file>")
        sys.exit(1)
    
    command = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else None
    
    if command == "inspect":
        inspect_website(target)
    elif command == "test":
        if target.startswith('http'):
            test_selectors(url=target)
        else:
            test_selectors(html_file=target)
    elif command == "selectors":
        # Auto-generate and test selectors
        if target.startswith('http'):
            response = requests.get(target)
            soup = BeautifulSoup(response.text, 'lxml')
        else:
            with open(target, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'lxml')
        
        selectors = generate_test_selectors(soup)
        print("🎯 Testing generated selectors:")
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"✅ {selector}: {len(elements)} elements")
            else:
                print(f"❌ {selector}: No elements")
