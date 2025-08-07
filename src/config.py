"""
Konfigurasi untuk scraper Mahkamah Agung
"""

import os

# URL Configuration
BASE_URL = "https://putusan3.mahkamahagung.go.id"
DIREKTORI_URL = f"{BASE_URL}/direktori"

# Directory Configuration
DATA_DIR = "data"
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
LOG_DIR = "logs"

# Scraping Configuration
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
DELAY_RANGE = (1, 3)  # Random delay between requests
RATE_LIMIT_DELAY_RANGE = (2, 5)  # Delay when rate limited

# User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

# Selenium Configuration (fallback)
SELENIUM_CONFIG = {
    "headless": True,
    "window_size": (1920, 1080),
    "page_load_timeout": 30,
    "implicit_wait": 10
}

# Data Validation
REQUIRED_FIELDS = ["nomor", "tanggal", "jenis"]
OPTIONAL_FIELDS = ["link", "scraped_at", "additional_data"]

# Export Configuration
EXPORT_FORMATS = ["csv", "json", "excel"]
CSV_ENCODING = "utf-8"
JSON_INDENT = 2

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
