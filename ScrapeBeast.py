
import time, sys, os, re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
from newspaper import Article

# --- HTML GENERATION LIB (Merged from HTMLwhidbey.py) ---
import html
import textwrap
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

TAILWIND_CDN = "https://cdn.tailwindcss.com"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

@dataclass(frozen=True)
class ArticleItem:
    id: str
    title: str
    snippet: str
    text: str
    pub_date: str | None = None
    tag: str | None = None

def _coalesce(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip() != "":
            return v
    return None

def _make_snippet(text: str, max_chars: int = 260) -> str:
    text = sanitize_text(text)
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1].rsplit(" ", 1)[0]
    if not cut:
        cut = text[: max_chars - 1]
    return cut + "…"

def sanitize_text(s: str | None) -> str:
    """
    Remove ANSI color codes and obvious markdown-y noise so cards stay clean.
    """
    if not s:
        return ""
    s = ANSI_RE.sub("", s)
    s = s.replace("\u00a0", " ")
    # Drop common archive metadata lines that can sneak into snippets
    s = re.sub(r"^\*\*Date:\*\*.*$", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\*\*Scraped:\*\*.*$", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\*\*Source:\*\*.*$", "", s, flags=re.MULTILINE)
    # De-markdown a bit (best-effort)
    s = s.replace("**", "")
    s = s.replace("__", "")
    s = s.replace("*", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_articles(raw_items: Iterable[dict[str, Any]]) -> list[ArticleItem]:
    normalized: list[ArticleItem] = []
    for idx, raw in enumerate(raw_items, 1):
        if not isinstance(raw, dict):
            continue
        title = _coalesce(raw, "title", "headline", "name")
        snippet = _coalesce(raw, "snippet", "summary", "description")
        text = _coalesce(raw, "text", "content", "body")
        pub_date = _coalesce(raw, "pub_date", "published", "date")
        tag = _coalesce(raw, "tag", "category", "section")

        if not title:
            continue

        clean_title = sanitize_text(str(title))
        snippet_str = sanitize_text(str(snippet)) if snippet is not None else _make_snippet(str(text or ""))
        if not snippet_str:
            snippet_str = "No summary available."

        clean_text = sanitize_text(str(text or ""))
        if not clean_text:
            clean_text = "No article content available (this item did not include full text)."

        normalized.append(
            ArticleItem(
                id=f"article-{idx}",
                title=clean_title.strip(),
                snippet=snippet_str,
                text=clean_text,
                pub_date=sanitize_text(str(pub_date)).strip() if pub_date is not None else None,
                tag=sanitize_text(str(tag)).strip() if tag is not None else None,
            )
        )
    return normalized

def best_effort_parse_markdown_archive(md_path: Path) -> list[dict[str, Any]]:
    """
    Attempts to parse files produced by ScrapeBeast.
    """
    text = md_path.read_text(encoding="utf-8", errors="replace")

    # decorated shape:
    # **Source:** url
    simple = re.compile(r"^\*\*Source:\*\*\s+(?P<url>\S+)\s*$", re.MULTILINE)
    title_line = re.compile(r"^##\s+\d+\.\s+(?P<title>.+?)(?:\s+<a name='article-\d+'></a>)?\s*$", re.MULTILINE)
    titles = list(title_line.finditer(text))
    if not titles:
        # Fallback to simple shape if no titles found
        return []

    items: list[dict[str, Any]] = []
    for idx, tm in enumerate(titles):
        start = tm.end()
        end = titles[idx + 1].start() if idx + 1 < len(titles) else len(text)
        chunk = text[start:end]
        url_m = simple.search(chunk)
        url = url_m.group("url").strip() if url_m else None
        body = chunk
        body = re.sub(r"^\*\*Date:\*\*.*$", "", body, flags=re.MULTILINE)
        body = re.sub(r"^\*\*Source:\*\*.*$", "", body, flags=re.MULTILINE)
        body = re.sub(r"^\*\*Scraped:\*\*.*$", "", body, flags=re.MULTILINE)
        body = sanitize_text(body)
        if url:
            items.append({"title": sanitize_text(tm.group("title")).strip(), "url": url, "text": body})
    return items

def render_html(items: list[ArticleItem], last_scraped: str) -> str:
    def esc(s: str) -> str:
        return html.escape(s, quote=True)

    cards = []
    for it in items:
        badge = ""
        if it.tag:
            badge = (
                f"<span class=\"inline-flex items-center rounded-full bg-slate-900/5 px-2.5 py-1 "
                f"text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-900/10\">{esc(it.tag)}</span>"
            )
        date = f"<div class=\"text-xs text-slate-500\">{esc(it.pub_date)}</div>" if it.pub_date else ""

        cards.append(
            "\n".join(
                [
                    "<article class=\"group rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm "
                    "transition hover:-translate-y-0.5 hover:shadow-md\">",
                    "  <div class=\"flex items-start justify-between gap-4\">",
                    "    <div class=\"min-w-0\">",
                    f"      <h2 class=\"text-lg font-semibold leading-snug text-slate-900\">{esc(it.title)}</h2>",
                    f"      <div class=\"mt-2 flex flex-wrap items-center gap-2\">{badge}{date}</div>",
                    "    </div>",
                    "  </div>",
                    f"  <p class=\"mt-4 text-sm leading-6 text-slate-600\">{esc(it.snippet)}</p>",
                    "  <div class=\"mt-6\">",
                    f"    <a href=\"#{esc(it.id)}\" "
                    "class=\"inline-flex items-center justify-center rounded-xl bg-slate-900 px-4 py-2 "
                    "text-sm font-medium text-white shadow-sm transition hover:bg-slate-800 focus:outline-none "
                    "focus:ring-2 focus:ring-slate-400 focus:ring-offset-2\">"
                    "Read</a>",
                    "  </div>",
                    "</article>",
                ]
            )
        )

    cards_html = "\n".join(cards) if cards else "<div class=\"text-slate-600\">No items to display.</div>"

    full_articles = []
    for it in items:
        badge = ""
        if it.tag:
            badge = (
                f"<span class=\"inline-flex items-center rounded-full bg-slate-900/5 px-2.5 py-1 "
                f"text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-900/10\">{esc(it.tag)}</span>"
            )
        date = f"<span class=\"text-xs text-slate-500\">{esc(it.pub_date)}</span>" if it.pub_date else ""

        # Preserve paragraph breaks for readability
        paragraphs = [p.strip() for p in it.text.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [it.text]
        body_html = "\n".join(
            f"<p class=\"mt-4 text-sm leading-7 text-slate-700\">{esc(p)}</p>" for p in paragraphs
        )

        full_articles.append(
            "\n".join(
                [
                    f"<section id=\"{esc(it.id)}\" class=\"scroll-mt-24\">",
                    "  <div class=\"rounded-2xl border border-slate-200/70 bg-white p-7 shadow-sm\">",
                    "    <div class=\"flex flex-col gap-2 md:flex-row md:items-baseline md:justify-between\">",
                    f"      <h2 class=\"text-2xl font-semibold tracking-tight\">{esc(it.title)}</h2>",
                    f"      <div class=\"flex flex-wrap items-center gap-2\">{badge}{date}</div>",
                    "    </div>",
                    f"    {body_html}",
                    "    <div class=\"mt-8\">",
                    "      <a href=\"#top\" class=\"text-sm font-medium text-slate-700 hover:text-slate-900\">Back to top</a>",
                    "    </div>",
                    "  </div>",
                    "</section>",
                ]
            )
        )

    full_html = "\n".join(full_articles)

    return textwrap.dedent(
        f"""\
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Whidbey Viewer</title>
            <script src="{TAILWIND_CDN}"></script>
            <style>
              /* subtle, high-end feel */
              body {{
                background:
                  radial-gradient(1200px 500px at 20% 0%, rgba(15, 23, 42, 0.06), transparent 60%),
                  radial-gradient(900px 400px at 80% 10%, rgba(99, 102, 241, 0.06), transparent 55%),
                  #f8fafc;
              }}
            </style>
          </head>
          <body class="text-slate-900 antialiased">
            <div id="top" class="mx-auto max-w-6xl px-6 py-12">
              <header class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div>
                  <div class="text-xs font-medium tracking-widest text-slate-500">WHIDBEY VIEWER</div>
                  <h1 class="mt-2 text-3xl font-semibold tracking-tight">Latest Scrape</h1>
                  <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                    Minimalist cards with fast scanning, clean typography, and lots of whitespace.
                  </p>
                </div>
                <div class="rounded-2xl border border-slate-200/70 bg-white/70 px-4 py-3 text-sm text-slate-700 shadow-sm backdrop-blur">
                  <span class="text-slate-500">Last Scraped:</span>
                  <span class="font-medium">{html.escape(last_scraped)}</span>
                </div>
              </header>

              <main class="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2">
                {cards_html}
              </main>

              <div class="mt-14 border-t border-slate-200/70 pt-10">
                <div class="text-xs font-medium tracking-widest text-slate-500">ARTICLES</div>
                <div class="mt-6 flex flex-col gap-8">
                  {full_html}
                </div>
              </div>

              <div class="fixed bottom-6 right-6 z-50">
                  <span class="inline-flex items-center rounded-full bg-indigo-600 px-3 py-1 text-xs font-medium text-white shadow-lg ring-1 ring-inset ring-indigo-500">
                      Generated by ScrapeBeast
                  </span>
              </div>
            </div>
          </body>
        </html>
        """
    )


def _infer_last_scraped(source_path: Path | None) -> str:
    if source_path and source_path.exists():
        ts = datetime.fromtimestamp(source_path.stat().st_mtime)
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_index_html_from_markdown(md_path: str | Path, out_path: str | Path = "index.html") -> Path:
    """
    Direct function to generate HTML from Markdown archive.
    """
    mdp = Path(md_path).expanduser()
    raw = best_effort_parse_markdown_archive(mdp)
    items = normalize_articles(raw)
    last_scraped = _infer_last_scraped(mdp)

    outp = Path(out_path).expanduser()
    outp.write_text(render_html(items, last_scraped), encoding="utf-8")
    return outp.resolve()

# --- END HTML GENERATION LIB ---

# --- CLI COLORS (ANSI) ---
G, P, O, R = "\033[1;32m", "\033[1;35m", "\033[1;33m", "\033[0m"
color_map = {'NEWS': G, 'OBIT': P, 'LETTER': O}

# --- FILENAME & DATABASE ---
month_str = datetime.now().strftime("%B_%Y")
ARCHIVE_FILE = f"whidbey_{month_str}.md"
DB_FILE = 'scraped_urls.txt'

# 1. BROWSER SETUP
options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)

if os.path.exists(DB_FILE):
    with open(DB_FILE, 'r') as f: seen_urls = set(line.strip() for line in f)
else: seen_urls = set()

target_pages = [
    ('NEWS', 'https://www.whidbeynewstimes.com/'),
    ('NEWS', 'https://www.whidbeynewstimes.com/news/'),
    ('LETTER', 'https://www.whidbeynewstimes.com/letters/'),
    ('OBIT', 'https://www.whidbeynewstimes.com/obituaries/')
]

# 2. DISCOVERY
discovered = []
print(f"[*] Checking for new articles for {month_str.replace('_', ' ')}...")

for tag, page in target_pages:
    try:
        driver.get(page)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for link in soup.find_all('a', href=True):
            url = link['href']
            if url.startswith('/'): url = 'https://www.whidbeynewstimes.com' + url
            clean_url = url.split('?')[0].rstrip('/')
            
            # Avoid duplicates and non-article links
            if clean_url not in seen_urls and clean_url.count('-') > 2:
                if not any(item['url'] == clean_url for item in discovered):
                    discovered.append({'url': clean_url, 'tag': tag})
    except Exception as e:
        print(f"\n[!] Error scanning {page}: {e}")

if not discovered:
    print(f"{O}[!] No new articles found.{R}")
    driver.quit()
    
    # Even if no new articles, we might want to regenerate index.html if it's missing?
    # Or just exit. For now, let's just make sure the viewer is up to date if the file exists.
    if os.path.exists(ARCHIVE_FILE):
         print(f"[*] Updating viewer from existing archive...")
         try:
            out_html = generate_index_html_from_markdown(ARCHIVE_FILE, "index.html")
            print(f"[*] Offline viewer updated: {out_html}")
            # Try to open it
            webbrowser.open(f"file://{out_html}")
         except Exception as e:
            print(f"[!] HTML viewer generation failed: {e}")
            
    sys.exit()

# 3. HARVESTING
new_entries = []
print(f"[*] Found {len(discovered)} new items. Starting harvest...")

for index, item in enumerate(discovered, 1):
    c = color_map[item['tag']]
    sys.stdout.write(f"\r[*] {c}[{item['tag']}]{R} Scraping {index}/{len(discovered)}...")
    sys.stdout.flush()
    try:
        driver.get(item['url'])
        time.sleep(4)
        art = Article(item['url'])
        art.download(input_html=driver.page_source)
        art.parse()
        
        # Extract published date
        p_date = art.publish_date.strftime("%b %d, %Y") if art.publish_date else datetime.now().strftime("%b %d, %Y")
        
        new_entries.append({
            'title': art.title, 
            'text': art.text, 
            'url': item['url'], 
            'tag': item['tag'], 
            'pub_date': p_date
        })
        # Log to DB immediately
        with open(DB_FILE, 'a') as f: f.write(f"{item['url']}\n")
    except: continue

driver.quit()

# 4. ARCHIVE RECONSTRUCTION (The "Sandwich" Logic)
old_body = ""
old_toc_text = ""
start_num = 1

if os.path.exists(ARCHIVE_FILE):
    with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
        full_old_content = f.read()
    
    # 4a. Find the last article number
    existing_nums = re.findall(r'## (\d+)\.', full_old_content)
    if existing_nums:
        start_num = max(map(int, existing_nums)) + 1
    
    # 4b. Split the file to extract the old body and old TOC
    # We split at the first divider that separates TOC from Content
    if "\n\n---\n\n" in full_old_content:
        top_part, old_body = full_old_content.split("\n\n---\n\n", 1)
        # Pull just the TOC lines out of the top part
        toc_match = re.search(r'### Table of Contents\n(.*?)$', top_part, re.DOTALL)
        if toc_match:
            old_toc_text = toc_match.group(1).strip()

# 5. GENERATE NEW CONTENT STRINGS
new_toc_lines = ""
new_article_body = ""
for i, art in enumerate(new_entries, start_num):
    c = color_map[art['tag']]
    # TOC Line with Date
    new_toc_lines += f"{i}. {c}[{art['tag']}]{R} {art['title']} - **{art['pub_date']}** [Link](#article-{i})\n"
    # Article Header with Date
    new_article_body += f"## {i}. {c}[{art['tag']}]{R} {art['title']} <a name='article-{i}'></a>\n"
    new_article_body += f"**Date:** {art['pub_date']} | **Scraped:** {datetime.now().strftime('%Y-%m-%d')}\n"
    new_article_body += f"**Source:** {art['url']}\n\n{art['text']}\n\n---\n\n"

# 6. FINAL FILE WRITE
with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
    f.write(f"# Whidbey Archive: {month_str.replace('_', ' ')}\n\n")
    f.write("### Table of Contents\n")
    f.write(new_toc_lines)
    if old_toc_text:
        f.write(f"--- *Previous Harvests* ---\n{old_toc_text}")
    
    f.write("\n\n---\n\n") # This is our split marker
    f.write(new_article_body)
    f.write(old_body)

print(f"\n\n{G}[+] Success! Archive updated with {len(new_entries)} articles.{R}")
print(f"[*] New count starts at #{start_num}. Current Month: {ARCHIVE_FILE}")

# 7. OFFLINE HTML VIEWER (Integrated)
try:
    out_html = generate_index_html_from_markdown(ARCHIVE_FILE, "index.html")
    print(f"[*] Offline viewer updated: {out_html}")
    webbrowser.open(f"file://{out_html}")
except Exception as e:
    print(f"[!] HTML viewer generation failed: {e}")
