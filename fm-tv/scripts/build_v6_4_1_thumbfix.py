from pathlib import Path

src = Path('fm-tv/blogger-embed-v6-4.html')
out = Path('fm-tv/blogger-embed-v6-4-1.html')
s = src.read_text(encoding='utf-8')

s = s.replace('<!-- FM TV BUILD V6.4 SEARCH VIEW 2026-08-12 -->', '<!-- FM TV BUILD V6.4.1 THUMBNAIL FIX 2026-08-12 -->', 1)
s = s.replace('data-fmtv-build="v6-4-search-view-2026-08-12"', 'data-fmtv-build="v6-4-1-thumbnail-fix-2026-08-12"', 1)

fix = r'''
<style id="fmtv-v6-4-1-thumbfix">
/* Hard reset against Blogger/theme image styles. */
#fmtv-app .yt-thumb,
#fmtv-app .yt-feature-media,
#fmtv-app .yt-trend-thumb,
#fmtv-app.search-view .yt-video.yt-search-result .yt-thumb{
  position:relative!important;
  overflow:hidden!important;
  padding:0!important;
  margin:0!important;
  line-height:0!important;
  font-size:0!important;
  background:#1d1e22!important;
  box-sizing:border-box!important;
}

#fmtv-app .yt-thumb > img,
#fmtv-app .yt-feature-media > img,
#fmtv-app .yt-trend-thumb > img,
#fmtv-app.search-view .yt-video.yt-search-result .yt-thumb > img{
  position:absolute!important;
  top:0!important;
  right:0!important;
  bottom:0!important;
  left:0!important;
  inset:0!important;
  width:100%!important;
  height:100%!important;
  min-width:100%!important;
  min-height:100%!important;
  max-width:none!important;
  max-height:none!important;
  margin:0!important;
  padding:0!important;
  border:0!important;
  outline:0!important;
  border-radius:0!important;
  box-shadow:none!important;
  display:block!important;
  vertical-align:top!important;
  object-fit:cover!important;
  object-position:50% 50%!important;
  transform:translateZ(0);
}

/* Keep the thumbnail geometry exact and eliminate sub-pixel seams. */
#fmtv-app .yt-thumb{
  width:100%!important;
  aspect-ratio:16 / 9!important;
}
#fmtv-app .yt-trend-thumb,
#fmtv-app .yt-feature-media{
  aspect-ratio:16 / 9!important;
}

/* Preserve the existing hover zoom after the hard image reset. */
#fmtv-app .yt-video:hover .yt-thumb > img{
  transform:scale(1.015) translateZ(0)!important;
}
</style>
'''

marker = '<div class="yt-shell">'
if marker not in s:
    raise SystemExit('yt-shell marker not found')
s = s.replace(marker, fix + '\n' + marker, 1)

required = [
    'FM TV BUILD V6.4.1 THUMBNAIL FIX',
    'fmtv-v6-4-1-thumbfix',
    'padding:0!important;',
    'vertical-align:top!important;',
    'object-fit:cover!important;',
]
for item in required:
    if item not in s:
        raise SystemExit(f'missing required marker: {item}')

out.write_text(s, encoding='utf-8')
print('Built', out)
