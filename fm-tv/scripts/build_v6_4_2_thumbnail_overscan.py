from pathlib import Path

src = Path('fm-tv/blogger-embed-v6-4-1.html')
out = Path('fm-tv/blogger-embed-v6-4-2.html')
s = src.read_text(encoding='utf-8')

s = s.replace('<!-- FM TV BUILD V6.4.1 THUMBNAIL FIX 2026-08-12 -->', '<!-- FM TV BUILD V6.4.2 THUMBNAIL OVERSCAN FIX 2026-08-13 -->', 1)
s = s.replace('data-fmtv-build="v6-4-1-thumbnail-fix-2026-08-12"', 'data-fmtv-build="v6-4-2-thumbnail-overscan-fix-2026-08-13"', 1)

css = r'''
/* V6.4.2 final thumbnail overscan fix */
#fmtv-app .yt-thumb,
#fmtv-app .yt-trend-thumb,
#fmtv-app .yt-feature-media{
  position:relative!important;
  overflow:hidden!important;
  line-height:0!important;
  font-size:0!important;
  padding:0!important;
  margin:0!important;
}
#fmtv-app .yt-thumb img,
#fmtv-app .yt-trend-thumb img,
#fmtv-app .yt-feature-media img{
  position:absolute!important;
  left:50%!important;
  top:50%!important;
  inset:auto!important;
  width:104%!important;
  height:104%!important;
  min-width:104%!important;
  min-height:104%!important;
  max-width:none!important;
  max-height:none!important;
  margin:0!important;
  padding:0!important;
  border:0!important;
  display:block!important;
  object-fit:cover!important;
  object-position:50% 50%!important;
  transform:translate(-50%,-50%) scale(1.01)!important;
  transform-origin:50% 50%!important;
  vertical-align:top!important;
}
#fmtv-app .yt-video:hover .yt-thumb img{
  transform:translate(-50%,-50%) scale(1.035)!important;
}
'''

if '</style>' not in s:
    raise SystemExit('style end not found')
s = s.replace('</style>', css + '\n</style>', 1)

if 'width:104%!important' not in s or 'translate(-50%,-50%)' not in s:
    raise SystemExit('overscan CSS missing')

out.write_text(s, encoding='utf-8')
print('Built', out)
