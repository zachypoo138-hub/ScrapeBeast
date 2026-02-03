import json
import newspaper
from newspaper import Config, Article

# 1. SETUP (The "ThinkPad Disguise")
USER_AGENT = 'Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
config = Config()
config.browser_user_agent = USER_AGENT

url = 'https://www.whidbeynewstimes.com/news/oak-harbor-adopts-speed-zone-reductions/'
article = Article(url, config=config)

try:
    print(f"[*] Fetching: {url}")
    article.download()
    article.parse()
    article.nlp()

    # 2. THE DATA PACKAGE
    # We organize it once so we can use it for both files
    data = {
        "title": article.title,
        "author": article.authors,
        "tags": article.keywords,
        "summary": article.summary,
        "url": url
    }

    # 3. SAVE TO JSON (The Database)
    # We use 'a' to append or 'w' to overwrite - let's use 'w' for a clean test
    with open('news_data.json', 'w', encoding='utf-8') as f_json:
        json.dump(data, f_json, indent=4, ensure_ascii=False)
    print("[+] JSON saved: news_data.json")

    # 4. SAVE TO MARKDOWN (The Reader)
    with open('news_reader.md', 'w', encoding='utf-8') as f_md:
        f_md.write(f"# {data['title']}\n\n")
        f_md.write(f"**By:** {', '.join(data['author'])}\n")
        f_md.write(f"**Keywords:** {', '.join(data['tags'][:10])}\n\n")
        f_md.write(f"## Summary\n{data['summary']}\n\n")
        f_md.write(f"---\n*Source: {data['url']}*")
    print("[+] Markdown saved: news_reader.md")

except Exception as e:
    print(f"[!] Error occurred: {e}")