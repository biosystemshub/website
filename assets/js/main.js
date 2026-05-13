'use strict';
// ============================================================
// BiosystemsHub — main.js
// Handles: nav highlighting, mobile nav, category filter,
//          video rendering from data/videos.json, click-to-play
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  markActiveNav();
  initMobileNav();
  initCategoryFilter();

  // Page-specific initialisation
  const page = document.body.dataset.page;
  if (page === 'home')   initHomepageVideos();
  if (page === 'videos') initVideosPage();
});

// ── Active nav link ──────────────────────────────────────────
function markActiveNav() {
  const page = document.body.dataset.page || '';
  document.querySelectorAll('.nav-links a').forEach(a => {
    const href = a.getAttribute('href');
    let match = false;
    if (page === 'home'      && href.endsWith('index.html') && !href.includes('articles')) match = true;
    if ((page === 'articles' || page === 'article') && href.includes('articles/index.html')) match = true;
    if (page === 'videos'    && href.endsWith('videos.html'))    match = true;
    if (page === 'resources' && href.endsWith('resources.html')) match = true;
    if (page === 'about'     && href.endsWith('about.html'))     match = true;
    if (page === 'contact'   && href.endsWith('contact.html'))   match = true;
    if (match) a.classList.add('active');
  });
}

// ── Mobile nav toggle ────────────────────────────────────────
function initMobileNav() {
  const toggle = document.querySelector('.nav-toggle');
  const links  = document.querySelector('.nav-links');
  if (!toggle || !links) return;

  toggle.addEventListener('click', () => {
    const open = toggle.classList.toggle('open');
    links.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
  });

  // Close when a link is clicked
  links.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      toggle.classList.remove('open');
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  });

  // Close when clicking outside
  document.addEventListener('click', e => {
    if (!toggle.contains(e.target) && !links.contains(e.target)) {
      toggle.classList.remove('open');
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });
}

// ── Category filter ──────────────────────────────────────────
function initCategoryFilter() {
  const bar = document.querySelector('.filter-bar');
  if (!bar) return;

  const buttons = bar.querySelectorAll('.filter-btn');
  const cards   = document.querySelectorAll('[data-category]');
  const noRes   = document.querySelector('.no-results');

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.dataset.filter;
      let visible = 0;

      cards.forEach(card => {
        const match = filter === 'all' || card.dataset.category === filter;
        card.dataset.hidden = match ? 'false' : 'true';
        if (match) visible++;
      });

      if (noRes) noRes.classList.toggle('visible', visible === 0);
    });
  });
}

// ── Homepage: render 3 latest videos ────────────────────────
function initHomepageVideos() {
  const container = document.getElementById('homepage-videos');
  if (!container) return;

  const base = getSiteRoot();
  fetch(base + 'data/videos.json')
    .then(r => { if (!r.ok) throw new Error('Not found'); return r.json(); })
    .then(videos => {
      if (!videos.length) {
        container.innerHTML = emptyMsg('Video content coming soon — check back later.');
        return;
      }
      container.innerHTML = videos.slice(0, 3).map(v => videoCardHTML(v)).join('');
      attachPlayHandlers(container);
    })
    .catch(() => {
      container.innerHTML = emptyMsg('Videos unavailable. Serve the site with a local server to preview.');
    });
}

// ── Videos page: render all videos with filter ───────────────
function initVideosPage() {
  const container = document.getElementById('videos-grid');
  if (!container) return;

  const base = getSiteRoot();
  fetch(base + 'data/videos.json')
    .then(r => { if (!r.ok) throw new Error('Not found'); return r.json(); })
    .then(videos => {
      if (!videos.length) {
        container.innerHTML = '<p class="no-results visible">No videos published yet.</p>';
        return;
      }
      container.innerHTML = videos.map(v => videoCardHTML(v, true)).join('');
      injectVideoCategoryButtons(videos);
      attachPlayHandlers(container);
      // Re-run filter init now that buttons and cards exist
      initCategoryFilter();
    })
    .catch(() => {
      container.innerHTML = '<p style="color:var(--text-muted);font-family:var(--font-sans);padding:2rem 0">' +
        'Could not load videos. Use <code>python -m http.server 8000</code> for local preview.' +
        '</p>';
    });
}

// Inject category filter buttons based on video data
function injectVideoCategoryButtons(videos) {
  const bar = document.querySelector('.filter-bar');
  if (!bar) return;

  const cats = [...new Set(videos.map(v => v.category).filter(Boolean))].sort();
  cats.forEach(cat => {
    if (bar.querySelector(`[data-filter="${CSS.escape(cat)}"]`)) return;
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.dataset.filter = cat;
    btn.textContent = cat;
    bar.appendChild(btn);
  });
}

// ── Video card HTML template ─────────────────────────────────
function videoCardHTML(v, showCategory = false) {
  const thumb = 'https://img.youtube.com/vi/' + esc(v.id) + '/mqdefault.jpg';
  const catBadge = showCategory && v.category
    ? '<span class="badge">' + esc(v.category) + '</span>'
    : '';
  return (
    '<div class="video-card" data-category="' + esc(v.category || '') + '">' +
    '<div class="video-embed-wrap lazy-video" data-videoid="' + esc(v.id) + '">' +
      '<div class="video-thumb-overlay">' +
        '<img src="' + thumb + '" alt="' + esc(v.title) + '" loading="lazy">' +
        '<div class="play-btn" role="button" aria-label="Play: ' + esc(v.title) + '"></div>' +
      '</div>' +
    '</div>' +
    '<div class="video-info">' +
      catBadge +
      '<h3>' + esc(v.title) + '</h3>' +
      '<p>' + esc(v.description || '') + '</p>' +
    '</div>' +
    '</div>'
  );
}

// ── Click-to-play: replace overlay with iframe ───────────────
function attachPlayHandlers(container) {
  container.querySelectorAll('.lazy-video').forEach(wrap => {
    wrap.addEventListener('click', () => {
      const id = wrap.dataset.videoid;
      // Use youtube-nocookie.com for enhanced privacy
      wrap.innerHTML =
        '<iframe src="https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) +
        '?autoplay=1&rel=0" allow="autoplay; encrypted-media; picture-in-picture" ' +
        'allowfullscreen loading="lazy" title="YouTube video player"></iframe>';
      wrap.classList.remove('lazy-video');
    });
  });
}

// ── Resolve site root (for fetch paths) ─────────────────────
function getSiteRoot() {
  const meta = document.querySelector('meta[name="site-root"]');
  return meta ? meta.content : '';
}

// ── Empty state message ──────────────────────────────────────
function emptyMsg(text) {
  return '<p style="color:var(--text-muted);font-family:var(--font-sans);padding:.5rem 0;grid-column:1/-1">' +
    esc(text) + '</p>';
}

// ── HTML escape (prevent XSS from JSON data) ────────────────
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}
