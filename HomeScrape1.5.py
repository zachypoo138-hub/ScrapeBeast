import time
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from newspaper import Config, Article

# 1. THE STEALTH SETUP
# cloudscraper creates a session that can solve Cloudflare challenges
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'linux',
        'desktop': True
    }
)

config = Config()
config.browser_user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'

site_url = 'https://www.whidbeynewstimes.com'
print(f"[*] Stealth targeting: {site_url}")

try:
    # 2. THE STEALTH HANDSHAKE
    response = scraper.get(site_url, timeout=15)
    print(f"[*] Response Code: {response.status_code}")
    
    if response.status_code != 200:
        print("[-] Blocked by the server. We might need a slower approach.")
    else:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look specifically for Whidbey's article patterns
        # They often use specific classes for their news links
        all_links = []
        for link in soup.find_all('a', href=True):
            url = link['href']
            if url.startswith('/'):
                url = site_url + url
            
            # Whidbey News-Times usually puts articles in /news/ or /business/
            if site_url in url and any(cat in url for cat in ['/news/', '/business/', '/life/', '/sports/']):
                # Only keep 'deep' links (usually the ones with more dashes)
                if url.count('-') > 2:
                    all_links.append(url)

        article_urls = list(set(all_links))
        print(f"[+] Successfully bypassed protection! Found {len(article_urls)} articles.")

        # 3. THE HARVEST
        for index, url in enumerate(article_urls[:5], 1):
            try:
                print(f"[{index}/5] Downloading: {url}")
                
                # Use the scraper to get the article HTML, then feed it to Newspaper
                article_html = scraper.get(url).text
                article = Article(url, config=config)
                article.set_html(article_html)
                article.parse()
                
                if len(article.text) < 200:
                    continue

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with open('whidbey_archive.md', 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*60}\n# {article.title}\n{url}\n{'='*60}\n\n{article.text}\n")

                print(f"    [+] Saved: {article.title}")
                time.sleep(5) # Local papers need a gentle touch

            except Exception as e:
                print(f"    [!] Error: {e}")

except Exception as e:
    print(f"[!] Scraper failed: {e}")