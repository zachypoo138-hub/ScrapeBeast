import newspaper
from newspaper import Config, Article

# 1. THE USER AGENT (Your Disguise)
# We use a real Arch Linux Chrome string so the site thinks you're a person.
USER_AGENT = 'Mozilla/5.0 (X11; Arch Linux; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'

config = Config()
config.browser_user_agent = USER_AGENT
config.request_timeout = 10  # Don't hang forever if the site is slow

# 2. THE TARGET
url = 'https://www.whidbeynewstimes.com/life/sound-waters-university-returns-to-coupeville/'

# 3. THE EXECUTION
article = Article(url, config=config)

try:
    article.download()
    article.parse()
    article.nlp() # This generates the keywords/summary

    print(f"--- SCRAPE SUCCESS ---")
    print(f"TITLE:    {article.title}")
    print(f"AUTHOR:   {', '.join(article.authors)}")
    
    # TAGS/KEYWORDS: Newspaper4k extracts these from the meta tags automatically
    print(f"TAGS:     {', '.join(article.keywords)}")
    
    print(f"\nCONTENT SUMMARY:\n{article.summary[:500]}...")

except Exception as e:
    print(f"--- SCRAPE FAILED ---")
    print(f"Reason: {e}")