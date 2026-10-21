#!/usr/bin/env python3
"""Build the Blogger page from the preserved live v7 shell and readable v8 JS/CSS."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'live-v7-backup.html').read_text(encoding='utf-8')
script = (ROOT / 'app-v8.js').read_text(encoding='utf-8')
style = (ROOT / 'styles-v8.css').read_text(encoding='utf-8')
source = source[:source.rindex('<script>')]
source = source.replace('data-fmtv-build="v7-shared-shell-2026-10-04"', 'data-fmtv-build="v8-discovery-2026-10-21"')
source = source.replace('<section class="fmtv-intro"', '<style id="fmtv-v8">\n' + style + '\n</style>\n<section class="fmtv-intro"', 1)
source = source.replace('<div class="yt-home-head"><h3>Featured today', '<div class="yt-home-head" id="fmtv-pick-heading"><h3>&#128293; Most watched in the last 24h', 1)
toolbar = '''
  <div class="yt-discovery-toolbar">
    <label class="yt-version-control" for="fmtv-version">Game <select id="fmtv-version"><option value="">All Football Manager</option><option value="FM27">FM27</option><option value="FM26">FM26</option><option value="older">Older FM</option><option value="other">Other football games</option></select></label>
    <div class="yt-library-controls">
      <button class="yt-pill" type="button" data-mode="later" title="Open your saved FM TV videos">Watch later <span id="fmtv-later-count">0</span></button>
      <div class="yt-sync-line"><span id="fmtv-sync-status" role="status">Saved in this browser only</span><button id="fmtv-sync-retry" type="button" hidden>Retry sync</button></div>
    </div>
  </div>
  <div class="yt-feed-status" id="fmtv-status" role="status" hidden></div>
'''
source = source.replace('  <div class="yt-body">', toolbar + '  <div class="yt-body">', 1)
source = source.replace('<div class="yt-player" id="fmtv-player"></div>', '<div class="yt-player" id="fmtv-player"></div><div class="yt-player-actions" id="fmtv-player-actions"></div><div class="yt-related" id="fmtv-related" hidden></div>', 1)
source += '''
<div class="yt-creators-modal" id="fmtv-creators-modal" role="dialog" aria-modal="true" aria-labelledby="fmtv-creators-title" aria-hidden="true">
  <div class="yt-creators-box">
    <div class="yt-creators-head"><h2 id="fmtv-creators-title">All creators</h2><button class="yt-close" id="fmtv-creators-close" type="button" aria-label="Close creators">&#215;</button></div>
    <div class="yt-creators-search-wrap"><input id="fmtv-creators-search" type="search" aria-label="Find a creator" placeholder="Search all creators..." autocomplete="off"></div>
    <div class="yt-creators-list" id="fmtv-creators-list"></div>
  </div>
</div>
'''
source += '<script>\n' + script.replace('</script', '<\\/script') + '\n</script>\n</div>\n'
required = re.findall(r'id="(fmtv-[^"]+)"', source)
duplicates = {name for name in required if required.count(name) > 1}
if duplicates:
    raise ValueError(f'Duplicate IDs: {duplicates}')
(ROOT / 'blogger-embed-v8.html').write_text(source, encoding='utf-8')
standalone = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FM TV v8 preview</title><style>html{color-scheme:dark}body{background:#0e131b;color:#edf3fb;font:15px/1.5 Arial,sans-serif;margin:0;padding:20px}main.preview{max-width:1440px;margin:auto}*{box-sizing:border-box}button,input,select{font:inherit}a{color:#8be1eb}@media(max-width:500px){body{padding:14px}}</style></head><body><main class="preview">' + source + '</main></body></html>'
(ROOT / 'preview-v8.html').write_text(standalone, encoding='utf-8')
responsive = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FM TV responsive QA</title><style>body{margin:0;background:#26313f}iframe{display:block;margin:0 auto;border:0;min-height:100vh;background:#0e131b}</style><iframe title="FM TV preview" id="preview"></iframe><script>var frame=document.getElementById("preview");var width=Math.max(320,Math.min(1440,Number(new URLSearchParams(location.search).get("qaWidth"))||1280));frame.style.width=width+"px";frame.style.height="100vh";frame.srcdoc=' + json.dumps(standalone).replace('</script', '<\\/script') + ';</script></html>'
(ROOT / 'responsive-preview-v8.html').write_text(responsive, encoding='utf-8')
print(f'Built Blogger embed: {len(source):,} characters; standalone and responsive QA previews.')
