from pathlib import Path

src=Path('fm-tv/blogger-embed-v6-2.html')
out=Path('fm-tv/blogger-embed-v6-3.html')
s=src.read_text(encoding='utf-8')
s=s.replace('<!-- FM TV BUILD V6.2 2026-08-12 -->','<!-- FM TV BUILD V6.3 FILTERS 2026-08-12 -->',1)
s=s.replace('data-fmtv-build="v6-2-2026-08-12"','data-fmtv-build="v6-3-filters-2026-08-12"',1)

css=r'''
/* V6.3 YouTube-style filters */
#fmtv-app .yt-filter-trigger{display:inline-flex;align-items:center;gap:6px}
#fmtv-app .yt-filter-trigger .filter-count{display:none;min-width:18px;height:18px;padding:0 5px;border-radius:9px;background:#67e8ff;color:#081014;align-items:center;justify-content:center;font-size:9px;font-weight:950}
#fmtv-app .yt-filter-trigger.has-filters{border-color:#4b9bb3;background:#1d2930}
#fmtv-app .yt-filter-trigger.has-filters .filter-count{display:inline-flex}
#fmtv-app .yt-filter-modal{position:fixed;z-index:1000001;inset:0;display:none;align-items:center;justify-content:center;padding:20px;background:rgba(0,0,0,.72);backdrop-filter:blur(5px)}
#fmtv-app .yt-filter-modal.open{display:flex}
#fmtv-app .yt-filter-box{width:min(920px,96vw);max-height:min(720px,90vh);overflow:auto;background:#232325;border:1px solid #3a3b40;border-radius:16px;box-shadow:0 28px 90px rgba(0,0,0,.55)}
#fmtv-app .yt-filter-head{position:sticky;top:0;z-index:2;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 20px;background:#232325;border-bottom:1px solid #36373b}
#fmtv-app .yt-filter-head h3{margin:0;font-size:20px;letter-spacing:-.3px}
#fmtv-app .yt-filter-x{width:36px;height:36px;border:0;background:transparent;color:#fff;font-size:25px;cursor:pointer;border-radius:50%}
#fmtv-app .yt-filter-x:hover{background:#343438}
#fmtv-app .yt-filter-groups{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;padding:10px 18px 6px}
#fmtv-app .yt-filter-group{min-width:0;padding:12px 18px 18px;border-right:1px solid #38383c}
#fmtv-app .yt-filter-group:last-child{border-right:0}
#fmtv-app .yt-filter-label{padding-bottom:10px;margin-bottom:8px;border-bottom:1px solid #434348;color:#f2f2f2;font-size:11px;font-weight:950;text-transform:uppercase;letter-spacing:.45px}
#fmtv-app .yt-filter-option{display:block;width:100%;border:0;background:transparent;color:#b8b8bd;padding:8px 0;text-align:left;font-size:12px;cursor:pointer}
#fmtv-app .yt-filter-option:hover{color:#fff}
#fmtv-app .yt-filter-option.active{color:#fff;font-weight:950}
#fmtv-app .yt-filter-option.active:before{content:'✓';display:inline-block;width:18px;color:#67e8ff;font-weight:950}
#fmtv-app .yt-filter-option:not(.active):before{content:'';display:inline-block;width:18px}
#fmtv-app .yt-filter-foot{position:sticky;bottom:0;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 20px;background:#232325;border-top:1px solid #36373b}
#fmtv-app .yt-filter-summary{color:#94969e;font-size:10px}
#fmtv-app .yt-filter-actions{display:flex;gap:8px}
#fmtv-app .yt-filter-clear,#fmtv-app .yt-filter-apply{min-height:38px;padding:0 15px;border-radius:19px;font-size:11px;font-weight:900;cursor:pointer}
#fmtv-app .yt-filter-clear{border:1px solid #47484f;background:#2a2a2d;color:#eee}
#fmtv-app .yt-filter-apply{border:0;background:#f1f1f1;color:#111!important}
#fmtv-app .yt-watched-badge{position:absolute;z-index:3;left:7px;bottom:7px;padding:4px 6px;border-radius:5px;background:rgba(0,0,0,.82);color:#ddd;font-size:8px;font-weight:900;pointer-events:none}
@media(max-width:900px){#fmtv-app .yt-filter-groups{grid-template-columns:repeat(2,minmax(0,1fr))}#fmtv-app .yt-filter-group:nth-child(2){border-right:0}#fmtv-app .yt-filter-group:nth-child(-n+2){border-bottom:1px solid #38383c}}
@media(max-width:560px){#fmtv-app .yt-filter-modal{padding:8px;align-items:flex-end}#fmtv-app .yt-filter-box{width:100%;max-height:88vh;border-radius:18px 18px 0 0}#fmtv-app .yt-filter-groups{grid-template-columns:1fr;padding:6px 14px}#fmtv-app .yt-filter-group{border-right:0!important;border-bottom:1px solid #38383c!important;padding:12px 8px}#fmtv-app .yt-filter-group:last-child{border-bottom:0!important}#fmtv-app .yt-filter-foot{align-items:flex-start;flex-direction:column}#fmtv-app .yt-filter-actions{width:100%}#fmtv-app .yt-filter-clear,#fmtv-app .yt-filter-apply{flex:1}}
'''
s=s.replace('</style>',css+'\n</style>',1)

old_actions='<div class="yt-top-actions"><button class="yt-pill active" data-mode="latest" type="button">Latest</button><button class="yt-pill" data-mode="trending" type="button">Trending 24h</button><button class="yt-pill fav" data-mode="favourites" type="button">★ My Channels <span id="fmtv-fav-count">0</span></button></div>'
new_actions='<div class="yt-top-actions"><button class="yt-pill yt-filter-trigger" id="fmtv-filter-open" type="button">☷ Filters <span class="filter-count" id="fmtv-filter-count">0</span></button><button class="yt-pill active" data-mode="latest" type="button">Latest</button><button class="yt-pill" data-mode="trending" type="button">Trending 24h</button><button class="yt-pill fav" data-mode="favourites" type="button">★ My Channels <span id="fmtv-fav-count">0</span></button></div>'
if old_actions not in s: raise SystemExit('top actions marker not found')
s=s.replace(old_actions,new_actions,1)

modal_html=r'''<div class="yt-filter-modal" id="fmtv-filter-modal" role="dialog" aria-modal="true" aria-label="FM TV search filters">
  <div class="yt-filter-box">
    <div class="yt-filter-head"><h3>Search filters</h3><button class="yt-filter-x" id="fmtv-filter-close" type="button" aria-label="Close filters">×</button></div>
    <div class="yt-filter-groups">
      <div class="yt-filter-group"><div class="yt-filter-label">Duration</div><button class="yt-filter-option" data-filter-group="duration" data-filter-value="any">Any duration</button><button class="yt-filter-option" data-filter-group="duration" data-filter-value="under10">Under 10 minutes</button><button class="yt-filter-option" data-filter-group="duration" data-filter-value="10to30">10–30 minutes</button><button class="yt-filter-option" data-filter-group="duration" data-filter-value="30to60">30–60 minutes</button><button class="yt-filter-option" data-filter-group="duration" data-filter-value="over60">Over 60 minutes</button></div>
      <div class="yt-filter-group"><div class="yt-filter-label">Upload date</div><button class="yt-filter-option" data-filter-group="date" data-filter-value="any">Any time</button><button class="yt-filter-option" data-filter-group="date" data-filter-value="today">Today</button><button class="yt-filter-option" data-filter-group="date" data-filter-value="week">This week</button><button class="yt-filter-option" data-filter-group="date" data-filter-value="month">This month</button><button class="yt-filter-option" data-filter-group="date" data-filter-value="year">This year</button></div>
      <div class="yt-filter-group"><div class="yt-filter-label">Watch status</div><button class="yt-filter-option" data-filter-group="watched" data-filter-value="all">All videos</button><button class="yt-filter-option" data-filter-group="watched" data-filter-value="unwatched">Unwatched</button><button class="yt-filter-option" data-filter-group="watched" data-filter-value="watched">Watched</button></div>
      <div class="yt-filter-group"><div class="yt-filter-label">Prioritise</div><button class="yt-filter-option" data-filter-group="sort" data-filter-value="relevance">Relevance</button><button class="yt-filter-option" data-filter-group="sort" data-filter-value="newest">Newest</button><button class="yt-filter-option" data-filter-group="sort" data-filter-value="popularity">Popularity</button><button class="yt-filter-option" data-filter-group="sort" data-filter-value="trending">Trending 24h</button></div>
    </div>
    <div class="yt-filter-foot"><div class="yt-filter-summary" id="fmtv-filter-summary">No extra filters applied</div><div class="yt-filter-actions"><button class="yt-filter-clear" id="fmtv-filter-clear" type="button">Clear</button><button class="yt-filter-apply" id="fmtv-filter-apply" type="button">Apply filters</button></div></div>
  </div>
</div>
'''
video_modal='<div class="yt-modal" id="fmtv-modal">'
if video_modal not in s: raise SystemExit('video modal marker not found')
s=s.replace(video_modal,modal_html+video_modal,1)

old_keys="var RECENT='https://raw.githubusercontent.com/FMBlogAPP/fm-blog-transfer-centre/main/fm-tv/data/videos.json',ARCHIVE='https://raw.githubusercontent.com/FMBlogAPP/fm-blog-transfer-centre/main/fm-tv/data/archive.json',FKEY='fmTvFavouriteCreatorsV1',root=document.getElementById('fmtv-app');if(!root)return;"
new_keys="var RECENT='https://raw.githubusercontent.com/FMBlogAPP/fm-blog-transfer-centre/main/fm-tv/data/videos.json',ARCHIVE='https://raw.githubusercontent.com/FMBlogAPP/fm-blog-transfer-centre/main/fm-tv/data/archive.json',FKEY='fmTvFavouriteCreatorsV1',WKEY='fmTvWatchedVideosV1',root=document.getElementById('fmtv-app');if(!root)return;"
if old_keys not in s: raise SystemExit('keys marker not found')
s=s.replace(old_keys,new_keys,1)

old_state="state={data:null,archive:null,archiveLoading:false,mode:'latest',category:'',creator:'',query:'',creatorQuery:'',shown:12,searchTimer:null,favs:new Set()};try{state.favs=new Set(JSON.parse(localStorage.getItem(FKEY)||'[]'))}catch(err){state.favs=new Set()}"
new_state="state={data:null,archive:null,archiveLoading:false,mode:'latest',category:'',creator:'',query:'',creatorQuery:'',shown:12,searchTimer:null,favs:new Set(),watched:new Set(),filters:{duration:'any',date:'any',watched:'all',sort:'relevance'},draftFilters:null};try{state.favs=new Set(JSON.parse(localStorage.getItem(FKEY)||'[]'))}catch(err){state.favs=new Set()}try{state.watched=new Set(JSON.parse(localStorage.getItem(WKEY)||'[]'))}catch(err){state.watched=new Set()}"
if old_state not in s: raise SystemExit('state marker not found')
s=s.replace(old_state,new_state,1)

old_el="load:$('#fmtv-load'),modal:$('#fmtv-modal'),modalTitle:$('#fmtv-modal-title'),player:$('#fmtv-player'),close:$('#fmtv-close')};"
new_el="load:$('#fmtv-load'),filterOpen:$('#fmtv-filter-open'),filterCount:$('#fmtv-filter-count'),filterModal:$('#fmtv-filter-modal'),filterClose:$('#fmtv-filter-close'),filterClear:$('#fmtv-filter-clear'),filterApply:$('#fmtv-filter-apply'),filterSummary:$('#fmtv-filter-summary'),modal:$('#fmtv-modal'),modalTitle:$('#fmtv-modal-title'),player:$('#fmtv-player'),close:$('#fmtv-close')};"
if old_el not in s: raise SystemExit('element map marker not found')
s=s.replace(old_el,new_el,1)

old_save="function saveFavs(){try{localStorage.setItem(FKEY,JSON.stringify(Array.from(state.favs)))}catch(err){}}"
new_save=old_save+"function saveWatched(){try{var a=Array.from(state.watched);if(a.length>500){a=a.slice(a.length-500);state.watched=new Set(a)}localStorage.setItem(WKEY,JSON.stringify(a))}catch(err){}}function markWatched(id){if(!id)return;state.watched.add(id);saveWatched()}function defaultFilters(){return{duration:'any',date:'any',watched:'all',sort:'relevance'}}function filterCount(){var f=state.filters,n=0;if(f.duration!=='any')n++;if(f.date!=='any')n++;if(f.watched!=='all')n++;if(f.sort!=='relevance')n++;return n}function filtersActive(){return filterCount()>0}function closeFilters(){el.filterModal.classList.remove('open');document.documentElement.style.overflow=''}function updateFilterUI(){var f=state.draftFilters||state.filters;root.querySelectorAll('[data-filter-group]').forEach(function(b){b.classList.toggle('active',f[b.getAttribute('data-filter-group')]===b.getAttribute('data-filter-value'))});var n=filterCount();el.filterCount.textContent=n;el.filterOpen.classList.toggle('has-filters',n>0);el.filterSummary.textContent=n?n+' filter'+(n===1?'':'s')+' applied':'No extra filters applied'}function openFilters(){state.draftFilters=Object.assign({},state.filters);updateFilterUI();el.filterModal.classList.add('open');document.documentElement.style.overflow='hidden'}"
if old_save not in s: raise SystemExit('save favs marker not found')
s=s.replace(old_save,new_save,1)

old_open="function openVideo(v){if(!v)return;el.modalTitle.textContent=v.title;var src='https://www.youtube.com/embed/'+encodeURIComponent(v.id)+'?autoplay=1&rel=0';"
new_open="function openVideo(v){if(!v)return;markWatched(v.id);el.modalTitle.textContent=v.title;var src='https://www.youtube.com/embed/'+encodeURIComponent(v.id)+'?autoplay=1&rel=0';"
if old_open not in s: raise SystemExit('open video marker not found')
s=s.replace(old_open,new_open,1)

old_hash="function setHash(){var p=[];if(state.creator)p.push('creator='+encodeURIComponent(state.creator));else{if(state.mode!=='latest')p.push('mode='+encodeURIComponent(state.mode));if(state.category)p.push('category='+encodeURIComponent(state.category))}var h=p.length?'#'+p.join('&'):'';if(location.hash!==h)history.replaceState(null,'',location.pathname+location.search+h)}function readHash(){var raw=location.hash.replace(/^#/,'');if(!raw)return;var p=new URLSearchParams(raw),creator=p.get('creator'),mode=p.get('mode'),category=p.get('category');if(creator)state.creator=creator;if(mode&&['latest','trending','favourites'].indexOf(mode)>-1)state.mode=mode;if(category)state.category=category}"
new_hash="function setHash(){var p=[];if(state.creator)p.push('creator='+encodeURIComponent(state.creator));else{if(state.mode!=='latest')p.push('mode='+encodeURIComponent(state.mode));if(state.category)p.push('category='+encodeURIComponent(state.category))}if(state.query.trim())p.push('q='+encodeURIComponent(state.query.trim()));var f=state.filters;if(f.duration!=='any')p.push('duration='+encodeURIComponent(f.duration));if(f.date!=='any')p.push('date='+encodeURIComponent(f.date));if(f.watched!=='all')p.push('watched='+encodeURIComponent(f.watched));if(f.sort!=='relevance')p.push('sort='+encodeURIComponent(f.sort));var h=p.length?'#'+p.join('&'):'';if(location.hash!==h)history.replaceState(null,'',location.pathname+location.search+h)}function readHash(){var raw=location.hash.replace(/^#/,'');if(!raw)return;var p=new URLSearchParams(raw),creator=p.get('creator'),mode=p.get('mode'),category=p.get('category'),q=p.get('q'),duration=p.get('duration'),date=p.get('date'),watched=p.get('watched'),sort=p.get('sort');if(creator)state.creator=creator;if(mode&&['latest','trending','favourites'].indexOf(mode)>-1)state.mode=mode;if(category)state.category=category;if(q){state.query=q;if(el.search)el.search.value=q}if(['any','under10','10to30','30to60','over60'].indexOf(duration)>-1)state.filters.duration=duration;if(['any','today','week','month','year'].indexOf(date)>-1)state.filters.date=date;if(['all','unwatched','watched'].indexOf(watched)>-1)state.filters.watched=watched;if(['relevance','newest','popularity','trending'].indexOf(sort)>-1)state.filters.sort=sort}"
if old_hash not in s: raise SystemExit('hash marker not found')
s=s.replace(old_hash,new_hash,1)

old_home="function goHome(){state.creator='';state.mode='latest';state.category='';state.query='';state.shown=12;el.search.value='';renderAll();setHash();scrollToNode(el.homeOnly)}"
new_home="function goHome(){state.creator='';state.mode='latest';state.category='';state.query='';state.filters=defaultFilters();state.shown=12;el.search.value='';renderAll();setHash();updateFilterUI();scrollToNode(el.homeOnly)}"
if old_home not in s: raise SystemExit('goHome marker not found')
s=s.replace(old_home,new_home,1)

old_card="<div class=\"yt-thumb\" data-play=\"'+esc(v.id)+'\"><img src=\"'+esc(v.thumbnail)+'\" alt=\"'+esc(v.title)+'\" loading=\"lazy\" decoding=\"async\">'+(fresh(v.publishedAt)?'<span class=\"yt-new\">New</span>':'')+'<span class=\"yt-duration\">'+esc(v.duration)+'</span></div>"
new_card="<div class=\"yt-thumb\" data-play=\"'+esc(v.id)+'\"><img src=\"'+esc(v.thumbnail)+'\" alt=\"'+esc(v.title)+'\" loading=\"lazy\" decoding=\"async\">'+(fresh(v.publishedAt)?'<span class=\"yt-new\">New</span>':'')+(state.watched.has(v.id)?'<span class=\"yt-watched-badge\">Watched</span>':'')+'<span class=\"yt-duration\">'+esc(v.duration)+'</span></div>"
if old_card not in s: raise SystemExit('card thumbnail marker not found')
s=s.replace(old_card,new_card,1)

start=s.index('function wantsArchive(){')
end=s.index('function renderFavShelf(){',start)
new_filter=r'''function wantsArchive(){return!!state.creator||!!state.category||state.mode==='favourites'||state.query.trim().length>=2||filtersActive()}function pool(){return state.archive&&wantsArchive()?state.archive.videos:((state.data&&state.data.videos)||[])}function relevanceScore(v,q,terms){if(!q)return 0;var title=(v.title||'').toLowerCase(),channel=(v.channelName||'').toLowerCase(),cat=(v.category||'').toLowerCase(),desc=(v.description||'').toLowerCase(),score=0;if(title===q)score+=120;if(title.indexOf(q)===0)score+=80;if(title.indexOf(q)>-1)score+=55;if(channel.indexOf(q)>-1)score+=35;if(cat.indexOf(q)>-1)score+=28;terms.forEach(function(t){if(title.indexOf(t)>-1)score+=18;if(desc.indexOf(t)>-1)score+=5});return score}function filtered(){var arr=pool().slice();if(state.creator)arr=arr.filter(function(v){return v.channelId===state.creator});if(state.category)arr=arr.filter(function(v){return v.category===state.category});var q=state.query.trim().toLowerCase(),terms=[];if(q){terms=[q];if(q.length>3&&q.slice(-1)==='s')terms.push(q.slice(0,-1));else if(q.length>3)terms.push(q+'s');arr=arr.filter(function(v){var hay=(v.title+' '+v.channelName+' '+v.category+' '+(v.description||'')).toLowerCase();return terms.some(function(t){return hay.indexOf(t)>-1})})}if(state.mode==='favourites')arr=arr.filter(function(v){return state.favs.has(v.channelId)});var f=state.filters;if(f.duration!=='any')arr=arr.filter(function(v){var d=Number(v.durationSeconds)||0;if(f.duration==='under10')return d<600;if(f.duration==='10to30')return d>=600&&d<1800;if(f.duration==='30to60')return d>=1800&&d<3600;if(f.duration==='over60')return d>=3600;return true});if(f.date!=='any'){var ages={today:86400000,week:604800000,month:2592000000,year:31536000000},max=ages[f.date]||0;if(max)arr=arr.filter(function(v){return Date.now()-new Date(v.publishedAt).getTime()<=max})}if(f.watched==='watched')arr=arr.filter(function(v){return state.watched.has(v.id)});else if(f.watched==='unwatched')arr=arr.filter(function(v){return!state.watched.has(v.id)});if(state.mode==='trending'||f.sort==='trending')arr.sort(function(a,b){var av=a.views24h==null?-1:a.views24h,bv=b.views24h==null?-1:b.views24h;return bv-av||(b.trendingScore||0)-(a.trendingScore||0)});else if(f.sort==='popularity')arr.sort(function(a,b){return(Number(b.views)||0)-(Number(a.views)||0)||new Date(b.publishedAt)-new Date(a.publishedAt)});else if(f.sort==='newest')arr.sort(function(a,b){return new Date(b.publishedAt)-new Date(a.publishedAt)});else if(q)arr.sort(function(a,b){return relevanceScore(b,q,terms)-relevanceScore(a,q,terms)||new Date(b.publishedAt)-new Date(a.publishedAt)});else arr.sort(function(a,b){return new Date(b.publishedAt)-new Date(a.publishedAt)});return arr}'''
s=s[:start]+new_filter+s[end:]

old_render_end="el.count.textContent=arr.length+' video'+(arr.length===1?'':'s');el.load.style.display=(arr.length>state.shown||(state.creator&&!state.archive))?'inline-block':'none'}"
new_render_end="el.count.textContent=arr.length+' video'+(arr.length===1?'':'s');el.load.style.display=(arr.length>state.shown||(state.creator&&!state.archive))?'inline-block':'none';updateFilterUI()}"
if old_render_end not in s: raise SystemExit('renderGrid end marker not found')
s=s.replace(old_render_end,new_render_end,1)

idx=s.index("el.search.addEventListener('input'")
filter_listeners=r'''el.filterOpen.addEventListener('click',openFilters);el.filterClose.addEventListener('click',closeFilters);el.filterModal.addEventListener('click',function(ev){if(ev.target===el.filterModal)closeFilters()});root.querySelectorAll('[data-filter-group]').forEach(function(b){b.addEventListener('click',function(){if(!state.draftFilters)state.draftFilters=Object.assign({},state.filters);state.draftFilters[b.getAttribute('data-filter-group')]=b.getAttribute('data-filter-value');updateFilterUI()})});el.filterClear.addEventListener('click',function(){state.draftFilters=defaultFilters();updateFilterUI()});el.filterApply.addEventListener('click',function(){state.filters=Object.assign({},state.draftFilters||defaultFilters());state.draftFilters=null;state.shown=24;closeFilters();renderGrid();bindInteractive(root);setHash();scrollToNode(el.gridSection);if(filtersActive()&&!state.archive)ensureArchive()});'''
s=s[:idx]+filter_listeners+s[idx:]

old_escape="document.addEventListener('keydown',function(ev){if(ev.key==='Escape')closeVideo()});"
new_escape="document.addEventListener('keydown',function(ev){if(ev.key==='Escape'){if(el.filterModal.classList.contains('open'))closeFilters();else closeVideo()}});"
if old_escape not in s: raise SystemExit('escape listener marker not found')
s=s.replace(old_escape,new_escape,1)

old_hashchange="window.addEventListener('hashchange',function(){state.creator='';state.mode='latest';state.category='';readHash();state.shown=12;renderAll();if(wantsArchive()&&!state.archive)ensureArchive()});"
new_hashchange="window.addEventListener('hashchange',function(){state.creator='';state.mode='latest';state.category='';state.query='';state.filters=defaultFilters();el.search.value='';readHash();state.shown=24;renderAll();if(wantsArchive()&&!state.archive)ensureArchive()});"
if old_hashchange not in s: raise SystemExit('hashchange marker not found')
s=s.replace(old_hashchange,new_hashchange,1)

out.write_text(s,encoding='utf-8')
print('built',out,len(s))
