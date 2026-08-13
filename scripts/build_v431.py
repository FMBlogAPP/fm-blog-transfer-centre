from pathlib import Path

src = Path('assets/transfer-centre-v43.js')
out = Path('assets/transfer-centre-v431.js')
app_path = Path('transfer-centre-app-v4.html')

s = src.read_text(encoding='utf-8')
old = "async function openEntity(e,push=true,fallbackHref=''){\n  currentEntity=e;state.entityTab='all';state.limit=50;root()?.classList.add('entity-active');"
new = "async function openEntity(e,push=true,fallbackHref=''){\n  currentEntity=e;state.entityTab='all';state.limit=50;root()?.classList.add('entity-active');\n  if(e.type==='nation'){state.nation=e.id;state.league='';rebuildLeague();syncDropdowns()}\n  if(e.type==='league'){state.nation=e.country||'';state.league=e.country?`${e.country}|||${e.id}`:'';rebuildLeague();syncDropdowns()}"
if old not in s:
    raise SystemExit('openEntity pattern not found')
s = s.replace(old,new,1)
out.write_text(s,encoding='utf-8')

app = app_path.read_text(encoding='utf-8')
if 'assets/transfer-centre-v43.js' not in app:
    raise SystemExit('V4.3 runtime ref not found')
app = app.replace('assets/transfer-centre-v43.js','assets/transfer-centre-v431.js',1)
app_path.write_text(app,encoding='utf-8')
print('Built V4.3.1 entity/filter synchronisation.')
