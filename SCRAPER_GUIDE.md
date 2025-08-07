# Scraper Usage Guide

## Overview
Scraper Mahkamah Agung yang telah diperbaiki dengan kompatibilitas urllib3 2.0+ dan error handling yang comprehensive.

## Fitur Utama

### 1. Kompatibilitas Library Modern
- ✅ Compatible dengan urllib3 2.5.0+
- ✅ Menggunakan `allowed_methods` bukan `method_whitelist` (deprecated)
- ✅ Modern retry strategy dengan backoff exponential

### 2. Error Handling yang Robust
- ✅ Connection timeouts dan network errors
- ✅ HTTP error codes (403, 404, 500, etc.)
- ✅ Rate limiting dengan automatic backoff
- ✅ DNS resolution failures
- ✅ SSL/TLS errors

### 3. Fallback Strategies
- ✅ Primary: Requests dengan retry strategy
- ✅ Fallback: Selenium WebDriver untuk anti-bot protection
- ✅ User agent rotation
- ✅ Random delays untuk menghindari detection

### 4. Debugging & Monitoring
- ✅ Comprehensive logging
- ✅ Progress tracking dengan tqdm
- ✅ Statistics collection
- ✅ Debug HTML saving
- ✅ Checkpoint system untuk resume scraping

## Quick Start

```python
from scraper import MahkamahAgungScraper

# Basic usage
scraper = MahkamahAgungScraper(debug=True)

# Test single page
content = scraper.get_page_content('https://putusan3.mahkamahagung.go.id')

# Scrape multiple pages
data = scraper.scrape_pages(start_page=1, max_pages=10)

# Save data
scraper.save_data('results', format='json')

# Cleanup
scraper.cleanup()
```

## Advanced Usage

### Custom Configuration
Semua konfigurasi tersedia di `config.py`:
- `DEFAULT_TIMEOUT`: Request timeout
- `MAX_RETRIES`: Maximum retry attempts
- `DELAY_RANGE`: Random delay between requests
- `USER_AGENTS`: List of user agents for rotation

### Error Recovery
- Automatic retry dengan exponential backoff
- Checkpoint system untuk resume dari interrupsi
- Fallback ke Selenium jika requests gagal

### Debugging
```python
# Enable debug mode
scraper = MahkamahAgungScraper(debug=True)

# Check logs
# File: logs/scraper_YYYYMMDD_HHMMSS.log

# Check debug HTML
# Directory: logs/html_debug/
```

## Error Scenarios Handled

1. **Network Issues**
   - DNS resolution failures
   - Connection timeouts
   - Connection resets

2. **HTTP Errors**
   - 403 Forbidden (website blocking)
   - 429 Too Many Requests (rate limiting)
   - 500+ Server errors
   - Redirects dan SSL issues

3. **Anti-Bot Protection**
   - User agent detection
   - JavaScript challenges (via Selenium)
   - CAPTCHA detection
   - IP blocking

## Performance & Statistics

Scraper mengumpulkan statistik real-time:
- Total requests
- Success/failure rates
- Method usage (requests vs selenium)
- Error types dan frequencies
- Data extraction rates

## Troubleshooting

### Common Issues

1. **"method_whitelist" Error**
   - ✅ Fixed: Menggunakan `allowed_methods` untuk urllib3 2.0+

2. **Connection Timeouts**
   - ✅ Handled: Automatic retry dengan exponential backoff

3. **Website Blocking**
   - ✅ Handled: Fallback ke Selenium dengan user agent rotation

4. **Rate Limiting**
   - ✅ Handled: Respect Retry-After headers dan backoff strategy

### Best Practices

1. Gunakan debug mode untuk troubleshooting
2. Monitor logs untuk error patterns
3. Adjust delays jika terlalu banyak rate limiting
4. Gunakan checkpoint system untuk scraping besar
5. Save data secara berkala untuk menghindari data loss