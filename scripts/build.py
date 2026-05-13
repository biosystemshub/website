#!/usr/bin/env python3
"""
BiosystemsHub build script
==========================
Scans the articles/ folder, extracts article metadata from each HTML file,
and regenerates:
  - data/articles.json        (metadata index for all articles)
  - articles/index.html       (filterable article listing page)
  - index.html featured block (the 3 latest articles on the homepage)

Usage:
  python scripts/build.py

No third-party packages required — uses Python standard library only.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser

# ── Paths ────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent
ARTICLES_DIR = ROOT / 'articles'
DATA_DIR     = ROOT / 'data'


# ── Metadata extraction ──────────────────────────────────────

class _MetaExtractor(HTMLParser):
    """Minimal HTML parser that extracts the article-meta JSON block."""

    def __init__(self):
        super().__init__()
        self._in_meta  = False
        self._buf      = []
        self.meta_json = None

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            attr_dict = dict(attrs)
            if attr_dict.get('id') == 'article-meta':
                self._in_meta = True
                self._buf = []

    def handle_endtag(self, tag):
        if tag == 'script' and self._in_meta:
            self._in_meta  = False
            self.meta_json = ''.join(self._buf).strip()

    def handle_data(self, data):
        if self._in_meta:
            self._buf.append(data)


def parse_article_meta(filepath: Path) -> dict | None:
    """Return article metadata dict from an HTML file, or None if missing/invalid."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except OSError as exc:
        print(f'  [error] Cannot read {filepath.name}: {exc}', file=sys.stderr)
        return None

    parser = _MetaExtractor()
    parser.feed(content)

    if parser.meta_json is None:
        return None

    try:
        meta = json.loads(parser.meta_json)
    except json.JSONDecodeError as exc:
        print(f'  [warn]  Malformed JSON in {filepath.name}: {exc}', file=sys.stderr)
        return None

    # Inject computed fields
    meta['filename'] = filepath.name
    meta['url']      = f'articles/{filepath.name}'
    return meta


def get_articles() -> list[dict]:
    """Scan articles/ and return metadata list sorted newest-first."""
    results = []
    for filepath in sorted(ARTICLES_DIR.glob('*.html')):
        if filepath.name == 'index.html':
            continue
        meta = parse_article_meta(filepath)
        if meta:
            results.append(meta)
            print(f'  [ok]    {filepath.name} — {meta.get("title", "(no title)")}')
        else:
            print(f'  [skip]  {filepath.name} — no article-meta block found')

    results.sort(key=lambda a: a.get('date', ''), reverse=True)
    return results


# ── JSON output ──────────────────────────────────────────────

def write_articles_json(articles: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / 'articles.json'
    out.write_text(
        json.dumps(articles, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    print(f'  [write] {out.relative_to(ROOT)}  ({len(articles)} article(s))')


# ── HTML helpers ─────────────────────────────────────────────

def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )


def _fmt_date(date_raw: str) -> str:
    try:
        d = datetime.strptime(date_raw, '%Y-%m-%d')
        return f'{d.strftime("%B")} {d.day}, {d.year}'
    except ValueError:
        return date_raw


def card_html(meta: dict, url_prefix: str = '') -> str:
    """Render an article card <article> element."""
    title    = _esc(meta.get('title', 'Untitled'))
    date_fmt = _fmt_date(meta.get('date', ''))
    author   = _esc(meta.get('author', 'BiosystemsHub'))
    category = _esc(meta.get('category', ''))
    desc     = _esc(meta.get('description', ''))
    url      = _esc(url_prefix + meta.get('url', '#'))
    thumb    = meta.get('thumbnail', '')

    badge = f'<span class="badge">{category}</span>' if category else ''

    if thumb:
        img_html = f'<img src="{_esc(thumb)}" alt="{title}" loading="lazy">'
    else:
        img_html = '<div class="card-thumb-placeholder">🧬</div>'

    return (
        f'<article class="card" data-category="{category}">\n'
        f'  <div class="card-thumb">{img_html}</div>\n'
        f'  <div class="card-body">\n'
        f'    <div class="card-meta">\n'
        f'      {badge}\n'
        f'      <span class="card-date">{date_fmt}</span>\n'
        f'    </div>\n'
        f'    <h3><a href="{url}">{title}</a></h3>\n'
        f'    <p class="card-author">By {author}</p>\n'
        f'    <p class="card-desc">{desc}</p>\n'
        f'    <div class="card-footer">\n'
        f'      <a href="{url}" class="card-link">Read article</a>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'</article>'
    )


# ── articles/index.html ──────────────────────────────────────

def _nav(active: str = 'articles') -> str:
    links = [
        ('index.html',          '../index.html',          'Home'),
        ('articles/index.html', '../articles/index.html', 'Articles'),
        ('videos.html',         '../videos.html',         'Videos'),
        ('resources.html',      '../resources.html',      'Resources'),
        ('about.html',          '../about.html',          'About'),
        ('contact.html',        '../contact.html',        'Contact'),
    ]
    items = ''
    for key, href, label in links:
        cls = ' class="active"' if key.startswith(active) else ''
        items += f'<li><a href="{href}"{cls}>{label}</a></li>\n      '
    return items.strip()


def _footer(prefix: str = '../') -> str:
    return f'''<footer class="site-footer" role="contentinfo">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-about">
        <h3>BiosystemsHub</h3>
        <p>A curated resource for biological systems science — featuring peer-reviewed articles, video lectures, and community contributions from researchers worldwide.</p>
      </div>
      <div class="footer-col">
        <h4>Navigate</h4>
        <ul>
          <li><a href="{prefix}index.html">Home</a></li>
          <li><a href="{prefix}articles/index.html">Articles</a></li>
          <li><a href="{prefix}videos.html">Videos</a></li>
          <li><a href="{prefix}resources.html">Resources</a></li>
          <li><a href="{prefix}about.html">About</a></li>
          <li><a href="{prefix}contact.html">Contact</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>Topics</h4>
        <ul>
          <li><a href="{prefix}articles/index.html">Systems Biology</a></li>
          <li><a href="{prefix}articles/index.html">Ecology</a></li>
          <li><a href="{prefix}articles/index.html">Genetics &amp; Genomics</a></li>
          <li><a href="{prefix}articles/index.html">Computational Biology</a></li>
          <li><a href="{prefix}articles/index.html">Neuroscience</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <span>&copy; 2026 BiosystemsHub. Content licensed under
        <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>.
      </span>
      <span>Hosted on GitHub Pages</span>
    </div>
  </div>
</footer>'''


def generate_articles_index(articles: list[dict]) -> str:
    categories = sorted({a['category'] for a in articles if a.get('category')})

    filter_buttons = '\n        '.join(
        f'<button class="filter-btn" data-filter="{_esc(c)}">{_esc(c)}</button>'
        for c in categories
    )

    if articles:
        cards_html = '\n        '.join(card_html(a, '../') for a in articles)
    else:
        cards_html = (
            '<div style="text-align:center;padding:3rem 1rem;color:var(--text-muted);'
            'font-family:var(--font-sans);grid-column:1/-1">\n'
            '  <p style="font-size:1.1rem">No articles published yet.</p>\n'
            '  <p style="font-size:.9rem;margin-top:.5rem">Add HTML files to the '
            '<code>articles/</code> folder and run <code>python scripts/build.py</code>.</p>\n'
            '</div>'
        )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="site-root" content="../">
  <title>Articles — BiosystemsHub</title>
  <meta name="description" content="Browse all biosystems science articles, reviews, and tutorials published on BiosystemsHub.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,400;0,700;1,400&family=Source+Sans+Pro:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/css/style.css">
</head>
<body data-page="articles">

<nav class="site-nav" role="navigation" aria-label="Main navigation">
  <div class="nav-inner">
    <a href="../index.html" class="nav-brand" aria-label="BiosystemsHub home">
      <div class="nav-brand-icon" aria-hidden="true">B</div>
      <span class="nav-brand-name">Biosystems<span>Hub</span></span>
    </a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="nav-links" aria-label="Toggle navigation">
      <span></span><span></span><span></span>
    </button>
    <ul class="nav-links" id="nav-links" role="list">
      <li><a href="../index.html">Home</a></li>
      <li><a href="../articles/index.html" class="active">Articles</a></li>
      <li><a href="../videos.html">Videos</a></li>
      <li><a href="../resources.html">Resources</a></li>
      <li><a href="../about.html">About</a></li>
      <li><a href="../contact.html">Contact</a></li>
    </ul>
  </div>
</nav>

<div class="page-wrap">
<main class="page-main">

  <header class="page-header">
    <div class="container">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="../index.html">Home</a>
        <span class="sep" aria-hidden="true">&rsaquo;</span>
        <span>Articles</span>
      </nav>
      <h1>Articles</h1>
      <p>Research articles, reviews, and tutorials on biological systems science.</p>
    </div>
  </header>

  <section class="section">
    <div class="container">

      <div class="filter-bar" role="group" aria-label="Filter articles by category">
        <span class="filter-label">Filter:</span>
        <button class="filter-btn active" data-filter="all">All</button>
        {filter_buttons}
      </div>

      <div class="cards-grid" id="articles-grid">
        {cards_html}
      </div>

      <p class="no-results" role="status">No articles match the selected category.</p>

    </div>
  </section>

</main>

{_footer('../')}
</div>

<script src="../assets/js/main.js"></script>
</body>
</html>
'''


# ── Homepage featured section ────────────────────────────────

def update_homepage_featured(articles: list[dict]) -> None:
    """Replace the FEATURED_START…FEATURED_END block in index.html."""
    index_path = ROOT / 'index.html'
    try:
        content = index_path.read_text(encoding='utf-8')
    except OSError as exc:
        print(f'  [error] Cannot read index.html: {exc}', file=sys.stderr)
        return

    if articles:
        featured_cards = '\n        '.join(card_html(a) for a in articles[:3])
    else:
        featured_cards = (
            '<div style="text-align:center;padding:2rem 1rem;color:var(--text-muted);'
            'font-family:var(--font-sans);grid-column:1/-1">\n'
            '          <p>No articles yet. Add an HTML file to the <code>articles/</code> '
            'folder and run <code>python scripts/build.py</code>.</p>\n'
            '        </div>'
        )

    replacement = (
        '<!-- FEATURED_START -->\n'
        '        ' + featured_cards + '\n'
        '        <!-- FEATURED_END -->'
    )

    updated, n = re.subn(
        r'<!-- FEATURED_START -->.*?<!-- FEATURED_END -->',
        replacement,
        content,
        flags=re.DOTALL,
    )

    if n == 0:
        print('  [warn]  FEATURED markers not found in index.html — skipping', file=sys.stderr)
        return

    index_path.write_text(updated, encoding='utf-8')
    count = min(len(articles), 3)
    print(f'  [write] index.html  (featured: {count} article(s))')


# ── Main ─────────────────────────────────────────────────────

def main() -> None:
    print('BiosystemsHub build script')
    print('=' * 42)

    print('\n→ Scanning articles/')
    articles = get_articles()
    print(f'  Found {len(articles)} article(s)')

    print('\n→ Writing data/articles.json')
    write_articles_json(articles)

    print('\n→ Generating articles/index.html')
    html = generate_articles_index(articles)
    out  = ARTICLES_DIR / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f'  [write] articles/index.html')

    print('\n→ Updating homepage featured section')
    update_homepage_featured(articles)

    print('\n✓  Build complete\n')


if __name__ == '__main__':
    main()
