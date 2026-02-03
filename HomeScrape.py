import json
import time
from datetime import datetime
import newspaper
from newspaper import Config

# 1. SETUP & DISGUISE
USER_AGENT = 'Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT
# We set memoize_articles=False so it scrapes even if you've run the script before
config.memoize_articles = False 
config.fetch_images = False # Faster and saves bandwidth

# 2. THE HOMEPAGE TARGET
site_url = 'https://www.whidbeynewstimes.com'
print(f"[*] Scanning homepage: {site_url}")

# This builds a map of the site
site_source = newspaper.build(site_url, config=config)

print(f"[+] Found {len(site_source.articles)} potential articles!")

# 3. THE LOOP (Limiting to 5 so we don't get banned immediately)
for article in site_source.articles[:5]:
    try:
        article.download()
        article.parse()
        article.nlp()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4. DATA PACKAGE
        data = {
            "scraped_at": timestamp,
            "title": article.title,
            "text": article.text,
            "url": article.url
        }

        # 5. APPEND TO JSON (One JSON object per line)
        with open('huge_archive.json', 'a', encoding='utf-8') as f_json:
            f_json.write(json.dumps(data, ensure_ascii=False) + "\n")

        # 6. APPEND TO MARKDOWN (With Big Dividers)
        with open('huge_archive.md', 'a', encoding='utf-8') as f_md:
            f_md.write(f"\n{'='*60}\n")
            f_md.write(f"# {data['title']}\n")
            f_md.write(f"**SOURCE:** {data['url']}\n")
            f_md.write(f"**TIME:** {data['scraped_at']}\n")
            f_md.write(f"{'='*60}\n\n")
            f_md.write(f"{data['text']}\n\n")
            f_md.write(f"\n[ END OF ARTICLE ]\n")

        print(f"[+] Archived: {article.title}")
        
        # Respect the server!
        time.sleep(5)

    except Exception as e:
        print(f"[!] Skipping an article due to error: {e}")

print("\n[*] Harvest complete. Check huge_archive.md for your reading list.")