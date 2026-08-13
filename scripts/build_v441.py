from pathlib import Path

src = Path('assets/transfer-centre-v44.js')
out = Path('assets/transfer-centre-v441.js')
app_path = Path('transfer-centre-app-v4.html')

s = src.read_text(encoding='utf-8')


def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'{label} pattern not found')
    s = s.replace(old, new, 1)


old = "function infoCell(label,value){if(value===undefined||value===null||value==='')return'';return `<div class=\"hub-info-cell\"><span>${esc(label)}</span><b>${esc(value)}</b></div>`}"
new = """function infoCell(label,value){if(value===undefined||value===null||value==='')return'';return `<div class=\"hub-info-cell\"><span>${esc(label)}</span><b>${esc(value)}</b></div>`}
function findHubPlayer(id){
  const key=String(id||'');
  const direct=hubData?.players?.[key];
  if(direct)return direct;
  for(const [teamId,squad] of Object.entries(hubData?.squads||{})){
    const p=(squad||[]).find(x=>String(x.id)===key);
    if(p)return {...p,team_id:Number(teamId)};
  }
  return null;
}"""
rep(old, new, 'hub player fallback helper')

old = """function playerHubHtml(id){
  const p=hubData?.players?.[String(id)];
  if(!p)return `<section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>PLAYER DATA</span><h4>Player profile</h4></div></div><div class=\"hub-note\">This player profile is still being enriched.</div></section>`;
  const birth=p.birth||{},club=hubData?.clubs?.[String(p.team_id)]||{},currentClub=club.name||club.team?.name||'';"""
new = """function playerHubHtml(id){
  const p=findHubPlayer(id);
  if(!p)return `<section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>PLAYER DATA</span><h4>Player profile</h4></div></div><div class=\"hub-note\">This player profile is still being enriched.</div></section>`;
  const latest=[...detailRows()].sort((a,b)=>(b.date||'').localeCompare(a.date||''))[0]||{};
  const birth=p.birth||{},club=hubData?.clubs?.[String(p.team_id)]||{};
  const currentClub=(kind(latest)==='free'&&latest.to_free_agent)?'Free agent':(club.name||club.team?.name||'');"""
rep(old, new, 'player hub fallback')

old = """}else if(e.type==='player'){const t=[...rr].sort((a,b)=>(b.date||'').localeCompare(a.date||''))[0]||{};title=displayPlayer(t)||e.name||'Player';eyebrow='Player Hub';icon=`<img class=\"detail-logo player-photo\" src=\"${esc(t.player_photo)}\" alt=\"${esc(title)}\">`;sub=`${t.position?`<span>${esc(t.position)}</span>`:''}${age(t)!==null?`<span class=\"dot\">•</span><span>${age(t)} years old</span>`:''}`;stats=[[rr.length,'Transfer records'],[age(t)??'—','Age'],[t.position||'—','Position'],[t.to||'—','Latest destination']];insight=t.date?`Latest tracked move: ${t.from} → ${t.to} on ${t.date}`:''}"""
new = """}else if(e.type==='player'){const t=[...rr].sort((a,b)=>(b.date||'').localeCompare(a.date||''))[0]||{},hp=findHubPlayer(e.id)||{},pAge=age(t)??hp.age??null,pPos=t.position||hp.position||'',pPhoto=t.player_photo||hp.photo||'',club=hubData?.clubs?.[String(hp.team_id)]||{},currentClub=(kind(t)==='free'&&t.to_free_agent)?'Free agent':(club.name||club.team?.name||'');title=e.name||hp.name||(rr.length?displayPlayer(t):'Player');eyebrow='Player Hub';icon=pPhoto?`<img class=\"detail-logo player-photo\" src=\"${esc(pPhoto)}\" alt=\"${esc(title)}\">`:'<div class=\"detail-fallback\">P</div>';sub=`${pPos?`<span>${esc(pPos)}</span>`:''}${pAge!==null?`<span class=\"dot\">•</span><span>${esc(pAge)} years old</span>`:''}`;stats=[[rr.length,'Transfer records'],[pAge??'—','Age'],[pPos||'—','Position'],[t.to||currentClub||'—','Current / latest club']];insight=t.date?`Latest tracked move: ${t.from} → ${t.to} on ${t.date}`:(currentClub?`Current squad: ${currentClub}`:'')}"""
rep(old, new, 'player entity header fallback')

old = "if(currentEntity.type==='player'){const t=rr[0]||{};meta.label=displayPlayer(t)||meta.label;meta.logo=t.player_photo}"
new = "if(currentEntity.type==='player'){const t=rr[0]||{},hp=findHubPlayer(currentEntity.id)||{};meta.label=(rr.length?displayPlayer(t):'')||hp.name||meta.label;meta.logo=t.player_photo||hp.photo}"
rep(old, new, 'player watch metadata')

out.write_text(s, encoding='utf-8')

app = app_path.read_text(encoding='utf-8')
if 'assets/transfer-centre-v44.js' in app:
    app = app.replace('assets/transfer-centre-v44.js', 'assets/transfer-centre-v441.js', 1)
elif 'assets/transfer-centre-v441.js' not in app:
    raise SystemExit('V4.4 runtime ref not found')
app_path.write_text(app, encoding='utf-8')
print('Built V4.4.1: squad-only players open useful Player Hubs.')
