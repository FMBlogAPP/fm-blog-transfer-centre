from pathlib import Path

src = Path('assets/transfer-centre-v41.js')
out = Path('assets/transfer-centre-v42.js')
app_path = Path('transfer-centre-app-v4.html')

s = src.read_text(encoding='utf-8')

old = "function closeEntity(push=true){currentEntity=null;root()?.classList.remove('entity-active');const d=$('.detail-view');if(d){d.classList.remove('show');d.style.removeProperty('display');d.innerHTML=''}if(push)writeUrl(null,state.mode,true);render();scrollTo($('.workspace'))}"
new = "function leaveEntityView(){currentEntity=null;root()?.classList.remove('entity-active');const d=$('.detail-view');if(d){d.classList.remove('show');d.style.removeProperty('display');d.removeAttribute('hidden');d.innerHTML=''}state.entityTab='all';requestFrameResize()}\nfunction closeEntity(push=true){leaveEntityView();if(push)writeUrl(null,state.mode,true);render();scrollTo($('.workspace'))}"
if old not in s: raise SystemExit('closeEntity pattern not found')
s = s.replace(old,new)

old = "function setMode(mode,push=true){state.mode=mode;state.limit=50;currentEntity=null;$('.detail-view').classList.remove('show');if(['radar','u21','u23','freeu23','balkan','southamerica','mls','watchlist','new','last24','free','loan'].includes(mode))loadFull().then(()=>{render();watchlistSummary()});else{render();watchlistSummary()}if(push)writeUrl(null,mode,true);scrollTo($('.controls-shell'))}"
new = "function setMode(mode,push=true){leaveEntityView();state.mode=mode;state.limit=50;if(['radar','u21','u23','freeu23','balkan','southamerica','mls','watchlist','new','last24','free','loan'].includes(mode))loadFull().then(()=>{render();watchlistSummary();scrollTo($('.workspace'))});else{render();watchlistSummary();scrollTo($('.workspace'))}if(push)writeUrl(null,mode,true)}"
if old not in s: raise SystemExit('setMode pattern not found')
s = s.replace(old,new)

old = "function clearAll(){state={q:'',nation:'',league:'',type:'',mode:'latest',limit:50,entityTab:'all'};currentEntity=null;$('.q').value='';$('.detail-view').classList.remove('show');$('.detail-view').innerHTML='';rebuildLeague();syncDropdowns();render();watchlistSummary();writeUrl(null,'latest',true)}"
new = "function clearAll(){leaveEntityView();state={q:'',nation:'',league:'',type:'',mode:'latest',limit:50,entityTab:'all'};$('.q').value='';rebuildLeague();syncDropdowns();render();watchlistSummary();writeUrl(null,'latest',true);scrollTo($('.workspace'))}"
if old not in s: raise SystemExit('clearAll pattern not found')
s = s.replace(old,new)

old = "const item=e.target.closest('.dd-item');if(item){const box=item.closest('.dd'),v=item.dataset.value||'';"
new = "const item=e.target.closest('.dd-item');if(item){leaveEntityView();const box=item.closest('.dd'),v=item.dataset.value||'';"
if old not in s: raise SystemExit('dropdown start pattern not found')
s = s.replace(old,new)

old = "state.limit=50;syncDropdowns();await loadFull();render();return}const quick=e.target.closest('.quickbtn');if(quick){state.nation=quick.dataset.country;"
new = "state.limit=50;syncDropdowns();writeUrl(null,state.mode,true);await loadFull();render();scrollTo($('.workspace'));return}const quick=e.target.closest('.quickbtn');if(quick){leaveEntityView();state.nation=quick.dataset.country;"
if old not in s: raise SystemExit('dropdown/quick bridge pattern not found')
s = s.replace(old,new)

old = "state.limit=50;rebuildLeague();syncDropdowns();await loadFull();render();return}const mode=e.target.closest('[data-mode]');"
new = "state.limit=50;rebuildLeague();syncDropdowns();writeUrl(null,state.mode,true);await loadFull();render();scrollTo($('.workspace'));return}const mode=e.target.closest('[data-mode]');"
if old not in s: raise SystemExit('quick end pattern not found')
s = s.replace(old,new)

old = "$('.q').addEventListener('input',()=>{clearTimeout(st);state.q=$('.q').value;state.limit=50;st=setTimeout(async()=>{if(state.q.trim())await loadFull();render()},180)})"
new = "$('.q').addEventListener('input',()=>{clearTimeout(st);if(currentEntity){leaveEntityView();writeUrl(null,state.mode,false)}state.q=$('.q').value;state.limit=50;st=setTimeout(async()=>{if(state.q.trim())await loadFull();render()},180)})"
if old not in s: raise SystemExit('search pattern not found')
s = s.replace(old,new)

out.write_text(s,encoding='utf-8')

app = app_path.read_text(encoding='utf-8')
app = app.replace('assets/transfer-centre-v41.js','assets/transfer-centre-v42.js')
app_path.write_text(app,encoding='utf-8')
print('Built V4.2 global navigation state reset.')
