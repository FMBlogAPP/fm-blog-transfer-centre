from pathlib import Path

src = Path('assets/transfer-centre-v431.js')
out = Path('assets/transfer-centre-v44.js')
app_path = Path('transfer-centre-app-v4.html')

s = src.read_text(encoding='utf-8')


def rep(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'{label} pattern not found')
    s = s.replace(old, new, 1)


rep(
    "const FEED=BASE+'data/feed.json', FULL=BASE+'data/transfers.json', CONFIG=BASE+'config.json';",
    "const FEED=BASE+'data/feed.json', FULL=BASE+'data/transfers.json', CONFIG=BASE+'config.json', HUB=BASE+'data/hub_profiles.json';",
    'data constants',
)

rep(
    "let cfg=null,feed=null,db=null,dbPromise=null,previousVisit=null,visitNow=new Date().toISOString(),currentEntity=null;",
    "let cfg=null,feed=null,db=null,dbPromise=null,hubData=null,hubPromise=null,previousVisit=null,visitNow=new Date().toISOString(),currentEntity=null;",
    'globals',
)

rep(
    "function cleanUrl(){const u=pageUrl();['club','player','league','nation','view'].forEach(k=>u.searchParams.delete(k));u.hash='';return u}",
    "function cleanUrl(){const u=pageUrl();['club','player','league','nation','hub','view'].forEach(k=>u.searchParams.delete(k));u.hash='';return u}",
    'cleanUrl',
)

old_write = "function writeUrl(entity,mode,push=true){try{const u=cleanUrl();if(entity?.type==='club')u.searchParams.set('club',entity.id);if(entity?.type==='player')u.searchParams.set('player',entity.id);if(entity?.type==='league'){u.searchParams.set('league',entity.id);u.searchParams.set('nation',entity.country)}if(entity?.type==='nation')u.searchParams.set('nation',entity.id);if(!entity&&mode&&mode!=='latest')u.searchParams.set('view',mode);(()=>{try{const h=(window.parent&&window.parent!==window)?window.parent.history:history;h[push?'pushState':'replaceState']({fmbtc:true},'',u)}catch(x){history[push?'pushState':'replaceState']({fmbtc:true},'',u)}})()}catch(e){}}"
new_write = "function writeUrl(entity,mode,push=true){try{const u=cleanUrl();if(entity?.type==='club')u.searchParams.set('club',entity.id);if(entity?.type==='player')u.searchParams.set('player',entity.id);if(entity?.type==='league'){u.searchParams.set('league',entity.id);u.searchParams.set('nation',entity.country)}if(entity?.type==='nation')u.searchParams.set('nation',entity.id);if(entity?.type==='hub')u.searchParams.set('hub',entity.id);if(!entity&&mode&&mode!=='latest')u.searchParams.set('view',mode);(()=>{try{const h=(window.parent&&window.parent!==window)?window.parent.history:history;h[push?'pushState':'replaceState']({fmbtc:true},'',u)}catch(x){history[push?'pushState':'replaceState']({fmbtc:true},'',u)}})()}catch(e){}}"
rep(old_write, new_write, 'writeUrl')

rep(
    "function rows(){return db||(feed?.transfers||[])}",
    "function loadHub(){if(hubData)return Promise.resolve(hubData);if(hubPromise)return hubPromise;hubPromise=fetch(HUB+'?v='+(feed?.meta?.feed_updated_at||feed?.meta?.updated_at||Date.now())).then(r=>{if(!r.ok)throw new Error('hub database');return r.json()}).then(d=>{hubData=d;return d}).catch(e=>{hubPromise=null;throw e});return hubPromise}\nfunction rows(){return db||(feed?.transfers||[])}",
    'hub loader',
)

rep(
    "eyebrow='Club Transfer Centre'",
    "eyebrow='Club Hub'",
    'club hub eyebrow',
)
rep(
    "eyebrow='Player Transfer Centre'",
    "eyebrow='Player Hub'",
    'player hub eyebrow',
)

old_move = '''function moveHtml(t){
  const fromHref=entityHref('club',t.from_id),toHref=entityHref('club',t.to_id);
  return `<div class=\"move\"><a class=\"club entity-link\" href=\"${esc(fromHref)}\" data-entity=\"club\" data-id=\"${esc(t.from_id)}\" data-name=\"${esc(t.from)}\"><img src=\"${esc(t.from_logo)}\" alt=\"\" loading=\"lazy\"><span>${esc(t.from)}</span></a><span class=\"arrow\">→</span><a class=\"club entity-link\" href=\"${esc(toHref)}\" data-entity=\"club\" data-id=\"${esc(t.to_id)}\" data-name=\"${esc(t.to)}\"><img src=\"${esc(t.to_logo)}\" alt=\"\" loading=\"lazy\"><span>${esc(t.to)}</span></a></div>`
}'''
new_move = '''function clubSideHtml(t,side){
  const id=t[side+'_id'],name=t[side]||'Unknown',logo=t[side+'_logo']||'';
  const free=!!t[side+'_free_agent']||(!id&&kind(t)==='free'&&name==='Free agent');
  if(free)return `<div class=\"club free-agent-side\"><span class=\"free-agent-icon\">FA</span><span>Free agent</span></div>`;
  if(!id)return `<div class=\"club static-club\"><span class=\"club-fallback\">FC</span><span>${esc(name)}</span></div>`;
  const href=entityHref('club',id);
  return `<a class=\"club entity-link\" href=\"${esc(href)}\" data-entity=\"club\" data-id=\"${esc(id)}\" data-name=\"${esc(name)}\">${logo?`<img src=\"${esc(logo)}\" alt=\"\" loading=\"lazy\">`:'<span class=\"club-fallback\">FC</span>'}<span>${esc(name)}</span></a>`
}
function moveHtml(t){return `<div class=\"move\">${clubSideHtml(t,'from')}<span class=\"arrow\">→</span>${clubSideHtml(t,'to')}</div>`}'''
rep(old_move, new_move, 'free-agent move renderer')

hub_helpers = r'''
const HUBS={
  radar:{title:'FM Radar',eyebrow:'FM Scouting Hub',icon:'✦',desc:'Young-player moves worth scouting in Football Manager.'},
  u21:{title:'U21 Transfer Hub',eyebrow:'Young Player Hub',icon:'21',desc:'Every tracked move involving a player aged 21 or under.'},
  u23:{title:'U23 Transfer Hub',eyebrow:'Young Player Hub',icon:'23',desc:'A broader view of the under-23 transfer market.'},
  freeu23:{title:'Free U23 Hub',eyebrow:'Recruitment Hub',icon:'FA',desc:'Young players moving on free transfers.'},
  balkan:{title:'Balkan Transfer Hub',eyebrow:'Regional Hub',icon:'B',desc:'Transfer activity touching Croatia, Serbia, Greece or Turkey.'},
  southamerica:{title:'South America Hub',eyebrow:'Regional Hub',icon:'SA',desc:'Tracked transfer activity across our South American leagues.'},
  mls:{title:'MLS Moves',eyebrow:'League Hub',icon:'MLS',desc:'Transfers involving Major League Soccer.'},
  watchlist:{title:'My Watchlist',eyebrow:'Personal Transfer Hub',icon:'★',desc:'Your saved clubs, players, leagues and nations in one place.'}
};
function hubRows(mode,list){
  let a=[...(list||[])];
  if(mode==='radar'||mode==='u21')a=a.filter(t=>age(t)!==null&&age(t)<=21);
  if(mode==='u23')a=a.filter(t=>age(t)!==null&&age(t)<=23);
  if(mode==='freeu23')a=a.filter(t=>age(t)!==null&&age(t)<=23&&kind(t)==='free');
  if(mode==='balkan')a=a.filter(t=>[t.country,t.from_country,t.to_country].some(c=>BALKAN.has(c)));
  if(mode==='southamerica')a=a.filter(t=>[t.country,t.from_country,t.to_country].some(c=>SAM.has(c)));
  if(mode==='mls')a=a.filter(t=>t.league==='Major League Soccer'||t.from_league==='Major League Soccer'||t.to_league==='Major League Soccer');
  if(mode==='watchlist')a=a.filter(matchesWatch);
  if(mode==='radar')a.sort((x,y)=>(age(x)-age(y))||((y.date||'').localeCompare(x.date||'')));
  else a.sort((x,y)=>(y.date||'').localeCompare(x.date||'')||(y.first_seen_at||'').localeCompare(x.first_seen_at||''));
  return a;
}
function hubHref(mode){try{const u=cleanUrl();u.searchParams.set('hub',mode);u.hash='fmbtc-detail';return u.toString()}catch(e){return'#fmbtc-detail'}}
function hubHeader(mode,rr){
  const d=HUBS[mode]||{title:'Explore',eyebrow:'Explore Hub',icon:'◎',desc:'Explore the transfer database.'};
  const clubs=new Set(rr.flatMap(t=>[t.from_id,t.to_id]).filter(Boolean));
  const nations=new Set(rr.flatMap(t=>[t.country,t.from_country,t.to_country]).filter(Boolean));
  const free=rr.filter(t=>kind(t)==='free').length,loans=rr.filter(t=>kind(t)==='loan').length;
  const saved=mode==='watchlist'?watchItems().length:null;
  const stats=mode==='watchlist'?[[saved,'Saved items'],[rr.length,'Matching transfers'],[clubs.size,'Clubs involved'],[nations.size,'Nations'],[rr.filter(t=>age(t)!==null&&age(t)<=21).length,'U21']]:[[rr.length,'Transfers'],[clubs.size,'Clubs involved'],[nations.size,'Nations'],[free,'Free'],[loans,'Loans']];
  return `<div class=\"detail-card hub-hero\"><div class=\"breadcrumb\"><button type=\"button\" class=\"detail-back\">Transfer Centre</button><span>/</span><span>Explore</span></div><div class=\"detail-main\"><div class=\"detail-ident\"><div class=\"detail-fallback hub-icon\">${esc(d.icon)}</div><div><span class=\"detail-eyebrow\">${esc(d.eyebrow)}</span><h3>${esc(d.title)}</h3><div class=\"detail-sub\"><span>${esc(d.desc)}</span></div></div></div><div class=\"detail-actions\"><button type=\"button\" class=\"detail-copy\">Copy link</button><button type=\"button\" class=\"detail-share\">Share</button></div></div><div class=\"detail-stats\">${stats.map(([v,l])=>`<div><b>${esc(v)}</b><span>${esc(l)}</span></div>`).join('')}</div></div>`;
}
function infoCell(label,value){if(value===undefined||value===null||value==='')return'';return `<div class=\"hub-info-cell\"><span>${esc(label)}</span><b>${esc(value)}</b></div>`}
function playerStatsHtml(p){
  const stats=p?.statistics||[];
  if(!stats.length)return `<div class=\"hub-note\">Detailed current-season statistics are being enriched automatically.</div>`;
  return `<div class=\"player-stat-seasons\">${stats.slice(0,6).map(s=>{const g=s.games||{},go=s.goals||{},pa=s.passes||{},ta=s.tackles||{},ca=s.cards||{},dr=s.dribbles||{},team=s.team||{},league=s.league||{};const rating=g.rating&&Number.isFinite(Number(g.rating))?Number(g.rating).toFixed(2):'—';return `<article class=\"player-stat-card\"><div class=\"player-stat-head\">${team.logo?`<img src=\"${esc(team.logo)}\" alt=\"\">`:''}<div><b>${esc(team.name||'Season statistics')}</b><span>${esc(league.name||'')}</span></div></div><div class=\"mini-stat-grid\">${infoCell('Apps',g.appearences??g.appearances??0)}${infoCell('Minutes',g.minutes??0)}${infoCell('Rating',rating)}${infoCell('Goals',go.total??0)}${infoCell('Assists',go.assists??0)}${infoCell('Key passes',pa.key??0)}${infoCell('Tackles',ta.total??0)}${infoCell('Dribbles',dr.success??0)}${infoCell('Yellow',ca.yellow??0)}${infoCell('Red',ca.red??0)}</div></article>`}).join('')}</div>`;
}
function playerHubHtml(id){
  const p=hubData?.players?.[String(id)];
  if(!p)return `<section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>PLAYER DATA</span><h4>Player profile</h4></div></div><div class=\"hub-note\">This player profile is still being enriched.</div></section>`;
  const birth=p.birth||{},club=hubData?.clubs?.[String(p.team_id)]||{},currentClub=club.name||club.team?.name||'';
  const birthplace=[birth.place,birth.country].filter(Boolean).join(', ');
  const bio=[infoCell('Full name',p.name),infoCell('Nationality',p.nationality),infoCell('Date of birth',birth.date),infoCell('Birthplace',birthplace),infoCell('Age',p.age),infoCell('Height',p.height),infoCell('Weight',p.weight),infoCell('Position',p.position),infoCell('Shirt number',p.number),infoCell('Current club',currentClub)].join('');
  const career=p.career||[],trophies=p.trophies||[],sidelined=p.sidelined||[];
  return `<section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>PLAYER DATA</span><h4>Profile</h4></div></div><div class=\"hub-info-grid\">${bio}</div></section><section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>2026 SEASON</span><h4>Statistics</h4></div></div>${playerStatsHtml(p)}</section>${career.length?`<section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>CAREER</span><h4>Clubs & seasons</h4></div></div><div class=\"career-list\">${career.slice(0,14).map(c=>{const t=c.team||{};const seasons=Array.isArray(c.seasons)?c.seasons.join(', '):c.seasons||'';return `<div class=\"career-row\">${t.logo?`<img src=\"${esc(t.logo)}\" alt=\"\">`:''}<b>${esc(t.name||'Club')}</b><span>${esc(seasons)}</span></div>`}).join('')}</div></section>`:''}${trophies.length?`<section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>HONOURS</span><h4>Trophies</h4></div></div><div class=\"trophy-grid\">${trophies.slice(0,12).map(x=>`<div><b>${esc(x.league||'Competition')}</b><span>${esc(x.season||'')} · ${esc(x.place||'')}</span></div>`).join('')}</div></section>`:''}${sidelined.length?`<section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>AVAILABILITY</span><h4>Sidelined history</h4></div></div><div class=\"career-list\">${sidelined.slice(0,8).map(x=>`<div class=\"career-row no-logo\"><b>${esc(x.type||'Unavailable')}</b><span>${esc(x.start||'')} → ${esc(x.end||'')}</span></div>`).join('')}</div></section>`:''}`;
}
function squadPlayerCard(p){
  const href=entityHref('player',p.id);
  return `<a class=\"squad-player entity-link\" href=\"${esc(href)}\" data-entity=\"player\" data-id=\"${esc(p.id)}\" data-name=\"${esc(p.name||'Player')}\">${p.photo?`<img src=\"${esc(p.photo)}\" alt=\"\" loading=\"lazy\">`:'<span class=\"squad-face\">P</span>'}<div><b>${esc(p.name||'Player')}</b><span>${p.number!=null?'#'+esc(p.number)+' · ':''}${esc(p.age?`${p.age} yrs`:'')}</span></div></a>`;
}
function clubHubHtml(id){
  const club=hubData?.clubs?.[String(id)]||{},squad=hubData?.squads?.[String(id)]||[],team=club.team||{},venue=club.venue||{},coach=(club.coaches||[])[0]||{},stats=club.statistics||{};
  const facts=[infoCell('Founded',team.founded),infoCell('Country',team.country||club.country),infoCell('Venue',venue.name),infoCell('City',venue.city),infoCell('Capacity',venue.capacity?nf(venue.capacity):''),infoCell('Surface',venue.surface),infoCell('Manager',coach.name),infoCell('Manager nationality',coach.nationality)].join('');
  const fx=stats.fixtures||{},goals=stats.goals||{};
  const statFacts=stats&&Object.keys(stats).length?[infoCell('Form',stats.form),infoCell('Played',fx.played?.total),infoCell('Wins',fx.wins?.total),infoCell('Draws',fx.draws?.total),infoCell('Losses',fx.loses?.total),infoCell('Goals for',goals.for?.total?.total),infoCell('Goals against',goals.against?.total?.total),infoCell('Clean sheets',stats.clean_sheet?.total)].join(''):'';
  const groups=[['Goalkeeper','Goalkeepers'],['Defender','Defenders'],['Midfielder','Midfielders'],['Attacker','Attackers']];
  const squadHtml=squad.length?groups.map(([pos,label])=>{const players=squad.filter(p=>p.position===pos);if(!players.length)return'';return `<div class=\"squad-group\"><div class=\"squad-group-title\"><b>${label}</b><span>${players.length}</span></div><div class=\"squad-grid\">${players.map(squadPlayerCard).join('')}</div></div>`}).join(''):`<div class=\"hub-note\">The current squad is still being refreshed from API-Football.</div>`;
  return `${facts?`<section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>CLUB DATA</span><h4>Club information</h4></div>${coach.photo?`<img class=\"coach-photo\" src=\"${esc(coach.photo)}\" alt=\"${esc(coach.name||'Manager')}\">`:''}</div><div class=\"hub-info-grid\">${facts}</div>${statFacts?`<div class=\"hub-subtitle\">Current season</div><div class=\"hub-info-grid\">${statFacts}</div>`:'<div class=\"hub-note\">Current-season club statistics are being enriched automatically.</div>'}</section>`:''}<section class=\"hub-section squad-section\"><div class=\"hub-section-head\"><div><span>CURRENT SQUAD</span><h4>First-team squad</h4></div><strong>${squad.length}</strong></div>${squadHtml}</section>`;
}
function watchlistManagerHtml(){
  const items=watchItems();
  if(!items.length)return `<section class=\"hub-section\"><div class=\"empty small\"><b>Your Watchlist is empty.</b>Open any club, player, league or nation and press Watch.</div></section>`;
  return `<section class=\"hub-section\"><div class=\"hub-section-head\"><div><span>MANAGE WATCHLIST</span><h4>Saved items</h4></div><strong>${items.length}</strong></div><div class=\"watch-manage-grid\">${items.map(x=>`<div class=\"watch-manage-card\"><div class=\"watch-manage-ident\"><span>${x.type==='nation'?flagImg(x.id,'watch-flag'):x.logo?`<img src=\"${esc(x.logo)}\" alt=\"\">`:'★'}</span><div><b>${esc(x.label||x.id)}</b><small>${esc(x.type)}</small></div></div><button type=\"button\" class=\"watch-remove\" data-watch-key=\"${esc(watchKey(x.type,x.id))}\">Remove</button></div>`).join('')}</div></section>`;
}
function entityExtras(e){if(!e)return'';if(e.type==='club')return clubHubHtml(e.id);if(e.type==='player')return playerHubHtml(e.id);if(e.type==='hub'&&e.id==='watchlist')return watchlistManagerHtml();return''}
'''

rep(
    "function renderDetailActions(){if(!currentEntity)return;const w=$('.detail-watch');if(w)w.textContent=watched(currentEntity.type,currentEntity.id)?'★ Watching':'☆ Watch'}",
    hub_helpers + "\nfunction currentWatchId(){if(!currentEntity)return'';return currentEntity.type==='league'?`${currentEntity.country}|||${currentEntity.id}`:currentEntity.id}\nfunction renderDetailActions(){if(!currentEntity||currentEntity.type==='hub')return;const w=$('.detail-watch');if(w)w.textContent=watched(currentEntity.type,currentWatchId())?'★ Watching':'☆ Watch'}",
    'hub helpers insertion',
)

old_detail_rows = "function detailRows(){if(!currentEntity||!db)return[];const e=currentEntity;if(e.type==='club')return db.filter(t=>String(t.from_id)===String(e.id)||String(t.to_id)===String(e.id));if(e.type==='player')return db.filter(t=>String(t.player_id)===String(e.id));if(e.type==='nation')return db.filter(t=>[t.country,t.from_country,t.to_country].includes(e.id));if(e.type==='league')return db.filter(t=>(t.country===e.country&&t.league===e.id)||(t.from_country===e.country&&t.from_league===e.id)||(t.to_country===e.country&&t.to_league===e.id));return[]}"
new_detail_rows = "function detailRows(){if(!currentEntity||!db)return[];const e=currentEntity;if(e.type==='club')return db.filter(t=>String(t.from_id)===String(e.id)||String(t.to_id)===String(e.id));if(e.type==='player')return db.filter(t=>String(t.player_id)===String(e.id));if(e.type==='nation')return db.filter(t=>[t.country,t.from_country,t.to_country].includes(e.id));if(e.type==='league')return db.filter(t=>(t.country===e.country&&t.league===e.id)||(t.from_country===e.country&&t.from_league===e.id)||(t.to_country===e.country&&t.to_league===e.id));if(e.type==='hub')return hubRows(e.id,db);return[]}"
rep(old_detail_rows, new_detail_rows, 'detailRows hubs')

old_render_entity = "function renderEntityRows(){const rr=entityFilteredRows(),shown=rr.slice(0,state.limit),detail=$('.detail-view');if(detail){detail.innerHTML=entityHeader(detailRows());detail.classList.add('show');detail.style.setProperty('display','block','important');detail.removeAttribute('hidden')}root()?.classList.add('entity-active');$('.count').textContent=nf(rr.length);$('.rows').innerHTML=shown.length?shown.map(rowHtml).join(''):'<div class=\"empty\"><b>No transfers found.</b></div>';const load=$('.load'),btn=$('.loadmore');if(load)load.hidden=rr.length<=state.limit;if(btn)btn.textContent=rr.length>state.limit?`Load ${Math.min(50,rr.length-state.limit)} more transfers`:'All transfers loaded';renderDetailActions();requestFrameResize()}"
new_render_entity = "function renderEntityRows(){const rr=entityFilteredRows(),shown=rr.slice(0,state.limit),detail=$('.detail-view');if(detail){const header=currentEntity?.type==='hub'?hubHeader(currentEntity.id,detailRows()):entityHeader(detailRows());detail.innerHTML=header+entityExtras(currentEntity);detail.classList.add('show');detail.style.setProperty('display','block','important');detail.removeAttribute('hidden')}root()?.classList.add('entity-active');$('.count').textContent=nf(rr.length);$('.rows').innerHTML=shown.length?shown.map(rowHtml).join(''):'<div class=\"empty\"><b>No transfers found.</b></div>';const load=$('.load'),btn=$('.loadmore');if(load)load.hidden=rr.length<=state.limit;if(btn)btn.textContent=rr.length>state.limit?`Load ${Math.min(50,rr.length-state.limit)} more transfers`:'All transfers loaded';renderDetailActions();requestFrameResize()}"
rep(old_render_entity, new_render_entity, 'entity extras renderer')

rep(
    "    await loadFull();\n    renderEntityRows();",
    "    await loadFull();\n    if(e.type==='club'||e.type==='player'){try{await loadHub()}catch(hubErr){console.warn('FM Blog hub data unavailable:',hubErr)}}\n    renderEntityRows();",
    'load hub on entity',
)

old_close = "function closeEntity(push=true){leaveEntityView();if(push)writeUrl(null,state.mode,true);render();scrollTo($('.workspace'))}"
new_close = "function closeEntity(push=true){const wasHub=currentEntity?.type==='hub';leaveEntityView();if(wasHub){state.mode='latest';state.q='';state.nation='';state.league='';state.type='';$('.q').value='';rebuildLeague();syncDropdowns()}if(push)writeUrl(null,state.mode,true);render();scrollTo($('.workspace'))}"
rep(old_close, new_close, 'close hub')

open_hub = '''async function openHub(mode,push=true){
  if(!HUBS[mode])return setMode(mode,push);
  leaveEntityView();
  state.q='';state.nation='';state.league='';state.type='';state.mode=mode;state.limit=50;
  $('.q').value='';rebuildLeague();syncDropdowns();
  return openEntity({type:'hub',id:mode,name:HUBS[mode].title},push,hubHref(mode));
}
'''
rep(
    "function setMode(mode,push=true){leaveEntityView();",
    open_hub + "function setMode(mode,push=true){leaveEntityView();",
    'openHub insertion',
)

rep(
    "}const mode=e.target.closest('[data-mode]');if(mode){setMode(mode.dataset.mode);return}",
    "}const explore=e.target.closest('.explorebtn');if(explore){await openHub(explore.dataset.mode,true);return}const mode=e.target.closest('[data-mode]');if(mode){setMode(mode.dataset.mode);return}",
    'explore hub binding',
)

rep(
    "const wc=e.target.closest('.watch-chip');if(wc){delete watch[wc.dataset.watchKey];saveWatch();watchlistSummary();render();return}if(e.target.closest('.watch-btn')){setMode('watchlist');return}",
    "const wr=e.target.closest('.watch-remove');if(wr){delete watch[wr.dataset.watchKey];saveWatch();if(currentEntity?.type==='hub'&&currentEntity.id==='watchlist')renderEntityRows();else{watchlistSummary();render()}toast('Removed from Watchlist');return}const wc=e.target.closest('.watch-chip');if(wc){delete watch[wc.dataset.watchKey];saveWatch();watchlistSummary();render();toast('Removed from Watchlist');return}if(e.target.closest('.watch-btn')){await openHub('watchlist',true);return}",
    'watchlist manager binding',
)

rep(
    "$('.q').addEventListener('input',()=>{clearTimeout(st);if(currentEntity){leaveEntityView();writeUrl(null,state.mode,false)}state.q=$('.q').value;",
    "$('.q').addEventListener('input',()=>{clearTimeout(st);if(currentEntity){const wasHub=currentEntity.type==='hub';leaveEntityView();if(wasHub)state.mode='latest';writeUrl(null,state.mode,false)}state.q=$('.q').value;",
    'search leaves hub',
)

old_open_url = "function openFromUrl(push=false){let u;try{u=pageUrl()}catch(e){return}const club=u.searchParams.get('club'),player=u.searchParams.get('player'),league=u.searchParams.get('league'),nation=u.searchParams.get('nation'),view=u.searchParams.get('view');if(club)return openEntity({type:'club',id:club},push);if(player)return openEntity({type:'player',id:player},push);if(league&&nation)return openEntity({type:'league',id:league,country:nation},push);if(nation)return openEntity({type:'nation',id:nation},push);setMode(view||'latest',false)}"
new_open_url = "function openFromUrl(push=false){let u;try{u=pageUrl()}catch(e){return}const club=u.searchParams.get('club'),player=u.searchParams.get('player'),league=u.searchParams.get('league'),nation=u.searchParams.get('nation'),hub=u.searchParams.get('hub'),view=u.searchParams.get('view');if(club)return openEntity({type:'club',id:club},push);if(player)return openEntity({type:'player',id:player},push);if(league&&nation)return openEntity({type:'league',id:league,country:nation},push);if(nation)return openEntity({type:'nation',id:nation},push);if(hub)return openHub(hub,push);setMode(view||'latest',false)}"
rep(old_open_url, new_open_url, 'hub URL routing')

out.write_text(s, encoding='utf-8')

app = app_path.read_text(encoding='utf-8')
if 'assets/transfer-centre-v431.js' not in app:
    raise SystemExit('V4.3.1 runtime ref not found')
app = app.replace('assets/transfer-centre-v431.js', 'assets/transfer-centre-v44.js', 1)

css = r'''
<style id="fmbtc-v44-hubs">
#fmbtc .free-agent-side,#fmbtc .static-club{cursor:default}
#fmbtc .free-agent-icon,#fmbtc .club-fallback{display:inline-flex;width:27px;height:27px;align-items:center;justify-content:center;border:1px solid rgba(117,241,156,.24);border-radius:8px;background:rgba(117,241,156,.08);color:#8ff4ac;font-size:8px;font-weight:950;flex:0 0 auto}
#fmbtc .club-fallback{border-color:var(--line);background:#151c28;color:#8390a3}
#fmbtc .hub-icon{font-size:19px;color:#cfc3ff;border-color:rgba(169,146,255,.35);background:linear-gradient(145deg,rgba(169,146,255,.12),rgba(97,220,255,.06))}
#fmbtc .hub-section{margin-top:10px;border:1px solid var(--line);background:#0c1118;border-radius:16px;padding:14px}
#fmbtc .hub-section-head{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:11px}
#fmbtc .hub-section-head>div>span{display:block;color:#718096;font-size:8px;font-weight:950;letter-spacing:1px;margin-bottom:3px}
#fmbtc .hub-section h4{margin:0;font-size:16px;letter-spacing:-.35px}
#fmbtc .hub-section-head>strong{font-size:20px;color:#dce5f2}
#fmbtc .hub-info-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px}
#fmbtc .hub-info-cell{border:1px solid rgba(151,165,190,.13);background:#090d13;border-radius:10px;padding:9px;min-width:0}
#fmbtc .hub-info-cell span{display:block;color:#718096;font-size:8px;margin-bottom:3px}
#fmbtc .hub-info-cell b{display:block;font-size:10px;line-height:1.3;white-space:normal;overflow-wrap:anywhere}
#fmbtc .hub-note{border-left:2px solid var(--violet);background:rgba(169,146,255,.05);border-radius:0 9px 9px 0;padding:9px 10px;color:#8996a9;font-size:9px}
#fmbtc .hub-subtitle{margin:12px 0 7px;color:#8d9aad;font-size:9px;font-weight:900;text-transform:uppercase;letter-spacing:.7px}
#fmbtc .coach-photo{width:44px;height:44px;border-radius:10px;object-fit:cover;border:1px solid var(--line)}
#fmbtc .squad-group+.squad-group{margin-top:12px}.squad-group-title{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}.squad-group-title b{font-size:10px}.squad-group-title span{font-size:8px;color:#6f7c90}
#fmbtc .squad-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}
#fmbtc .squad-player{display:flex;align-items:center;gap:8px;min-width:0;border:1px solid rgba(151,165,190,.13);background:#090d13;border-radius:10px;padding:8px;color:#e8edf5;text-decoration:none}
#fmbtc .squad-player:hover{border-color:rgba(97,220,255,.3);background:#101720}.squad-player img,.squad-face{width:34px;height:34px;border-radius:8px;object-fit:cover;flex:0 0 auto}.squad-face{display:flex;align-items:center;justify-content:center;background:#1b2431;color:#8290a3;font-size:9px;font-weight:900}
#fmbtc .squad-player div{min-width:0}.squad-player b{display:block;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.squad-player span{display:block;color:#718096;font-size:8px;margin-top:2px}
#fmbtc .player-stat-seasons{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.player-stat-card{border:1px solid rgba(151,165,190,.13);background:#090d13;border-radius:11px;padding:10px}.player-stat-head{display:flex;align-items:center;gap:8px;margin-bottom:8px}.player-stat-head img{width:27px;height:27px;object-fit:contain}.player-stat-head b{display:block;font-size:10px}.player-stat-head span{display:block;color:#718096;font-size:8px;margin-top:2px}.mini-stat-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px}.mini-stat-grid .hub-info-cell{padding:7px}.mini-stat-grid .hub-info-cell b{font-size:9px}
#fmbtc .career-list{display:grid;gap:6px}.career-row{display:grid;grid-template-columns:26px minmax(0,1fr) auto;align-items:center;gap:8px;border:1px solid rgba(151,165,190,.12);background:#090d13;border-radius:9px;padding:7px 9px}.career-row.no-logo{grid-template-columns:minmax(0,1fr) auto}.career-row img{width:25px;height:25px;object-fit:contain}.career-row b{font-size:9px}.career-row span{font-size:8px;color:#78869a;text-align:right}
#fmbtc .trophy-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.trophy-grid>div{border:1px solid rgba(255,215,122,.13);background:rgba(255,215,122,.035);border-radius:9px;padding:9px}.trophy-grid b{display:block;font-size:9px}.trophy-grid span{display:block;color:#8c8779;font-size:8px;margin-top:3px}
#fmbtc .watch-manage-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.watch-manage-card{display:flex;align-items:center;justify-content:space-between;gap:10px;border:1px solid rgba(151,165,190,.13);background:#090d13;border-radius:10px;padding:9px}.watch-manage-ident{display:flex;align-items:center;gap:8px;min-width:0}.watch-manage-ident>span{display:flex;width:28px;height:28px;align-items:center;justify-content:center}.watch-manage-ident img{max-width:28px;max-height:28px;object-fit:contain}.watch-manage-ident b{display:block;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.watch-manage-ident small{display:block;color:#718096;font-size:7px;text-transform:uppercase;margin-top:2px}.watch-remove{border:1px solid rgba(255,117,117,.24);background:rgba(124,34,34,.11);color:#ffabab;border-radius:999px;padding:6px 8px;font-size:8px;font-weight:900}.watch-remove:hover{background:rgba(124,34,34,.25);color:#fff}
@media(max-width:920px){#fmbtc .hub-info-grid{grid-template-columns:repeat(3,minmax(0,1fr))}#fmbtc .squad-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.mini-stat-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:680px){#fmbtc .hub-section{padding:11px}.hub-info-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.squad-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.player-stat-seasons{grid-template-columns:1fr}.mini-stat-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.trophy-grid,.watch-manage-grid{grid-template-columns:1fr}.career-row{grid-template-columns:24px minmax(0,1fr);}.career-row span{grid-column:2;text-align:left}.career-row.no-logo{grid-template-columns:1fr}.career-row.no-logo span{grid-column:1}}
</style>
'''
if '</head>' not in app:
    raise SystemExit('head close not found')
app = app.replace('</head>', css + '</head>', 1)
app_path.write_text(app, encoding='utf-8')
print('Built V4.4: Explore hubs, free agents, watchlist manager, current squads and richer player/club hubs.')
