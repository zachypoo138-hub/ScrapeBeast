import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from newspaper import Article

# 1. BROWSER SETUP (The "Real Human" Tank)
options = Options()
# options.add_argument("--headless") # Comment this out to WATCH it work!
driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

site_url = 'https://www.whidbeynewstimes.com'
print(f"[*] Opening browser to: {site_url}")

try:
    # 2. THE SLOW APPROACH
    driver.get(site_url)
    print("[*] Waiting 10 seconds for Cloudflare to 'Verify' us...")
    time.sleep(10) # Give it plenty of time to pass the "I am human" check

    # 3. MINE THE LINKS FROM THE REAL PAGE
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    all_links = []
    for link in soup.find_all('a', href=True):
        url = link['href']
        if url.startswith('/'): url = site_url + url
        
        # Whidbey News-Times specific pattern
        if site_url in url and '/news/' in url and url.count('-') > 2:
            all_links.append(url)

    article_urls = list(set(all_links))
    print(f"[+] Found {len(article_urls)} articles while masquerading as a real browser.")

    # 4. THE HARVEST
    for index, url in enumerate(article_urls[:3], 1): # Smallest sample possible
        print(f"[{index}/3] Reading: {url}")
        driver.get(url)
        time.sleep(5) # Slow and steady
        
        # Use newspaper to parse the text from the browser's current view
        article = Article(url)
        article.set_html(driver.page_source)
        article.parse()
        
        if len(article.text) > 100:
            with open('whidbey_slow_archive.md', 'a', encoding='utf-8') as f:
                f.write(f"\n# {article.title}\n{article.text}\n")
            print(f"    [+] Saved: {article.title}")

finally:
    driver.quit()
    print("[*] Browser closed.")