from pathlib import Path

src = Path('fm-tv/blogger-embed-v6-3-1.html')
out = Path('fm-tv/blogger-embed-v6-4.html')
s = src.read_text(encoding='utf-8')

s = s.replace('<!-- FM TV BUILD V6.3.1 FILTER CHECK FIX 2026-08-12 -->', '<!-- FM TV BUILD V6.4 SEARCH VIEW 2026-08-12 -->', 1)
s = s.replace('data-fmtv-build="v6-3-1-filter-check-fix-2026-08-12"', 'data-fmtv-build="v6-4-search-view-2026-08-12"', 1)

css = r'''
/* V6.4 dedicated YouTube-style search results + stricter thumbnail alignment */
#fmtv-app .yt-video{display:flex;flex-direction:column;height:100%;min-width:0}
#fmtv-app .yt-thumb{width:100%;aspect-ratio:16/9;flex:0 0 auto;position:relative;overflow:hidden}
#fmtv-app .yt-thumb img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 50%;display:block}
#fmtv-app .yt-info{min-height:94px}
#fmtv-app .yt-trend-thumb img,#fmtv-app .yt-feature-media img{object-position:50% 50%}
#fmtv-app.search-view .yt-chipbar{margin-bottom:8px}
#fmtv-app.search-view .yt-grid{grid-template-columns:1fr;gap:18px}
#fmtv-app.search-view .yt-video.yt-search-result{display:grid;grid-template-columns:minmax(300px,420px) minmax(0,1fr);gap:16px;align-items:start;height:auto}
#fmtv-app.search-view .yt-video.yt-search-result .yt-thumb{width:100%;border-radius:12px}
#fmtv-app .yt-search-copy{min-width:0;padding:3px 0 0}
#fmtv-app .yt-search-title{display:block;width:100%;border:0;background:none;padding:0;text-align:left;color:#f1f1f1;font-size:17px;line-height:1.35;font-weight:900;cursor:pointer}
#fmtv-app .yt-search-meta{font-size:10.5px;color:#95979f;margin-top:6px}
#fmtv-app .yt-search-channel{display:flex;align-items:center;gap:8px;margin-top:12px}
#fmtv-app .yt-search-channel img{width:30px;height:30px;border-radius:50%;object-fit:cover;background:#222}
#fmtv-app .yt-search-channel button{border:0;background:none;padding:0;color:#b2b4bb;font-size:10.5px;font-weight:800;cursor:pointer;text-align:left}
#fmtv-app .yt-search-desc{margin:10px 0 0;color:#8f9198;font-size:10.5px;line-height:1.5;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;max-width:820px}
#fmtv-app.search-view .yt-grid-section{scroll-margin-top:74px}
@media(max-width:840px){#fmtv-app.search-view .yt-video.yt-search-result{grid-template-columns:minmax(220px,330px) minmax(0,1fr)}}
@media(max-width:680px){#fmtv-app.search-view .yt-video.yt-search-result{display:block}#fmtv-app .yt-search-copy{padding:10px 1px 0}#fmtv-app .yt-search-title{font-size:14px}#fmtv-app .yt-search-desc{display:none}}
'''
if '</style>' not in s:
    raise SystemExit('style end not found')
s = s.replace('</style>', css + '\n</style>', 1)

# Search becomes a dedicated page state: hide homepage shelves while a query is active.
old_head = "function renderChannelHead(){if(state.creator){"
new_head = "function renderChannelHead(){if(state.query.trim()){el.homeOnly.style.display='none';el.channelHead.innerHTML='';return}if(state.creator){"
if old_head not in s:
    raise SystemExit('renderChannelHead marker not found')
s = s.replace(old_head, new_head, 1)

# Add a dedicated search-result card before archive helpers.
marker = "function wantsArchive(){"
if marker not in s:
    raise SystemExit('wantsArchive marker not found')
search_card = r'''function searchCard(v){var desc=(v.description||'').replace(/\s+/g,' ').trim();return'<article class="yt-video yt-search-result"><div class="yt-thumb" data-play="'+esc(v.id)+'"><img src="'+esc(v.thumbnail)+'" alt="'+esc(v.title)+'" loading="lazy" decoding="async">'+(fresh(v.publishedAt)?'<span class="yt-new">New</span>':'')+(state.watched.has(v.id)?'<span class="yt-watched-badge">Watched</span>':'')+'<span class="yt-duration">'+esc(v.duration)+'</span></div><div class="yt-search-copy"><button class="yt-search-title" type="button" data-play="'+esc(v.id)+'">'+esc(v.title)+'</button><div class="yt-search-meta">'+fmt(v.views)+' views · '+rel(v.publishedAt)+'</div><div class="yt-search-channel"><img src="'+esc(v.channelAvatar)+'" alt="" loading="lazy"><button type="button" data-creator="'+esc(v.channelId)+'">'+esc(v.channelName)+'</button></div>'+(desc?'<p class="yt-search-desc">'+esc(desc)+'</p>':'')+'</div></article>'}
'''
s = s.replace(marker, search_card + marker, 1)

old_grid_start = "function renderGrid(){var arr=filtered(),visible=arr.slice(0,state.shown),split=Math.min(8,visible.length),first=visible.slice(0,split),second=visible.slice(split);el.gridA.innerHTML=first.length?first.map(card).join(''):(visible.length?'':'<div class=\"yt-empty\">No videos match these filters.</div>');el.gridB.innerHTML=second.map(card).join('');el.feedAd.style.display=second.length?'block':'none';"
new_grid_start = "function renderGrid(){var isSearch=!!state.query.trim(),renderCard=isSearch?searchCard:card,arr=filtered(),visible=arr.slice(0,state.shown),split=Math.min(8,visible.length),first=visible.slice(0,split),second=visible.slice(split);root.classList.toggle('search-view',isSearch);el.gridA.innerHTML=first.length?first.map(renderCard).join(''):(visible.length?'':'<div class=\"yt-empty\">No videos match these filters.</div>');el.gridB.innerHTML=second.map(renderCard).join('');el.feedAd.style.display=second.length?'block':'none';"
if old_grid_start not in s:
    raise SystemExit('renderGrid start marker not found')
s = s.replace(old_grid_start, new_grid_start, 1)

# Avoid Blogger converting curly quote characters into literal HTML entities inside JS.
search_titles = [
    "el.gridTitle.textContent='Search results for “'+state.query.trim()+'”';",
    "el.gridTitle.textContent='Search results for &#8220;'+state.query.trim()+'&#8221;';",
    "el.gridTitle.textContent='Search results for &amp;#8220;'+state.query.trim()+'&amp;#8221;';",
]
replaced = False
for old in search_titles:
    if old in s:
        s = s.replace(old, "el.gridTitle.textContent='Search results for '+state.query.trim();", 1)
        replaced = True
        break
if not replaced:
    raise SystemExit('search title marker not found')

# Make search input actually switch the page state instead of leaving Trending/Featured visible.
old_input = "el.search.addEventListener('input',function(){state.query=el.search.value;state.shown=24;renderGrid();bindInteractive(root);if(state.searchTimer)clearTimeout(state.searchTimer);if(state.query.trim().length>=2&&!state.archive){state.searchTimer=setTimeout(function(){ensureArchive()},350)}});"
new_input = "el.search.addEventListener('input',function(){state.query=el.search.value;state.creator='';state.mode='latest';state.shown=24;renderChannelHead();renderGrid();bindInteractive(root);if(!state.query.trim()){renderAll();return}if(state.searchTimer)clearTimeout(state.searchTimer);if(state.query.trim().length>=2&&!state.archive){state.searchTimer=setTimeout(function(){ensureArchive()},350)}});"
if old_input not in s:
    raise SystemExit('search input handler marker not found')
s = s.replace(old_input, new_input, 1)

old_btn = "el.searchBtn.addEventListener('click',function(){state.query=el.search.value;state.shown=24;renderGrid();bindInteractive(root);scrollToNode(el.gridSection);if(state.query.trim().length>=2&&!state.archive)ensureArchive()});"
new_btn = "el.searchBtn.addEventListener('click',function(){state.query=el.search.value.trim();state.creator='';state.mode='latest';state.shown=24;renderAll();setHash();scrollToNode(el.gridSection);if(state.query.length>=2&&!state.archive)ensureArchive()});el.search.addEventListener('keydown',function(ev){if(ev.key==='Enter'){ev.preventDefault();el.searchBtn.click()}});"
if old_btn not in s:
    raise SystemExit('search button handler marker not found')
s = s.replace(old_btn, new_btn, 1)

# Keep homepage feature/shelves from being needlessly rendered while search is active.
s = s.replace("function renderFeature(){if(state.creator){", "function renderFeature(){if(state.creator||state.query.trim()){el.feature.innerHTML='';return}if(state.creator){", 1)
s = s.replace("function renderTrending(){if(state.creator)return;", "function renderTrending(){if(state.creator||state.query.trim())return;", 1)
s = s.replace("function renderFavShelf(){if(state.creator||!state.favs.size){", "function renderFavShelf(){if(state.creator||state.query.trim()||!state.favs.size){", 1)

# Build marker and guardrails.
if '&#8220;' in s or '&#8221;' in s:
    raise SystemExit('curly quote entities still present')
if 'Search results for “' in s:
    raise SystemExit('curly quote search title still present')
if 'yt-search-result' not in s or "root.classList.toggle('search-view'" not in s:
    raise SystemExit('search view output missing')

out.write_text(s, encoding='utf-8')
print('Built', out)
