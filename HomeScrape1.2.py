import json
import time
from datetime import datetime
import newspaper
from newspaper import Config, Article, Source

# 1. SETUP
USER_AGENT = 'Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT
config.memoize_articles = False 

# 2. THE HOMEPAGE
site_url = 'https://www.whidbeynewstimes.com'
print(f"[*] Manual Scanning: {site_url}")

# We create the 'Source' manually
# This avoids the build() function that was crashing for you
portal = Source(site_url, config=config)
portal.download()
portal.parse()

# This tells the library to find the article links on the page we just downloaded
portal.generate_articles()

print(f"[+] Found {len(portal.articles)} potential articles!")

# 3. THE HARVEST
# Let's grab 5 to test
for article in portal.articles[:5]:
    try:
        print(f"[*] Downloading: {article.url}")
        
        # We need to call download/parse on each individual article object
        article.download()
        article.parse()
        article.nlp()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4. SAVE TO THE GIANT FILE
        with open('huge_archive.md', 'a', encoding='utf-8') as f_md:
            f_md.write(f"\n{'='*60}\n")
            f_md.write(f"# {article.title}\n")
            f_md.write(f"**TIME:** {timestamp} | **URL:** {article.url}\n")
            f_md.write(f"{'='*60}\n\n")
            f_md.write(f"{article.text}\n\n")
            f_md.write(f"\n[ END OF ARTICLE ]\n")

        print(f"[+] Saved: {article.title}")
        time.sleep(3) # Be nice to the server

    except Exception as e:
        print(f"[!] Error on an article: {e}")

print("\n[*] Harvest complete. Check your huge_archive.md!")