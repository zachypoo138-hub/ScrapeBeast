import json
from datetime import datetime
import newspaper
from newspaper import Config, Article

# 1. SETUP & DISGUISE
USER_AGENT = 'Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT

url = 'https://www.whidbeynewstimes.com/news/no-firearms-involved-in-fight-after-racist-remark-outside-school/'
article = Article(url, config=config)

try:
    print(f"[*] Fetching: {url}")
    article.download()
    article.parse()
    article.nlp()

    # 2. GENERATE TIMESTAMP
    # Format: 2026-02-03 14:30:05
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3. THE DATA PACKAGE
    data = {
        "scraped_at": timestamp,
        "title": article.title,
        "author": article.authors,
        "tags": article.keywords,
        "summary": article.summary,
        "url": url
    }

    # 4. SAVE TO JSON
    with open('news_data.json', 'w', encoding='utf-8') as f_json:
        json.dump(data, f_json, indent=4, ensure_ascii=False)
    print(f"[+] JSON updated at {timestamp}")

    # 5. SAVE TO MARKDOWN
    with open('news_reader.md', 'w', encoding='utf-8') as f_md:
        f_md.write(f"# {data['title']}\n")
        f_md.write(f"**Scraped on:** {data['scraped_at']}\n\n")
        f_md.write(f"**By:** {', '.join(data['author'])}\n")
        f_md.write(f"**Keywords:** {', '.join(data['tags'][:10])}\n\n")
        f_md.write(f"## Summary\n{data['summary']}\n\n")
        f_md.write(f"---\n*Source: {data['url']}*")
    print(f"[+] Markdown updated at {timestamp}")

except Exception as e:
    print(f"[!] Error: {e}")