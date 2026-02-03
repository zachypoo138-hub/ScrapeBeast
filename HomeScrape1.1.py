import json
import time
from datetime import datetime
import newspaper
from newspaper import Config, Article

# 1. SETUP & DISGUISE
USER_AGENT = 'Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT
config.request_timeout = 10

# 2. THE HOMEPAGE TARGET
site_url = 'www.whidbeynewstimes.com'
print(f"[*] Scanning homepage: {site_url}")

# BYPASSING build() TO AVOID THE XPATH ERROR
# We use newspaper.popular_urls() or just get the links manually
article_urls = newspaper.popular_urls(site_url)

# If popular_urls returns nothing, we can try this backup discovery:
if not article_urls:
    # This is a 'Lite' version of build that is less likely to crash
    temp_source = newspaper.Source(site_url, config=config)
    temp_source.download()
    temp_source.parse()
    # We only take the articles it found without doing the 'feed' discovery
    article_urls = [a.url for a in temp_source.articles]

print(f"[+] Found {len(article_urls)} potential articles!")

# 3. THE LOOP (One giant file, formatted)
for url in article_urls[:5]: # Still limiting to 5 for safety
    try:
        # We check if the URL is valid/absolute
        if not url.startswith('http'):
            continue

        print(f"[*] Extracting: {url}")
        article = Article(url, config=config)
        article.download()
        article.parse()
        article.nlp()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data = {
            "scraped_at": timestamp,
            "title": article.title,
            "text": article.text,
            "url": url
        }

        # 4. APPEND TO THE GIANT MARKDOWN FILE
        with open('huge_archive.md', 'a', encoding='utf-8') as f_md:
            f_md.write(f"\n{'='*60}\n")
            f_md.write(f"# {data['title']}\n")
            f_md.write(f"**TIME:** {data['scraped_at']} | **SOURCE:** {data['url']}\n")
            f_md.write(f"{'='*60}\n\n")
            f_md.write(f"{data['text']}\n\n")
            f_md.write(f"\n[ END OF ARTICLE ]\n")

        print(f"[+] Successfully archived: {article.title}")
        time.sleep(5) # The "Don't Ban Me" pause

    except Exception as e:
        print(f"[!] Error on {url}: {e}")

print("\n[*] Finished. Your 'huge_archive.md' is ready.")