"""
HTMLwhidbey.py
---------------
Generate a clean, modern index.html "viewer" for scraped news items.

Supports:
  - JSON input: a file containing a list of article dicts
  - Python module input: a module path exporting a list variable (default: `articles`)
  - Fallback: attempt to parse a Whidbey markdown archive (best-effort)

Expected article fields (flexible):
  - title (or headline)
  - url (or link)
  - text (or content)  -> used to make snippet if snippet/summary not provided
  - snippet/summary (optional)
  - pub_date/date (optional)
  - tag/category (optional)
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import textwrap
import webbrowser
from dataclasses import dataclass
from datetime import datetime
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


def load_from_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # common wrapper shapes: {"articles": [...]}
        for k in ("articles", "items", "results", "data"):
            if isinstance(data.get(k), list):
                return data[k]  # type: ignore[return-value]
        raise ValueError("JSON was an object but no list found under common keys (articles/items/results/data).")
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of objects (or an object containing a list).")
    return data  # type: ignore[return-value]


def load_from_py_module(module_path: Path, var_name: str = "articles") -> list[dict[str, Any]]:
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    raw = getattr(module, var_name, None)
    if raw is None:
        raise AttributeError(f"Module does not export `{var_name}`")
    if not isinstance(raw, list):
        raise TypeError(f"`{var_name}` must be a list (got {type(raw).__name__})")
    return raw  # type: ignore[return-value]


def best_effort_parse_markdown_archive(md_path: Path) -> list[dict[str, Any]]:
    """
    Attempts to parse files produced by ScrapeBeast2.0 / ScrapeBeast3.0.
    This is not perfect, but gives you a viewer even if you only have the .md archive.
    """
    text = md_path.read_text(encoding="utf-8", errors="replace")

    # ScrapeBeast2.0 shape:
    # ## {i}. Title <a name='article-i'></a>
    # *Source: URL*
    # body...
    pattern = re.compile(
        r"^##\s+\d+\.\s+(?P<title>.+?)\s+<a name='article-\d+'></a>\s*\n"
        r"\*Source:\s+(?P<url>.+?)\*\s*\n\n"
        r"(?P<body>.*?)(?:\n---\n|$)",
        re.MULTILINE | re.DOTALL,
    )

    items: list[dict[str, Any]] = []
    for m in pattern.finditer(text):
        title = m.group("title").strip()
        url = m.group("url").strip()
        body = m.group("body").strip()
        items.append({"title": title, "url": url, "text": body})

    if items:
        return items

    # ScrapeBeast3.0 shape is more decorated; fall back to simpler extraction:
    # **Source:** url
    simple = re.compile(r"^\*\*Source:\*\*\s+(?P<url>\S+)\s*$", re.MULTILINE)
    title_line = re.compile(r"^##\s+\d+\.\s+(?P<title>.+?)(?:\s+<a name='article-\d+'></a>)?\s*$", re.MULTILINE)
    titles = list(title_line.finditer(text))
    if not titles:
        return []

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

              <footer class="mt-14 text-xs text-slate-500">
                Generated by <span class="font-medium text-slate-700">HTMLwhidbey.py</span>
              </footer>
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
    Library-friendly entrypoint so scrapers can call this directly.
    """
    mdp = Path(md_path).expanduser()
    raw = best_effort_parse_markdown_archive(mdp)
    items = normalize_articles(raw)
    last_scraped = _infer_last_scraped(mdp)

    outp = Path(out_path).expanduser()
    outp.write_text(render_html(items, last_scraped), encoding="utf-8")
    return outp.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate index.html viewer from scraped items (JSON/list/module/markdown)."
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        type=str,
        default=None,
        help="Path to JSON file containing a list of article dicts (or object with key `articles`).",
    )
    parser.add_argument(
        "--py",
        dest="py_path",
        type=str,
        default=None,
        help="Path to a .py module exporting a list variable (default: `articles`).",
    )
    parser.add_argument(
        "--var",
        dest="var_name",
        type=str,
        default="articles",
        help="Variable name to read from --py module (default: articles).",
    )
    parser.add_argument(
        "--md",
        dest="md_path",
        type=str,
        default=None,
        help="Path to a markdown archive to parse (best-effort).",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        type=str,
        default="index.html",
        help="Output HTML path (default: index.html).",
    )
    args = parser.parse_args()

    src_path: Path | None = None
    raw: list[dict[str, Any]] = []

    if args.json_path:
        src_path = Path(args.json_path).expanduser()
        raw = load_from_json(src_path)
    elif args.py_path:
        src_path = Path(args.py_path).expanduser()
        raw = load_from_py_module(src_path, args.var_name)
    elif args.md_path:
        src_path = Path(args.md_path).expanduser()
        raw = best_effort_parse_markdown_archive(src_path)
    else:
        # convenience defaults: look for common files
        cwd = Path.cwd()
        for candidate in ("articles.json", "whidbey_articles.json"):
            p = cwd / candidate
            if p.exists():
                src_path = p
                raw = load_from_json(p)
                break
        if not raw:
            # try newest whidbey_*.md from ScrapeBeast3.0
            md_candidates = sorted(cwd.glob("whidbey_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if md_candidates:
                src_path = md_candidates[0]
                raw = best_effort_parse_markdown_archive(src_path)

    items = normalize_articles(raw)
    last_scraped = _infer_last_scraped(src_path)

    out_path = Path(args.out_path).expanduser()
    out_path.write_text(render_html(items, last_scraped), encoding="utf-8")

    abs_out = out_path.resolve()
    print(f"[+] Wrote {abs_out} ({len(items)} items)")

    # Auto-open in browser (can be disabled for cron)
    if os.environ.get("HTMLWHIDBEY_NO_OPEN", "").strip() not in ("1", "true", "yes", "on"):
        webbrowser.open(f"file://{abs_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

