import json
import time
from datetime import datetime
import newspaper
from newspaper import Config, Article

# 1. SETUP
USER_AGENT = 'Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT

# 2. THE HOMEPAGE
site_url = 'https://www.whidbeynewstimes.com'
print(f"[*] Mining links from: {site_url}")

# We use the built-in link extractor which is much more stable
# This just grabs every link on the page without trying to be "smart" yet
all_links = newspaper.utils.extract_urls(site_url)

# Filter for links that look like actual articles (usually have more than 2 slashes)
# And make sure they belong to the same site
article_urls = [url for url in all_links if site_url in url and url.count('/') > 3]
article_urls = list(set(article_urls)) # Remove duplicates

print(f"[+] Mined {len(article_urls)} potential articles!")

# 3. THE LOOP
for url in article_urls[:5]:
    try:
        print(f"[*] Processing: {url}")
        article = Article(url, config=config)
        article.download()
        article.parse()
        
        # Only proceed if we actually got a title (proves it's a real article)
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

print("\n[*] Harvest complete. Check huge_archive.md")