import time
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from newspaper import Article

# 1. BROWSER SETUP (Stealth / Headless Mode)
options = Options()
options.add_argument("--headless") # GOING DARK: No window will pop up
driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

site_url = 'https://www.whidbeynewstimes.com'
SAMPLE_SIZE = 5 # You can increase this once you're ready

print(f"[*] Starting Headless Scraper for: {site_url}")

try:
    driver.get(site_url)
    print("[*] Waiting for Cloudflare verification (approx 10s)...")
    time.sleep(10) 

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    all_links = []
    for link in soup.find_all('a', href=True):
        url = link['href']
        if url.startswith('/'): url = site_url + url
        if site_url in url and '/news/' in url and url.count('-') > 2:
            all_links.append(url)

    article_urls = list(set(all_links))
    work_list = article_urls[:SAMPLE_SIZE]
    
    total = len(work_list)
    print(f"[+] Found {len(article_urls)} articles. Sample size: {total}\n")

    # 2. THE HARVEST LOOP WITH PROGRESS BAR
    for index, url in enumerate(work_list, 1):
        try:
            # Progress Bar Logic
            percent = (index / total) * 100
            bar_length = 20
            filled = int(bar_length * index // total)
            bar = '█' * filled + '-' * (bar_length - filled)
            
            # \r allows the line to overwrite itself in the CLI
            sys.stdout.write(f"\r[{bar}] {percent:.0f}% | Article {index}/{total}")
            sys.stdout.flush()

            driver.get(url)
            time.sleep(5) # Slow/Bottom approach for safety
            
            # THE FIX: Using the new newspaper4k syntax
            article = Article(url)
            article.download(input_html=driver.page_source) 
            article.parse()
            
            if len(article.text) > 100:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open('whidbey_headless.md', 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*60}\n# {article.title}\nURL: {url}\nTIME: {timestamp}\n{'='*60}\n\n{article.text}\n")
            
        except Exception as e:
            print(f"\n[!] Error on {url}: {e}")

except Exception as e:
    print(f"\n[!] Critical Failure: {e}")

finally:
    driver.quit()
    print("\n\n[*] Browser closed. Harvest stored in 'whidbey_headless.md'.")