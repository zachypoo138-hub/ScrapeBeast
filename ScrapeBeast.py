import time
import sys
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from newspaper import Article

# --- CONFIGURATION ---
DB_FILE = 'scraped_urls.txt'
ARCHIVE_FILE = 'whidbey_master_archive.md'
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

# 1. LOAD MEMORY
if os.path.exists(DB_FILE):
    with open(DB_FILE, 'r') as f:
        seen_urls = set(line.strip() for line in f)
else:
    seen_urls = set()

site_url = 'https://www.whidbeynewstimes.com'
sections = ['/news/', '/letters/', '/obituaries/']

print(f"[*] UNLEASHED: Targeting News, Letters, and Obits at {site_url}")

try:
    driver.get(site_url)
    time.sleep(10) # Cloudflare handshake

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    all_links = []
    
    # 2. COLLECT ALL RELEVANT LINKS
    for link in soup.find_all('a', href=True):
        url = link['href']
        if url.startswith('/'): url = site_url + url
        
        # Check if URL belongs to our desired sections
        if site_url in url and any(sec in url for sec in sections):
            if url not in seen_urls and url.count('-') > 2:
                all_links.append(url)

    work_list = list(set(all_links))
    total = len(work_list)
    
    if total == 0:
        print("[!] No new articles found since last run.")
    else:
        print(f"[+] Found {total} NEW articles to scrape!")

    # 3. THE HARVEST
    for index, url in enumerate(work_list, 1):
        try:
            # Progress Bar
            percent = (index / total) * 100
            sys.stdout.write(f"\r[PROGRESS] {percent:.0f}% | {index}/{total} | {url[:50]}...")
            sys.stdout.flush()

            driver.get(url)
            time.sleep(5) 
            
            article = Article(url)
            article.download(input_html=driver.page_source)
            article.parse()
            
            if len(article.text) > 100:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Save to Master Archive
                with open(ARCHIVE_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*60}\n# {article.title}\nURL: {url}\nDATE: {timestamp}\n{'='*60}\n\n{article.text}\n")
                
                # Update Memory
                with open(DB_FILE, 'a') as f:
                    f.write(f"{url}\n")
                seen_urls.add(url)

        except Exception as e:
            print(f"\n[!] Error on {url}: {e}")

finally:
    driver.quit()
    print(f"\n\n[*] Run Complete. Archive updated: {ARCHIVE_FILE}")