import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import newspaper
from newspaper import Config, Article

# 1. SETUP
USER_AGENT = 'Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT

# 2. THE HOMEPAGE
site_url = 'https://www.whidbeynewstimes.com'
print(f"[*] Mining links manually from: {site_url}")

try:
    # Get the homepage HTML
    response = requests.get(site_url, headers={'User-Agent': USER_AGENT}, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find every link (<a> tag) on the page
    all_links = []
    for link in soup.find_all('a', href=True):
        url = link['href']
        # Convert relative links (like /news/123) to full links
        if url.startswith('/'):
            url = site_url + url
        all_links.append(url)

    # Filter: Only keep links from the same site that look like articles
    article_urls = [u for u in all_links if site_url in u and u.count('/') > 3]
    article_urls = list(set(article_urls)) # Remove duplicates

    print(f"[+] Mined {len(article_urls)} potential articles!")

except Exception as e:
    print(f"[!] Could not read homepage: {e}")
    article_urls = []

# 3. THE HARVEST LOOP
for url in article_urls[:5]:
    try:
        print(f"[*] Extracting: {url}")
        article = Article(url, config=config)
        article.download()
        article.parse()
        
        if not article.title:
            continue
            
        article.nlp()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4. APPEND TO THE GIANT FILE
        with open('huge_archive.md', 'a', encoding='utf-8') as f_md:
            f_md.write(f"\n{'='*60}\n")
            f_md.write(f"# {article.title}\n")
            f_md.write(f"**TIME:** {timestamp} | **URL:** {url}\n")
            f_md.write(f"{'='*60}\n\n")
            f_md.write(f"{article.text}\n\n")
            f_md.write(f"\n[ END OF ARTICLE ]\n")

        print(f"[+] Saved: {article.title}")
        time.sleep(5) 

    except Exception as e:
        print(f"[!] Skip: {e}")

print("\n[*] Harvest complete.")