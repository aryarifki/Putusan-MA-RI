# Scrapper Putusan-MA-RI

## 🔧 Pembaruan Terakhir (2025-08-07)

### ✅ Perbaikan Scraper 
- **Kompatibilitas urllib3 2.0+**: Fixed TypeError untuk `method_whitelist` → `allowed_methods`
- **Error Handling Comprehensive**: Menangani timeout, rate limiting, connection errors
- **Fallback Strategy**: Requests → Selenium untuk anti-bot protection
- **Debug & Monitoring**: Logging detail, progress tracking, checkpoint system
- **User Agent Rotation**: Menghindari detection dengan rotasi user agent
- **HTML Structure Analysis**: Debug tools untuk analisis struktur website

### 🚀 Quick Start

```bash
# Test konektivitas
python scraper.py --test-only --debug

# Scrape 10 halaman dengan format JSON
python scraper.py --pages 10 --format json

# Resume dari checkpoint
python scraper --resume --pages 50

# Debug mode dengan HTML analysis
python run_analysis.py --debug
```

### 📖 Dokumentasi Lengkap
- [📋 Panduan Lengkap Scraper](SCRAPER_GUIDE.md)
- [💻 Contoh Penggunaan](example_usage.py)
- [🔍 Debug Tools](test_debug.py)

## 🛠️ Requirements

Pastikan menggunakan versi library terbaru:

```bash
pip install -r requirements.txt
```

Library utama:
- `requests >= 2.28.0`
- `urllib3 >= 2.5.0` (compatible)
- `beautifulsoup4 >= 4.11.0`
- `selenium >= 4.8.0`
- `pandas >= 1.5.0`
- `tqdm >= 4.64.0`

## 📁 Struktur Proyek

```
├── src/
│   ├── scraper.py              # Main scraper (UPDATED)
│   ├── config.py               # Konfigurasi sistem
│   ├── utils.py                # Utility functions
│   ├── debug_tools.py          # Debug dan monitoring tools (NEW)
│   └── html_structure_analyzer.py # HTML analysis tools (NEW)
├── data/
│   ├── raw/                    # Data mentah hasil scraping
│   └── processed/              # Data yang sudah diproses
├── logs/
│   ├── scraper_*.log          # Log files scraping
│   └── html_debug/            # Debug HTML files (NEW)
│       ├── requests_index_*.html
│       └── requests__direktori_*.html
├── example_usage.py           # Contoh penggunaan (NEW)
├── run_analysis.py            # Script analisis (NEW)
├── test_debug.py              # Debug testing (NEW)
├── SCRAPER_GUIDE.md           # Panduan lengkap (NEW)
└── requirements.txt           # Dependencies
```

## 🔍 Error Handling & Debugging

### Error Scenarios yang Ditangani
- ✅ **DNS resolution failures**: Automatic retry dengan backoff
- ✅ **Connection timeouts**: Configurable timeout settings
- ✅ **HTTP error codes**: 403, 404, 429, 500+ dengan retry logic
- ✅ **Rate limiting**: Exponential backoff strategy
- ✅ **SSL/TLS errors**: Certificate validation handling
- ✅ **Anti-bot protection**: Selenium WebDriver fallback

### Debug Features
- 🔍 **HTML Debug Saving**: Menyimpan response HTML untuk analisis
- 📊 **Progress Tracking**: Real-time monitoring dengan tqdm
- 📈 **Statistics Collection**: Success/error rates dan performance metrics
- 🔄 **Checkpoint System**: Resume scraping dari titik terakhir
- 📝 **Comprehensive Logging**: Multi-level logging (DEBUG, INFO, WARNING, ERROR)

## 📊 Features Utama

### Modern Scraping Infrastructure
- **urllib3 2.0+ Compatible**: Menggunakan `allowed_methods` pattern terbaru
- **Automatic Retry Logic**: Exponential backoff dengan jitter
- **User Agent Rotation**: Mencegah detection dengan rotasi UA
- **Session Management**: Persistent cookies dan headers

### Data Processing & Analysis
- **HTML Structure Analysis**: Tools untuk memahami struktur website
- **Multiple Output Formats**: JSON, CSV, Excel support
- **Data Validation**: Schema validation untuk data integrity
- **Incremental Processing**: Efficient data processing dengan chunking

### Monitoring & Observability
- **Real-time Progress**: Live progress bars dan statistics
- **Performance Metrics**: Request timing dan success rates
- **Error Analytics**: Detailed error categorization dan reporting
- **Debug Artifacts**: HTML saves dan request/response logging

## 🎯 Target Website Analysis

Scraper ini dirancang khusus untuk website Mahkamah Agung Indonesia:

### Endpoint yang Didukung
- `https://putusan3.mahkamahagung.go.id/` - Homepage
- `https://putusan3.mahkamahagung.go.id/direktori.html` - Direktori putusan
- `https://putusan3.mahkamahagung.go.id/direktori/index/kategori/*` - Kategori specific
- `https://putusan3.mahkamahagung.go.id/pengadilan/index/ditjen/*` - Per peradilan

### Struktur Data yang Diextract
- **Metadata Putusan**: Nomor, tanggal, pengadilan
- **Kategori Hukum**: Perdata, pidana, TUN, agama, dll
- **Statistik**: View count, download count, status
- **Hierarki Pengadilan**: MA, tinggi, negeri, agama, militer, pajak

## 🚀 Quick Start Examples

### 1. Test Konektivitas
```bash
python scraper.py --test-only --debug --verbose
```

### 2. Scraping Basic
```bash
# Scrape 50 halaman dengan retry logic
python scraper.py --pages 50 --format json --retry-attempts 3
```

### 3. Advanced Scraping
```bash
# Full scraping dengan semua features
python scraper.py \
    --pages 100 \
    --format excel \
    --debug \
    --save-html \
    --checkpoint-interval 10 \
    --delay-range 1,3
```

### 4. Resume dari Checkpoint
```bash
python scraper.py --resume --pages 200
```

### 5. Debug Mode
```bash
# Analisis struktur HTML
python run_analysis.py --analyze-structure --save-debug

# Test dengan Selenium fallback
python test_debug.py --use-selenium
```

## 📈 Performance & Monitoring

### Statistics Tracking
- **Success Rate**: Percentage keberhasilan request
- **Average Response Time**: Waktu rata-rata response
- **Error Distribution**: Breakdown error berdasarkan type
- **Throughput**: Pages per minute processed

### Checkpoint System
- Auto-save progress setiap N pages
- Resume capability dari titik terakhir
- Backup data integrity checks
- Rolling checkpoint dengan retention

### Memory Management
- Efficient data structures untuk large datasets
- Garbage collection optimization
- Memory usage monitoring
- Configurable batch processing

## 🔧 Configuration

### Environment Variables
```bash
export SCRAPER_USER_AGENT="Custom User Agent"
export SCRAPER_DELAY_MIN=1
export SCRAPER_DELAY_MAX=3
export SCRAPER_TIMEOUT=30
export SCRAPER_RETRY_ATTEMPTS=3
```

### Config File (src/config.py)
```python
# Request settings
DEFAULT_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3
DELAY_RANGE = (1, 3)

# Output settings
DEFAULT_OUTPUT_FORMAT = 'json'
CHECKPOINT_INTERVAL = 50

# Debug settings
SAVE_DEBUG_HTML = True
DEBUG_LOG_LEVEL = 'INFO'
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. urllib3 Compatibility Error
```
TypeError: 'method_whitelist' parameter is not supported.
```
**Solution**: Update ke urllib3 >= 2.0 dan gunakan `allowed_methods`

#### 2. Connection Timeout
```
requests.exceptions.ConnectTimeout
```
**Solution**: Increase timeout, check network, enable debug mode

#### 3. Rate Limiting (429)
```
HTTP 429 Too Many Requests
```
**Solution**: Increase delay range, enable exponential backoff

#### 4. Anti-bot Detection
```
HTTP 403 Forbidden
```
**Solution**: Enable Selenium fallback, rotate user agents

### Debug Commands
```bash
# Full debug dengan HTML save
python example_usage.py --debug --save-html --verbose

# Network diagnostics
python test_debug.py --test-network --timeout 60

# HTML structure analysis
python run_analysis.py --analyze-structure
```

## 📊 Output Formats

### JSON Output
```json
{
  "metadata": {
    "scraped_at": "2025-08-07T15:30:00Z",
    "pages_processed": 50,
    "success_rate": 96.0
  },
  "data": [
    {
      "nomor_putusan": "123/Pdt.G/2025/PN.Jkt",
      "pengadilan": "Pengadilan Negeri Jakarta",
      "kategori": "Perdata",
      "tanggal": "2025-01-15",
      "status": "Berkekuatan Hukum Tetap"
    }
  ]
}
```

### CSV Output
```csv
nomor_putusan,pengadilan,kategori,tanggal,status
123/Pdt.G/2025/PN.Jkt,Pengadilan Negeri Jakarta,Perdata,2025-01-15,Berkekuatan Hukum Tetap
```

## 🔒 Best Practices

### Rate Limiting
- Gunakan delay 1-3 detik antar request
- Monitor response headers untuk rate limit info
- Implement exponential backoff untuk errors

### Data Integrity
- Validate data structure sebelum save
- Implement checksum untuk file integrity
- Backup checkpoint files secara berkala

### Error Handling
- Log semua errors dengan context
- Implement graceful degradation
- Monitor error rates dan patterns

## 📚 References

- [Mahkamah Agung Website](https://putusan3.mahkamahagung.go.id/)
- [Requests Documentation](https://docs.python-requests.org/)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Implement changes dengan tests
4. Update documentation
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

Untuk pertanyaan atau issues:
- Create GitHub issue dengan detail error
- Include log files dan debug output
- Specify environment (OS, Python version, dependencies)

---

**Last Updated**: 2025-08-07  
**Version**: 2.0.0  
**Compatibility**: Python 3.8+, urllib3 2.0+
