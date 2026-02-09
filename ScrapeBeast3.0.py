import time, sys, os, re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from newspaper import Article

# --- CLI COLORS (ANSI) ---
G, P, O, R = "\033[1;32m", "\033[1;35m", "\033[1;33m", "\033[0m"
color_map = {'NEWS': G, 'OBIT': P, 'LETTER': O}

# --- FILENAME & DATABASE ---
month_str = datetime.now().strftime("%B_%Y")
ARCHIVE_FILE = f"whidbey_{month_str}.md"
DB_FILE = 'scraped_urls.txt'

# 1. BROWSER SETUP
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

if os.path.exists(DB_FILE):
    with open(DB_FILE, 'r') as f: seen_urls = set(line.strip() for line in f)
else: seen_urls = set()

target_pages = [
    ('NEWS', 'https://www.whidbeynewstimes.com/'),
    ('NEWS', 'https://www.whidbeynewstimes.com/news/'),
    ('LETTER', 'https://www.whidbeynewstimes.com/letters/'),
    ('OBIT', 'https://www.whidbeynewstimes.com/obituaries/')
]

# 2. DISCOVERY
discovered = []
print(f"[*] Checking for new articles for {month_str.replace('_', ' ')}...")

for tag, page in target_pages:
    try:
        driver.get(page)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for link in soup.find_all('a', href=True):
            url = link['href']
            if url.startswith('/'): url = 'https://www.whidbeynewstimes.com' + url
            clean_url = url.split('?')[0].rstrip('/')
            
            # Avoid duplicates and non-article links
            if clean_url not in seen_urls and clean_url.count('-') > 2:
                if not any(item['url'] == clean_url for item in discovered):
                    discovered.append({'url': clean_url, 'tag': tag})
    except Exception as e:
        print(f"\n[!] Error scanning {page}: {e}")

if not discovered:
    print(f"{O}[!] No new articles found.{R}")
    driver.quit(); sys.exit()

# 3. HARVESTING
new_entries = []
print(f"[*] Found {len(discovered)} new items. Starting harvest...")

for index, item in enumerate(discovered, 1):
    c = color_map[item['tag']]
    sys.stdout.write(f"\r[*] {c}[{item['tag']}]{R} Scraping {index}/{len(discovered)}...")
    sys.stdout.flush()
    try:
        driver.get(item['url'])
        time.sleep(4)
        art = Article(item['url'])
        art.download(input_html=driver.page_source)
        art.parse()
        
        # Extract published date
        p_date = art.publish_date.strftime("%b %d, %Y") if art.publish_date else datetime.now().strftime("%b %d, %Y")
        
        new_entries.append({
            'title': art.title, 
            'text': art.text, 
            'url': item['url'], 
            'tag': item['tag'], 
            'pub_date': p_date
        })
        # Log to DB immediately
        with open(DB_FILE, 'a') as f: f.write(f"{item['url']}\n")
    except: continue

driver.quit()

# 4. ARCHIVE RECONSTRUCTION (The "Sandwich" Logic)
old_body = ""
old_toc_text = ""
start_num = 1

if os.path.exists(ARCHIVE_FILE):
    with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
        full_old_content = f.read()
    
    # 4a. Find the last article number
    existing_nums = re.findall(r'## (\d+)\.', full_old_content)
    if existing_nums:
        start_num = max(map(int, existing_nums)) + 1
    
    # 4b. Split the file to extract the old body and old TOC
    # We split at the first divider that separates TOC from Content
    if "\n\n---\n\n" in full_old_content:
        top_part, old_body = full_old_content.split("\n\n---\n\n", 1)
        # Pull just the TOC lines out of the top part
        toc_match = re.search(r'### Table of Contents\n(.*?)$', top_part, re.DOTALL)
        if toc_match:
            old_toc_text = toc_match.group(1).strip()

# 5. GENERATE NEW CONTENT STRINGS
new_toc_lines = ""
new_article_body = ""
for i, art in enumerate(new_entries, start_num):
    c = color_map[art['tag']]
    # TOC Line with Date
    new_toc_lines += f"{i}. {c}[{art['tag']}]{R} {art['title']} - **{art['pub_date']}** [Link](#article-{i})\n"
    # Article Header with Date
    new_article_body += f"## {i}. {c}[{art['tag']}]{R} {art['title']} <a name='article-{i}'></a>\n"
    new_article_body += f"**Date:** {art['pub_date']} | **Scraped:** {datetime.now().strftime('%Y-%m-%d')}\n"
    new_article_body += f"**Source:** {art['url']}\n\n{art['text']}\n\n---\n\n"

# 6. FINAL FILE WRITE
with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
    f.write(f"# Whidbey Archive: {month_str.replace('_', ' ')}\n\n")
    f.write("### Table of Contents\n")
    f.write(new_toc_lines)
    if old_toc_text:
        f.write(f"--- *Previous Harvests* ---\n{old_toc_text}")
    
    f.write("\n\n---\n\n") # This is our split marker
    f.write(new_article_body)
    f.write(old_body)

print(f"\n\n{G}[+] Success! Archive updated with {len(new_entries)} articles.{R}")
print(f"[*] New count starts at #{start_num}. Current Month: {ARCHIVE_FILE}")

# 7. OFFLINE HTML VIEWER (integrated)
# Generates/refreshes index.html from the markdown archive for offline use.
try:
    from HTMLwhidbey import generate_index_html_from_markdown

    out_html = generate_index_html_from_markdown(ARCHIVE_FILE, "index.html")
    print(f"[*] Offline viewer updated: {out_html}")
except Exception as e:
    print(f"[!] HTML viewer generation failed: {e}")