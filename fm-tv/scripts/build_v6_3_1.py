from pathlib import Path

src = Path('fm-tv/blogger-embed-v6-3.html')
out = Path('fm-tv/blogger-embed-v6-3-1.html')
s = src.read_text(encoding='utf-8')

s = s.replace(
    '<!-- FM TV BUILD V6.3 FILTERS 2026-08-12 -->',
    '<!-- FM TV BUILD V6.3.1 FILTER CHECK FIX 2026-08-12 -->',
    1,
)
s = s.replace(
    'data-fmtv-build="v6-3-filters-2026-08-12"',
    'data-fmtv-build="v6-3-1-filter-check-fix-2026-08-12"',
    1,
)

old = "#fmtv-app .yt-filter-option.active:before{content:'✓';display:inline-block;width:18px;color:#67e8ff;font-weight:950}\n#fmtv-app .yt-filter-option:not(.active):before{content:'';display:inline-block;width:18px}"
new = "#fmtv-app .yt-filter-option.active:before{content:\"\";display:inline-block;width:7px;height:12px;margin:0 10px 2px 4px;border-right:2px solid #67e8ff;border-bottom:2px solid #67e8ff;transform:rotate(45deg);vertical-align:middle}\n#fmtv-app .yt-filter-option:not(.active):before{content:\"\";display:inline-block;width:21px}"

if old not in s:
    raise SystemExit('filter checkmark CSS marker not found')

s = s.replace(old, new, 1)

if "content:'✓'" in s or 'content:"✓"' in s:
    raise SystemExit('unsafe glyph checkmark still present')
if 'border-right:2px solid #67e8ff' not in s:
    raise SystemExit('CSS-drawn checkmark missing')

out.write_text(s, encoding='utf-8')
print(f'Wrote {out}')
