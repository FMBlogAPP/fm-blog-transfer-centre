from pathlib import Path

src_path = Path('assets/transfer-centre-v4.js')
out_path = Path('assets/transfer-centre-v41.js')
app_path = Path('transfer-centre-app-v4.html')

s = src_path.read_text(encoding='utf-8')

old = "function renderEntityRows(){let rr=detailRows();if(currentEntity?.type==='club'){if(state.entityTab==='incoming')rr=rr.filter(t=>String(t.to_id)===String(currentEntity.id));if(state.entityTab==='outgoing')rr=rr.filter(t=>String(t.from_id)===String(currentEntity.id));if(state.entityTab==='loans')rr=rr.filter(t=>kind(t)==='loan');if(state.entityTab==='free')rr=rr.filter(t=>kind(t)==='free')}rr.sort((a,b)=>(b.date||'').localeCompare(a.date||''));$('.detail-view').innerHTML=entityHeader(detailRows());$('.detail-view').classList.add('show');$('.count').textContent=nf(rr.length);$('.rows').innerHTML=rr.length?rr.map(rowHtml).join(''):'<div class=\"empty\"><b>No transfers found.</b></div>';$('.load').hidden=true;renderDetailActions()}"
new = "function entityFilteredRows(){let rr=detailRows();if(currentEntity?.type==='club'){if(state.entityTab==='incoming')rr=rr.filter(t=>String(t.to_id)===String(currentEntity.id));if(state.entityTab==='outgoing')rr=rr.filter(t=>String(t.from_id)===String(currentEntity.id));if(state.entityTab==='loans')rr=rr.filter(t=>kind(t)==='loan');if(state.entityTab==='free')rr=rr.filter(t=>kind(t)==='free')}rr.sort((a,b)=>(b.date||'').localeCompare(a.date||''));return rr}\nfunction renderEntityRows(){const rr=entityFilteredRows(),shown=rr.slice(0,state.limit),detail=$('.detail-view');if(detail){detail.innerHTML=entityHeader(detailRows());detail.classList.add('show');detail.style.setProperty('display','block','important');detail.removeAttribute('hidden')}root()?.classList.add('entity-active');$('.count').textContent=nf(rr.length);$('.rows').innerHTML=shown.length?shown.map(rowHtml).join(''):'<div class=\"empty\"><b>No transfers found.</b></div>';const load=$('.load'),btn=$('.loadmore');if(load)load.hidden=rr.length<=state.limit;if(btn)btn.textContent=rr.length>state.limit?`Load ${Math.min(50,rr.length-state.limit)} more transfers`:'All transfers loaded';renderDetailActions();requestFrameResize()}"
if old not in s:
    raise SystemExit('renderEntityRows pattern not found')
s = s.replace(old, new)

old = "async function openEntity(e,push=true,fallbackHref=''){\n  currentEntity=e;state.entityTab='all';"
new = "async function openEntity(e,push=true,fallbackHref=''){\n  currentEntity=e;state.entityTab='all';state.limit=50;root()?.classList.add('entity-active');"
if old not in s:
    raise SystemExit('openEntity pattern not found')
s = s.replace(old, new)

old = "function closeEntity(push=true){currentEntity=null;$('.detail-view').classList.remove('show');$('.detail-view').innerHTML='';if(push)writeUrl(null,state.mode,true);render();scrollTo($('.controls-shell'))}"
new = "function closeEntity(push=true){currentEntity=null;root()?.classList.remove('entity-active');const d=$('.detail-view');if(d){d.classList.remove('show');d.style.removeProperty('display');d.innerHTML=''}if(push)writeUrl(null,state.mode,true);render();scrollTo($('.workspace'))}"
if old not in s:
    raise SystemExit('closeEntity pattern not found')
s = s.replace(old, new)

old = "const load=e.target.closest('.loadmore');if(load){const a=modeFilter(rows());if(!db&&state.limit+50>a.length)await loadFull();state.limit+=50;render();return}"
new = "const load=e.target.closest('.loadmore');if(load){load.disabled=true;load.textContent='Loading…';try{if(!db)await loadFull();state.limit+=50;render()}finally{load.disabled=false}return}"
if old not in s:
    raise SystemExit('loadmore pattern not found')
s = s.replace(old, new)

old = "$('.loadmore').textContent=!db&&state.limit>=a.length?'Load full database':'Load more';"
new = "$('.loadmore').textContent=!db?'Load 50 more transfers':a.length>state.limit?`Load ${Math.min(50,a.length-state.limit)} more transfers`:'All transfers loaded';"
if old not in s:
    raise SystemExit('render load button pattern not found')
s = s.replace(old, new)

# Add a lightweight frame resize notifier callable after every render/detail render.
marker = "function setDbState(t){const e=$('.db-state');if(e)e.textContent=t}"
replacement = marker + "\nfunction requestFrameResize(){requestAnimationFrame(()=>{try{const app=root();if(!app)return;const h=Math.ceil(app.getBoundingClientRect().height)+4;if(window.frameElement&&window.parent!==window)window.frameElement.style.height=Math.max(700,h)+'px';window.parent?.postMessage?.({type:'fmbtc-height',height:h},'*')}catch(e){}})}"
if marker not in s:
    raise SystemExit('setDbState marker not found')
s = s.replace(marker, replacement)

# Ensure every ordinary render also asks the iframe to shrink/grow.
old = "syncActive();renderModeIntro(a);watchlistSummary()}"
new = "syncActive();renderModeIntro(a);watchlistSummary();requestFrameResize()}"
if old not in s:
    raise SystemExit('render tail pattern not found')
s = s.replace(old, new, 1)

out_path.write_text(s, encoding='utf-8')

app = app_path.read_text(encoding='utf-8')
app = app.replace('min-height:100%!important;', 'min-height:0!important;height:auto!important;')
app = app.replace('.detail-view.show{display:block}', '.detail-view.show{display:block!important}')
app = app.replace('assets/transfer-centre-v4.js', 'assets/transfer-centre-v41.js')

# Replace the old scrollHeight-based bridge with root-height measurement to avoid iframe feedback loops.
old_bridge = """<script>\n(function(){\n  function sendHeight(){\n    var h=Math.max(document.documentElement.scrollHeight,document.body?document.body.scrollHeight:0);\n    parent.postMessage({type:'fmbtc-height',height:h},'*');\n  }\n  window.addEventListener('load',sendHeight);\n  window.addEventListener('resize',sendHeight);"""
new_bridge = """<script>\n(function(){\n  function sendHeight(){\n    var app=document.getElementById('fmbtc');\n    var h=app?Math.ceil(app.getBoundingClientRect().height)+4:700;\n    try{if(window.frameElement&&parent!==window)window.frameElement.style.height=Math.max(700,h)+'px';}catch(e){}\n    parent.postMessage({type:'fmbtc-height',height:h},'*');\n  }\n  window.addEventListener('load',sendHeight);\n  window.addEventListener('resize',sendHeight);"""
if old_bridge in app:
    app = app.replace(old_bridge, new_bridge)

app_path.write_text(app, encoding='utf-8')
print('Built V4.1 runtime, forced entity detail visibility, paginated entity rows, and fixed iframe height feedback.')
