import json
from datetime import datetime
import newspaper
from newspaper import Config, Article

# 1. SETUP
USER_AGENT = 'Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT

url = 'https://www.whidbeynewstimes.com/business/mosey-downtown-oak-harbor-for-winter-stroll/'
article = Article(url, config=config)

try:
    print(f"[*] Extracting full content from: {url}")
    article.download()
    article.parse()
    article.nlp() # We still run this for the tags and summary

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. THE DATA PACKAGE (Now with full_text)
    data = {
        "scraped_at": timestamp,
        "title": article.title,
        "author": article.authors,
        "tags": article.keywords,
        "summary": article.summary,
        "full_text": article.text, # This is the "Full Meaty Article"
        "url": url
    }

    # 3. SAVE TO JSON (Append mode is tricky with JSON, so we write a new entry)
    # Pro Tip: In a real project, you'd load the old JSON and add to the list
    with open('news_archive.json', 'a', encoding='utf-8') as f_json:
        f_json.write(json.dumps(data, ensure_ascii=False) + "\n")

    # 4. SAVE TO MARKDOWN (Perfect for reading)
    with open('news_archive.md', 'a', encoding='utf-8') as f_md:
        f_md.write(f"\n# {data['title']}\n")
        f_md.write(f"**Date:** {data['scraped_at']} | **Author:** {', '.join(data['author'])}\n\n")
        f_md.write(f"### The Summary\n> {data['summary']}\n\n")
        f_md.write(f"### Full Article\n{data['full_text']}\n")
        f_md.write(f"\n{'-'*40}\n")

    print(f"[+] Success! '{article.title}' added to archive.")

except Exception as e:
    print(f"[!] Error: {e}")