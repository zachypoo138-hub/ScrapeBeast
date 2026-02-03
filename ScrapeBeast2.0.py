import time
import sys
import os
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from newspaper import Article

# --- CONFIG ---
DB_FILE = 'scraped_urls.txt'
ARCHIVE_FILE = 'whidbey_master.md'
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

# Load already scraped URLs
if os.path.exists(DB_FILE):
    with open(DB_FILE, 'r') as f: seen_urls = set(line.strip() for line in f)
else: seen_urls = set()

target_pages = [
    'https://www.whidbeynewstimes.com/news/',
    'https://www.whidbeynewstimes.com/letters/',
    'https://www.whidbeynewstimes.com/obituaries/'
]

# 1. DISCOVERY
all_discovered_links = []
for page in target_pages:
    driver.get(page)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    for link in soup.find_all('a', href=True):
        url = link['href']
        if url.startswith('/'): url = 'https://www.whidbeynewstimes.com' + url
        clean_url = url.split('?')[0].split('#')[0]
        if clean_url not in seen_urls and any(sec in clean_url for sec in ['/news/', '/letters/', '/obituaries/']):
            if clean_url.count('-') > 2: all_discovered_links.append(clean_url)

work_list = list(set(all_discovered_links))
if not work_list:
    print("[*] No new content. Exiting.")
    driver.quit()
    sys.exit()

# 2. THE HARVEST (Storing in memory temporarily to build TOC)
new_articles = []
for index, url in enumerate(work_list, 1):
    print(f"\r[*] Scraping {index}/{len(work_list)}...", end="")
    driver.get(url)
    time.sleep(4)
    article = Article(url)
    article.download(input_html=driver.page_source)
    article.parse()
    if len(article.text) > 100:
        new_articles.append({'title': article.title, 'text': article.text, 'url': url})
        with open(DB_FILE, 'a') as f: f.write(f"{url}\n")

driver.quit()

# 3. WRITING TO FILE (Table of Contents + Numbered Articles)
timestamp = datetime.now().strftime("%B %d, %Y")
with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
    f.write(f"# Whidbey Archive - {timestamp}\n\n")
    f.write("## Table of Contents\n")
    
    # Write TOC Links
    for i, art in enumerate(new_articles, 1):
        f.write(f"{i}. [{art['title']}](#article-{i})\n")
    
    f.write("\n---\n\n")
    
    # Write Numbered Articles
    for i, art in enumerate(new_articles, 1):
        f.write(f"## {i}. {art['title']} <a name='article-{i}'></a>\n")
        f.write(f"*Source: {art['url']}*\n\n")
        f.write(f"{art['text']}\n\n")
        f.write("---\n")

print(f"\n[+] Success! {len(new_articles)} articles saved with a Table of Contents.")