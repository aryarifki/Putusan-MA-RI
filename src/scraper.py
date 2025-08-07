import csv, os, re, time
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

BASE_URL = "https://putusan3.mahkamahagung.go.id/direktori"
OUT_DIR  = "data/raw"
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# sesi dengan retry & timeout lebih besar
session = requests.Session()
retry = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)

def get_total_pages():
    try:
        r = session.get(BASE_URL, headers=HEADERS, timeout=60)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Gagal ambil halaman awal:", e)
        return 1
    soup = BeautifulSoup(r.text, "lxml")
    last = soup.find("a", string=re.compile("Terakhir"))
    if last and "page=" in last["href"]:
        return int(last["href"].split("page=")[-1])
    return 1

def scrape_page(page_num):
    url = f"{BASE_URL}?page={page_num}"
    try:
        r = session.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Skip hal {page_num} → {e}")
        return []
    soup = BeautifulSoup(r.text, "lxml")
    rows = soup.select("table.table tbody tr")
    data = []
    for tr in rows:
        cols = tr.find_all("td")
        if len(cols) < 4:
            continue
        data.append({
            "nomor": cols[0].get_text(strip=True),
            "tgl":   cols[1].get_text(strip=True),
            "jenis": cols[2].get_text(strip=True),
            "link":  "https://putusan3.mahkamahagung.go.id" + cols[0].find("a")["href"]
        })
    return data

def scrape_all():
    total = get_total_pages()
    print(f"Total halaman: {total}")
    all_rows = []
    for p in tqdm(range(1, total + 1), desc="Scraping"):
        rows = scrape_page(p)
        all_rows.extend(rows)
        time.sleep(2)  # jeda lebih lama di jaringan HP
    csv_path = os.path.join(OUT_DIR, "direktori_putusan.csv")
    with open(csv_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nomor", "tgl", "jenis", "link"])
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Selesai! {len(all_rows)} putusan tersimpan di {csv_path}")

if __name__ == "__main__":
    scrape_all()
