"""
Utility functions untuk scraper Mahkamah Agung
"""

import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Union
from urllib.parse import urljoin, urlparse

def setup_directories():
    """Setup direktori yang diperlukan"""
    directories = [
        "data/raw",
        "data/processed", 
        "logs",
        "logs/html_debug"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def clean_text(text: str) -> str:
    """Membersihkan text dari karakter yang tidak diinginkan"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might cause issues
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    return text.strip()

def normalize_url(url: str, base_url: str) -> str:
    """Normalize URL untuk memastikan format yang benar"""
    if not url:
        return ""
    
    # Jika sudah URL lengkap
    if url.startswith('http'):
        return url
    
    # Jika relative URL
    if url.startswith('/'):
        return urljoin(base_url, url)
    
    # Jika URL relatif tanpa slash
    return urljoin(base_url + '/', url)

def validate_data(data: Dict) -> bool:
    """Validasi data yang di-scrape"""
    required_fields = ["nomor", "tanggal", "jenis"]
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False
    
    # Validasi format tanggal jika diperlukan
    if data.get("tanggal"):
        # Basic date validation - bisa diperluas sesuai kebutuhan
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
            r'\d{1,2}\s+\w+\s+\d{4}'
        ]
        
        date_valid = any(re.search(pattern, data["tanggal"]) for pattern in date_patterns)
        if not date_valid:
            logging.warning(f"Format tanggal tidak valid: {data['tanggal']}")
    
    return True

def deduplicate_data(data: List[Dict], key_field: str = "nomor") -> List[Dict]:
    """Menghapus duplikasi data berdasarkan field tertentu"""
    seen = set()
    unique_data = []
    
    for item in data:
        key = item.get(key_field, "")
        if key and key not in seen:
            seen.add(key)
            unique_data.append(item)
    
    return unique_data

def save_checkpoint(data: List[Dict], page_num: int, total_pages: int):
    """Menyimpan checkpoint untuk resume scraping"""
    checkpoint_dir = "logs/checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    checkpoint_file = os.path.join(checkpoint_dir, "last_checkpoint.json")
    
    checkpoint_data = {
        "last_page": page_num,
        "total_pages": total_pages,
        "data_count": len(data),
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    
    import json
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

def load_checkpoint() -> Optional[Dict]:
    """Memuat checkpoint terakhir"""
    checkpoint_file = "logs/checkpoints/last_checkpoint.json"
    
    if not os.path.exists(checkpoint_file):
        return None
    
    try:
        import json
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading checkpoint: {e}")
        return None

def format_file_size(size_bytes: int) -> str:
    """Format ukuran file menjadi readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def estimate_time_remaining(start_time: datetime, current_page: int, total_pages: int) -> str:
    """Estimasi waktu yang tersisa untuk scraping"""
    if current_page == 0:
        return "Unknown"
    
    elapsed = datetime.now() - start_time
    avg_time_per_page = elapsed.total_seconds() / current_page
    remaining_pages = total_pages - current_page
    remaining_seconds = avg_time_per_page * remaining_pages
    
    hours = int(remaining_seconds // 3600)
    minutes = int((remaining_seconds % 3600) // 60)
    seconds = int(remaining_seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

class ProgressTracker:
    """Class untuk tracking progress scraping"""
    
    def __init__(self, total_pages: int):
        self.total_pages = total_pages
        self.start_time = datetime.now()
        self.current_page = 0
        self.data_count = 0
        self.error_count = 0
        
    def update(self, page: int, data_count: int, has_error: bool = False):
        """Update progress"""
        self.current_page = page
        self.data_count = data_count
        if has_error:
            self.error_count += 1
    
    def get_stats(self) -> Dict:
        """Mendapatkan statistik progress"""
        elapsed = datetime.now() - self.start_time
        progress_percent = (self.current_page / self.total_pages) * 100
        
        return {
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "progress_percent": round(progress_percent, 2),
            "data_count": self.data_count,
            "error_count": self.error_count,
            "elapsed_time": str(elapsed).split('.')[0],
            "estimated_remaining": estimate_time_remaining(
                self.start_time, self.current_page, self.total_pages
            )
  }
