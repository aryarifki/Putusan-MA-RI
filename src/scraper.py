import csv
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# Setup logging
def setup_logging():
    os.makedirs("logs", exist_ok=True)
    log_filename = f"logs/scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

class MahkamahAgunScraper:
    def __init__(self):
        self.logger = setup_logging()
        self.base_url = "https://putusan3.mahkamahagung.go.id"
        self.direktori_url = f"{self.base_url}/direktori"
        self.out_dir = "data/raw"
        os.makedirs(self.out_dir, exist_ok=True)
        
        # User agents untuk rotasi
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
        
        self.session = self._create_session()
        
    def _create_session(self):
        """Membuat session dengan retry dan timeout yang tepat"""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_headers(self):
        """Mendapatkan headers dengan user agent random"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
    
    def _save_debug_html(self, html_content: str, page_num: int = 0):
        """Menyimpan HTML untuk debugging"""
        debug_dir = "logs/html_debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        filename = f"{debug_dir}/page_{page_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML debug saved to: {filename}")
    
    def _make_request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        """Membuat request dengan retry dan error handling"""
        for attempt in range(retries):
            try:
                headers = self._get_headers()
                response = self.session.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Delay random untuk menghindari rate limiting
                time.sleep(random.uniform(1, 3))
                
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == retries - 1:
                    self.logger.error(f"All attempts failed for {url}")
                    return None
                time.sleep(random.uniform(2, 5))
        
        return None
    
    def get_total_pages(self) -> int:
        """Mendapatkan total halaman dengan multiple fallback strategies"""
        self.logger.info("Mengambil total halaman...")
        
        response = self._make_request(self.direktori_url)
        if not response:
            self.logger.error("Gagal mengambil halaman utama")
            return 1
        
        # Save HTML for debugging
        self._save_debug_html(response.text, 0)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Strategy 1: Cari link "Terakhir"
        last_links = soup.find_all('a', string=re.compile(r'Terakhir|Last', re.IGNORECASE))
        for link in last_links:
            href = link.get('href', '')
            if 'page=' in href:
                try:
                    page_num = int(href.split('page=')[-1])
                    self.logger.info(f"Total halaman ditemukan (Strategy 1): {page_num}")
                    return page_num
                except ValueError:
                    continue
        
        # Strategy 2: Cari pagination dengan pattern yang berbeda
        pagination_patterns = [
            r'page=(\d+)',
            r'halaman=(\d+)',
            r'p=(\d+)'
        ]
        
        for pattern in pagination_patterns:
            matches = re.findall(pattern, response.text)
            if matches:
                max_page = max(map(int, matches))
                self.logger.info(f"Total halaman ditemukan (Strategy 2): {max_page}")
                return max_page
        
        # Strategy 3: Cari di pagination elements
        pagination_elements = soup.find_all(['nav', 'div'], class_=re.compile(r'pag', re.IGNORECASE))
        for element in pagination_elements:
            links = element.find_all('a')
            page_numbers = []
            for link in links:
                text = link.get_text(strip=True)
                if text.isdigit():
                    page_numbers.append(int(text))
            
            if page_numbers:
                max_page = max(page_numbers)
                self.logger.info(f"Total halaman ditemukan (Strategy 3): {max_page}")
                return max_page
        
        self.logger.warning("Tidak dapat menentukan total halaman, menggunakan default: 1")
        return 1
    
    def scrape_page(self, page_num: int) -> List[Dict]:
        """Scraping satu halaman dengan multiple selector strategies"""
        url = f"{self.direktori_url}?page={page_num}"
        self.logger.info(f"Scraping halaman {page_num}: {url}")
        
        response = self._make_request(url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Multiple selector strategies
        selectors = [
            "table.table tbody tr",
            "table tbody tr",
            ".table tbody tr",
            "tbody tr",
            "tr"
        ]
        
        rows = []
        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                self.logger.info(f"Ditemukan {len(rows)} baris dengan selector: {selector}")
                break
        
        if not rows:
            self.logger.warning(f"Tidak ada data ditemukan di halaman {page_num}")
            # Save HTML for debugging
            self._save_debug_html(response.text, page_num)
            return []
        
        data = []
        for i, tr in enumerate(rows):
            try:
                cols = tr.find_all(['td', 'th'])
                if len(cols) < 3:  # Skip header atau row yang tidak lengkap
                    continue
                
                # Extract data dengan multiple strategies
                row_data = self._extract_row_data(cols, tr)
                if row_data:
                    data.append(row_data)
                    
            except Exception as e:
                self.logger.warning(f"Error parsing row {i} di halaman {page_num}: {e}")
                continue
        
        self.logger.info(f"Berhasil extract {len(data)} data dari halaman {page_num}")
        return data
    
    def _extract_row_data(self, cols, tr) -> Optional[Dict]:
        """Extract data dari row dengan berbagai strategi"""
        try:
            # Strategy 1: Asumsi kolom standar (nomor, tanggal, jenis, link)
            if len(cols) >= 4:
                nomor_col = cols[0]
                tgl_col = cols[1]
                jenis_col = cols[2]
                
                # Extract nomor
                nomor = nomor_col.get_text(strip=True)
                
                # Extract link
                link_element = nomor_col.find('a')
                if not link_element:
                    link_element = tr.find('a')
                
                if link_element:
                    href = link_element.get('href', '')
                    if href.startswith('/'):
                        link = urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        link = href
                    else:
                        link = urljoin(self.direktori_url, href)
                else:
                    link = ""
                
                return {
                    "nomor": nomor,
                    "tanggal": tgl_col.get_text(strip=True),
                    "jenis": jenis_col.get_text(strip=True),
                    "link": link,
                    "scraped_at": datetime.now().isoformat()
                }
            
            # Strategy 2: Jika struktur berbeda, coba extract semua text
            elif len(cols) >= 2:
                all_text = [col.get_text(strip=True) for col in cols]
                link_element = tr.find('a')
                link = ""
                if link_element:
                    href = link_element.get('href', '')
                    if href:
                        link = urljoin(self.base_url, href)
                
                return {
                    "nomor": all_text[0] if all_text else "",
                    "tanggal": all_text[1] if len(all_text) > 1 else "",
                    "jenis": all_text[2] if len(all_text) > 2 else "",
                    "additional_data": all_text[3:] if len(all_text) > 3 else [],
                    "link": link,
                    "scraped_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.warning(f"Error extracting row data: {e}")
            
        return None
    
    def save_data(self, data: List[Dict], filename_prefix: str = "direktori_putusan"):
        """Menyimpan data ke berbagai format"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save as CSV
        csv_path = os.path.join(self.out_dir, f"{filename_prefix}_{timestamp}.csv")
        if data:
            fieldnames = list(data[0].keys())
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            self.logger.info(f"Data CSV disimpan: {csv_path}")
        
        # Save as JSON
        json_path = os.path.join(self.out_dir, f"{filename_prefix}_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Data JSON disimpan: {json_path}")
        
        return csv_path, json_path
    
    def scrape_all(self, max_pages: int = None):
        """Scraping semua halaman"""
        self.logger.info("Memulai scraping...")
        
        total_pages = self.get_total_pages()
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        self.logger.info(f"Total halaman yang akan di-scrape: {total_pages}")
        
        all_data = []
        failed_pages = []
        
        for page_num in tqdm(range(1, total_pages + 1), desc="Scraping"):
            try:
                page_data = self.scrape_page(page_num)
                all_data.extend(page_data)
                
                if not page_data:
                    failed_pages.append(page_num)
                
                # Progress report setiap 10 halaman
                if page_num % 10 == 0:
                    self.logger.info(f"Progress: {page_num}/{total_pages} halaman, {len(all_data)} data terkumpul")
                
            except Exception as e:
                self.logger.error(f"Error scraping halaman {page_num}: {e}")
                failed_pages.append(page_num)
                continue
        
        # Save data
        if all_data:
            csv_path, json_path = self.save_data(all_data)
            self.logger.info(f"Scraping selesai! {len(all_data)} data berhasil dikumpulkan")
            self.logger.info(f"Data disimpan di: {csv_path}")
            
            if failed_pages:
                self.logger.warning(f"Halaman yang gagal: {failed_pages}")
        else:
            self.logger.error("Tidak ada data yang berhasil di-scrape!")
        
        return all_data

def main():
    scraper = MahkamahAgunScraper()
    
    # Test dengan beberapa halaman pertama
    print("Testing dengan 5 halaman pertama...")
    data = scraper.scrape_all(max_pages=5)
    
    if data:
        print(f"Berhasil! {len(data)} data terkumpul")
        print("Sample data:")
        for i, item in enumerate(data[:3]):
            print(f"{i+1}. {item}")
    else:
        print("Tidak ada data yang berhasil di-scrape. Cek log untuk detail.")

if __name__ == "__main__":
    main()
