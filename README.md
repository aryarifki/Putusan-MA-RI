# Putusan-MA-RI
Mengklasifikasi dan Meringkas Putusan Mahkamah Agung Indonesia dengan IBM Granite

## 🔧 Pembaruan Terbaru (2025-08-07)

### ✅ Perbaikan Scraper
Scraper telah diperbaiki dengan fitur-fitur berikut:

- **Kompatibilitas urllib3 2.0+**: Fixed TypeError untuk `method_whitelist` → `allowed_methods`
- **Error Handling Comprehensive**: Menangani timeout, rate limiting, connection errors
- **Fallback Strategy**: Requests → Selenium untuk anti-bot protection
- **Debug & Monitoring**: Logging detail, progress tracking, checkpoint system
- **User Agent Rotation**: Menghindari detection dengan rotasi user agent

### 🚀 Quick Start

```bash
# Test konektivitas
python example_usage.py --test-only --debug

# Scrape 10 halaman
python example_usage.py --pages 10 --format json

# Resume dari checkpoint
python example_usage.py --resume --pages 50
```

### 📖 Dokumentasi
- [Panduan Lengkap Scraper](SCRAPER_GUIDE.md)
- [Contoh Penggunaan](example_usage.py)

## 🛠️ Requirements

Pastikan menggunakan versi library terbaru:

```bash
pip install -r requirements.txt
```

Library utama:
- requests >= 2.28.0
- urllib3 >= 2.5.0 (compatible)
- beautifulsoup4 >= 4.11.0
- selenium >= 4.8.0

## 📁 Struktur Proyek

```
├── src/
│   ├── scraper.py       # Main scraper (UPDATED)
│   ├── config.py        # Konfigurasi
│   └── utils.py         # Utility functions
├── data/
│   ├── raw/             # Data mentah
│   └── processed/       # Data yang sudah diproses
├── logs/                # Log files dan debug data
├── example_usage.py     # Contoh penggunaan (NEW)
├── SCRAPER_GUIDE.md     # Panduan lengkap (NEW)
└── requirements.txt
```

## 🔍 Error Handling

Scraper menangani berbagai error scenario:

- ✅ DNS resolution failures
- ✅ Connection timeouts  
- ✅ HTTP error codes (403, 429, 500+)
- ✅ Rate limiting dengan backoff
- ✅ SSL/TLS errors
- ✅ Anti-bot protection via Selenium

## 📊 Features

- **Modern urllib3 patterns**: Compatible dengan versi terbaru
- **Automatic retry**: Exponential backoff strategy
- **Progress tracking**: Real-time monitoring dengan tqdm
- **Data persistence**: Checkpoint system untuk resume
- **Multiple output formats**: JSON, CSV, Excel
- **Comprehensive logging**: Debug dan monitoring lengkap
