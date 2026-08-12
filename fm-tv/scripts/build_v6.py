from pathlib import Path

src = Path('fm-tv/blogger-embed-v5-fixed.html')
out = Path('fm-tv/blogger-embed-v6.html')
s = src.read_text(encoding='utf-8')

s = s.replace('<!-- FM TV BUILD V5 FIXED 2026-08-12-2225 -->', '<!-- FM TV BUILD V6 2026-08-12 -->')
s = s.replace('data-fmtv-build="v5-fixed-2026-08-12-2225"', 'data-fmtv-build="v6-2026-08-12"')

css = r'''
/* V6 product polish */
#fmtv-app .yt-feature-media img,#fmtv-app .yt-trend-thumb img,#fmtv-app .yt-thumb img{object-fit:cover!important;object-position:50% 50%!important}
#fmtv-app .yt-feature-media img,#fmtv-app .yt-trend-thumb img,#fmtv-app .yt-thumb img{position:absolute;inset:0;width:100%;height:100%}
#fmtv-app #fmtv-channel-head,#fmtv-app #fmtv-grid-section,#fmtv-app #fmtv-trending-shelf,#fmtv-app #fmtv-fav-shelf{scroll-margin-top:92px}
#fmtv-app .yt-channel-head{padding:20px 22px;background:#141416;border:1px solid #2b2c31;border-radius:16px;box-shadow:none}
#fmtv-app .yt-channel-top{gap:18px;align-items:center}
#fmtv-app .yt-channel-avatar{width:84px;height:84px;border:1px solid #383a40;background:#202126}
#fmtv-app .yt-channel-title{font-size:27px;letter-spacing:-.65px}
#fmtv-app .yt-channel-stats{font-size:11px;color:#aaaeb8}
#fmtv-app .yt-channel-actions{gap:10px;align-items:center}
#fmtv-app .yt-channel-fav{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 15px;background:#24252a;border:1px solid #3b3d44;border-radius:20px;color:#eee;font-size:11px;font-weight:900;transition:.16s ease}
#fmtv-app .yt-channel-fav:hover{background:#303137}
#fmtv-app .yt-channel-fav.on{background:rgba(255,216,74,.08);border-color:rgba(255,216,74,.42);color:var(--yellow)}
#fmtv-app .yt-subscribe{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 18px!important;border-radius:20px!important;background:#ff0033!important;color:#fff!important;font-size:11px!important;font-weight:950!important;box-shadow:0 7px 22px rgba(255,0,51,.2);transition:.16s ease}
#fmtv-app .yt-subscribe:hover{background:#e6002e!important;transform:translateY(-1px)}
#fmtv-app .yt-channel-desc{max-width:820px;margin-top:16px;padding-top:14px;border-top:1px solid #2a2b30;color:#c3c5cc;font-size:11.5px;line-height:1.6}
#fmtv-app .yt-view-page-head .yt-channel-top{align-items:center}
#fmtv-app .yt-view-icon{width:64px;height:64px;border-radius:16px;display:grid;place-items:center;font-size:29px;font-weight:950;background:linear-gradient(135deg,rgba(103,232,255,.18),rgba(168,134,255,.22));border:1px solid #353a45}
#fmtv-app .yt-view-page-head.trending .yt-view-icon{background:linear-gradient(135deg,rgba(255,59,87,.2),rgba(255,142,62,.15))}
#fmtv-app .yt-view-page-head.favourites .yt-view-icon{color:var(--yellow);background:rgba(255,216,74,.08);border-color:rgba(255,216,74,.28)}
#fmtv-app .yt-view-page-head.category .yt-view-icon{background:linear-gradient(135deg,rgba(103,232,255,.15),rgba(168,134,255,.18))}
#fmtv-app .yt-view-page-head .yt-channel-desc{margin-bottom:0}
#fmtv-app .yt-feed-ad{display:none;margin:30px 0;padding:4px 0;grid-column:1/-1}
#fmtv-app .yt-grid-segment+.yt-grid-segment{margin-top:24px}
#fmtv-app .yt-ad-slot{position:relative}
@media(max-width:720px){#fmtv-app .yt-channel-top{align-items:flex-start;flex-wrap:wrap}#fmtv-app .yt-channel-avatar{width:68px;height:68px}#fmtv-app .yt-channel-actions{width:100%;margin-left:0}#fmtv-app .yt-channel-fav,#fmtv-app .yt-subscribe{flex:1}#fmtv-app .yt-view-icon{width:54px;height:54px;font-size:24px}}
'''
s = s.replace('</style>', css + '\n</style>', 1)

old_main = '<section class="yt-shelf"><div class="yt-shelf-head"><div><h3 id="fmtv-grid-title">Latest from the FM community</h3><div class="yt-subtext" id="fmtv-grid-note"></div></div><div class="yt-subtext" id="fmtv-count"></div></div><div class="yt-grid" id="fmtv-grid"></div><div class="yt-load-wrap"><button class="yt-load" id="fmtv-load" type="button">Show more</button></div></section><div class="yt-ad-slot"><div class="content_hint"></div></div>'
new_main = '<section class="yt-shelf" id="fmtv-grid-section"><div class="yt-shelf-head"><div><h3 id="fmtv-grid-title">Latest from the FM community</h3><div class="yt-subtext" id="fmtv-grid-note"></div></div><div class="yt-subtext" id="fmtv-count"></div></div><div class="yt-grid yt-grid-segment" id="fmtv-grid-a"></div><div class="yt-ad-slot yt-feed-ad" id="fmtv-feed-ad"><div class="content_hint"></div></div><div class="yt-grid yt-grid-segment" id="fmtv-grid-b"></div><div class="yt-load-wrap"><button class="yt-load" id="fmtv-load" type="button">Show more</button></div></section><div class="yt-ad-slot"><div class="content_hint"></div></div>'
if old_main not in s:
    raise SystemExit('Main grid HTML marker not found')
s = s.replace(old_main, new_main, 1)

old_el = "grid:$('#fmtv-grid'),load:$('#fmtv-load')"
new_el = "gridA:$('#fmtv-grid-a'),gridB:$('#fmtv-grid-b'),feedAd:$('#fmtv-feed-ad'),gridSection:$('#fmtv-grid-section'),load:$('#fmtv-load')"
if old_el not in s:
    raise SystemExit('Element map marker not found')
s = s.replace(old_el, new_el, 1)

old_find = "function findVideo(id){var ar=(state.archive&&state.archive.videos)||[],re=(state.data&&state.data.videos)||[];return ar.find(function(v){return v.id===id})||re.find(function(v){return v.id===id})}"
new_find = old_find + "function scrollToNode(node){if(!node)return;setTimeout(function(){try{node.scrollIntoView({behavior:'smooth',block:'start'})}catch(err){node.scrollIntoView(true)}},35)}function goHome(){state.creator='';state.mode='latest';state.category='';state.query='';state.shown=12;el.search.value='';renderAll();setHash();scrollToNode(el.homeOnly)}function goMode(mode){state.creator='';state.category='';state.mode=mode||'latest';state.shown=state.mode==='latest'?12:24;renderAll();setHash();scrollToNode(state.mode==='latest'?el.gridSection:el.channelHead)}"
if old_find not in s:
    raise SystemExit('findVideo marker not found')
s = s.replace(old_find, new_find, 1)

start = s.index('function bindInteractive(scope){')
end = s.index('function creatorRow(c){', start)
new_bind = r'''function bindInteractive(scope){var box=scope||root;box.querySelectorAll('[data-play]').forEach(function(node){node.onclick=function(ev){ev.preventDefault();var v=findVideo(node.getAttribute('data-play'));if(v)openVideo(v)}});box.querySelectorAll('[data-home]').forEach(function(node){node.onclick=function(ev){ev.preventDefault();goHome()}});box.querySelectorAll('[data-creator]').forEach(function(node){node.onclick=function(ev){ev.preventDefault();state.creator=node.getAttribute('data-creator')||'';state.mode='latest';state.category='';state.query='';state.shown=12;el.search.value='';renderAll();setHash();if(state.creator){if(!state.archive)ensureArchive();scrollToNode(el.channelHead)}else scrollToNode(el.homeOnly)}});box.querySelectorAll('[data-star]').forEach(function(node){node.onclick=function(ev){ev.preventDefault();ev.stopPropagation();toggleFav(node.getAttribute('data-star'))}});box.querySelectorAll('[data-mode]').forEach(function(node){node.onclick=function(ev){ev.preventDefault();goMode(node.getAttribute('data-mode')||'latest')}});box.querySelectorAll('[data-cat]').forEach(function(node){node.onclick=function(ev){ev.preventDefault();state.creator='';state.mode='latest';state.category=node.getAttribute('data-cat')||'';state.shown=state.category?24:12;renderAll();setHash();scrollToNode(state.category?el.channelHead:el.gridSection)}})}
'''
s = s[:start] + new_bind + s[end:]

start = s.index('function renderChannelHead(){')
end = s.index('function renderGrid(){', start)
new_context = r'''function renderChannelHead(){if(state.creator){var c=channelById(state.creator);el.homeOnly.style.display='none';if(!c){el.channelHead.innerHTML='';return}el.channelHead.innerHTML='<section class="yt-channel-head"><button class="yt-back" type="button" data-home>← FM TV Home</button><div class="yt-channel-top"><img class="yt-channel-avatar" src="'+esc(c.avatar)+'" alt="'+esc(c.name)+'"><div class="yt-channel-main"><div class="yt-channel-title">'+esc(c.name)+'</div><div class="yt-channel-stats">'+esc(subText(c))+'</div></div><div class="yt-channel-actions"><button class="yt-channel-fav '+(state.favs.has(c.id)?'on':'')+'" type="button" data-star="'+esc(c.id)+'">★ Favourite</button><a class="yt-subscribe" href="'+esc(c.channelUrl)+(c.channelUrl.indexOf('?')>-1?'&':'?')+'sub_confirmation=1" target="_blank" rel="noopener noreferrer">Subscribe</a></div></div><p class="yt-channel-desc">'+esc(c.description||'No channel description available.')+'</p></section>';return}if(state.mode==='trending'){el.homeOnly.style.display='none';el.channelHead.innerHTML='<section class="yt-channel-head yt-view-page-head trending"><button class="yt-back" type="button" data-home>← FM TV Home</button><div class="yt-channel-top"><div class="yt-view-icon">↗</div><div class="yt-channel-main"><div class="yt-channel-title">Trending 24h</div><div class="yt-channel-stats">The Football Manager videos getting the most attention right now</div></div></div><p class="yt-channel-desc">'+(state.data&&state.data.views24hReady?'Ranked by actual YouTube views gained during the last 24 hours.':'Hourly tracking is still building its first full 24-hour baseline, so momentum ranking is temporarily being used.')+'</p></section>';return}if(state.mode==='favourites'){el.homeOnly.style.display='none';el.channelHead.innerHTML='<section class="yt-channel-head yt-view-page-head favourites"><button class="yt-back" type="button" data-home>← FM TV Home</button><div class="yt-channel-top"><div class="yt-view-icon">★</div><div class="yt-channel-main"><div class="yt-channel-title">Your Channels</div><div class="yt-channel-stats">'+state.favs.size+' starred creator'+(state.favs.size===1?'':'s')+'</div></div></div><p class="yt-channel-desc">Your personalised FM TV feed, containing videos only from the creators you have starred.</p></section>';return}if(state.category){el.homeOnly.style.display='none';el.channelHead.innerHTML='<section class="yt-channel-head yt-view-page-head category"><button class="yt-back" type="button" data-home>← FM TV Home</button><div class="yt-channel-top"><div class="yt-view-icon">▶</div><div class="yt-channel-main"><div class="yt-channel-title">'+esc(state.category)+'</div><div class="yt-channel-stats">Football Manager '+esc(state.category.toLowerCase())+' videos</div></div></div></section>';return}el.channelHead.innerHTML='';el.homeOnly.style.display='block'}
'''
s = s[:start] + new_context + s[end:]

start = s.index('function renderGrid(){')
end = s.index('async function ensureArchive()', start)
new_grid = r'''function renderGrid(){var arr=filtered(),visible=arr.slice(0,state.shown),split=Math.min(8,visible.length),first=visible.slice(0,split),second=visible.slice(split);el.gridA.innerHTML=first.length?first.map(card).join(''):(visible.length?'':'<div class="yt-empty">No videos match these filters.</div>');el.gridB.innerHTML=second.map(card).join('');el.feedAd.style.display=second.length?'block':'none';if(state.creator){var c=channelById(state.creator);el.gridTitle.textContent=(c?c.name:'Creator')+' videos';el.gridNote.textContent=state.archive?'Latest uploads from the past year':'Latest uploads'}else if(state.mode==='trending'){el.gridTitle.textContent='Trending 24h';el.gridNote.textContent=state.data&&state.data.views24hReady?'Ranked by actual 24h view growth':'Momentum ranking until 24h data matures'}else if(state.mode==='favourites'){el.gridTitle.textContent='Your channel feed';el.gridNote.textContent='Videos from starred creators'}else if(state.category){el.gridTitle.textContent=state.category+' videos';el.gridNote.textContent='Latest '+state.category.toLowerCase()+' from the FM community'}else{el.gridTitle.textContent='Latest from the FM community';el.gridNote.textContent=''}el.count.textContent=arr.length+' video'+(arr.length===1?'':'s');el.load.style.display=(arr.length>state.shown||(state.creator&&!state.archive))?'inline-block':'none'}
'''
s = s[:start] + new_grid + s[end:]

s = s.replace("renderGrid();bindInteractive(el.grid)", "renderGrid();bindInteractive(root)")
s = s.replace("el.grid.innerHTML='<div class=\"yt-empty\">FM TV is temporarily unavailable.</div>'", "el.gridA.innerHTML='<div class=\"yt-empty\">FM TV is temporarily unavailable.</div>';el.gridB.innerHTML='';el.feedAd.style.display='none'")

old_search_btn = "el.searchBtn.addEventListener('click',function(){state.query=el.search.value;state.shown=12;renderGrid();bindInteractive(root)})"
if old_search_btn in s:
    s = s.replace(old_search_btn, "el.searchBtn.addEventListener('click',function(){state.query=el.search.value;state.shown=24;renderGrid();bindInteractive(root);scrollToNode(el.gridSection)})")

out.write_text(s, encoding='utf-8')
print(f'Built {out} ({len(s)} bytes)')
