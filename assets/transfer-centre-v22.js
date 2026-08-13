(function(){
'use strict';

const BASE='https://raw.githubusercontent.com/FMBlogAPP/fm-blog-transfer-centre/main/';
const FEED_URL=BASE+'data/feed.json';
const FULL_URL=BASE+'data/transfers.json';
const CONFIG_URL=BASE+'config.json';
const VISIT_KEY='fmbtc_last_visit_v22';
const ROOT_ID='fmbtc';

const CODES={England:'GB',Scotland:'GB',Spain:'ES',Italy:'IT',Germany:'DE',France:'FR',Portugal:'PT',Netherlands:'NL',Belgium:'BE',Croatia:'HR',Serbia:'RS',Turkey:'TR',Austria:'AT',Switzerland:'CH',Denmark:'DK',Sweden:'SE',Norway:'NO',Poland:'PL',Czechia:'CZ',Greece:'GR',Argentina:'AR',Brazil:'BR',Colombia:'CO',Uruguay:'UY',Chile:'CL',Peru:'PE',USA:'US',Mexico:'MX',Canada:'CA',Japan:'JP','South Korea':'KR',Australia:'AU'};
const subFlag=tag=>String.fromCodePoint(0x1F3F4,...[...tag].map(c=>0xE0000+c.charCodeAt(0)),0xE007F);
const SPECIAL={England:subFlag('gbeng'),Scotland:subFlag('gbsct')};
const flag=c=>{if(SPECIAL[c])return SPECIAL[c];const x=CODES[c];return x?[...x].map(ch=>String.fromCodePoint(127397+ch.charCodeAt(0))).join(''):'🌐'};
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const nf=n=>Number(n||0).toLocaleString('en-GB');
const kind=t=>/loan/i.test(t.type||'')?'loan':/free/i.test(t.type||'')?'free':'permanent';
const labelType=t=>kind(t)==='loan'?'Loan':kind(t)==='free'?'Free':'Permanent';
const parseTime=v=>{const n=Date.parse(v||'');return Number.isFinite(n)?n:0};
const within24=t=>parseTime(t.first_seen_at)>=Date.now()-86400000;
const displayCountry=l=>l.display_country||l.country||'';
const leagueLogo=id=>id?`https://media.api-sports.io/football/leagues/${id}.png`:'';

let app=null;
let config=null;
let feed=null;
let fullDb=null;
let fullPromise=null;
let previousVisit=null;
let visitNow=new Date().toISOString();
let currentView=null;
let state={q:'',nation:'',league:'',type:'',tab:'latest',limit:50,entityTab:'all'};

try{previousVisit=localStorage.getItem(VISIT_KEY)}catch(e){}

function root(){return document.getElementById(ROOT_ID)}
function $ (s,r){return (r||root())?.querySelector(s)||null}
function $$ (s,r){return [...((r||root())?.querySelectorAll(s)||[])]}

function isNewForUser(t){return !!(previousVisit&&parseTime(t.first_seen_at)>parseTime(previousVisit))}
function leagueObj(country,name){return (config?.leagues||[]).find(l=>displayCountry(l)===country&&l.name===name)||null}
function leagueId(country,name){return leagueObj(country,name)?.id||null}
function clubMeta(id,rows){
  for(const t of rows){
    if(String(t.to_id)===String(id)) return {id:t.to_id,name:t.to,logo:t.to_logo,country:t.to_country||t.country,league:t.to_league||t.league,league_id:t.to_league_id||leagueId(t.to_country||t.country,t.to_league||t.league)};
    if(String(t.from_id)===String(id)) return {id:t.from_id,name:t.from,logo:t.from_logo,country:t.from_country||t.country,league:t.from_league||t.league,league_id:t.from_league_id||leagueId(t.from_country||t.country,t.from_league||t.league)};
  }
  return {id,name:'Club',logo:'',country:'',league:'',league_id:null};
}
function rowCountry(t){return t.country||t.to_country||t.from_country||''}
function rowLeague(t){return t.league||t.to_league||t.from_league||''}
function rowLeagueId(t){return t.league_id||leagueId(rowCountry(t),rowLeague(t))}

function boot(){
  const r=root();
  if(!r||r.dataset.fmbtcReady==='1')return;
  r.dataset.fmbtcReady='1';
  app=r;
  bindDocumentEvents();
  Promise.all([
    fetch(FEED_URL+'?v='+Date.now()).then(x=>{if(!x.ok)throw new Error('feed');return x.json()}),
    fetch(CONFIG_URL+'?v='+Date.now()).then(x=>{if(!x.ok)throw new Error('config');return x.json()})
  ]).then(([f,c])=>{
    if(root()!==r){r.dataset.fmbtcReady='0';return boot()}
    feed=f;config=c;
    updateTopStats();
    buildQuickFilters();
    buildDropdowns();
    render();
    showReturnBanner();
    openFromUrl();
    setTimeout(()=>{try{localStorage.setItem(VISIT_KEY,visitNow)}catch(e){}},1500);
  }).catch(err=>{
    console.error('FM Blog Transfer Centre:',err);
    const rows=$('.rows');if(rows)rows.innerHTML='<div class="empty"><b>Live transfer data could not be loaded.</b>Please refresh the page in a moment.</div>';
  });
}

function watchForBloggerRewrite(){
  let last=root();
  const obs=new MutationObserver(()=>{
    const now=root();
    if(now&&now!==last){last=now;setTimeout(boot,60)}
  });
  if(document.body)obs.observe(document.body,{childList:true,subtree:true});
}

function loadFull(){
  if(fullDb)return Promise.resolve(fullDb);
  if(fullPromise)return fullPromise;
  const dbState=$('.db-state');if(dbState)dbState.textContent='Loading full database…';
  fullPromise=fetch(FULL_URL+'?v='+(feed?.meta?.updated_at||Date.now())).then(x=>{if(!x.ok)throw new Error('full');return x.json()}).then(d=>{
    fullDb=(d.transfers||[]).filter(x=>!x.demo);
    if(dbState)dbState.textContent='Full database';
    showReturnBanner();
    return fullDb;
  }).catch(e=>{fullPromise=null;if(dbState)dbState.textContent='Fast feed';throw e});
  return fullPromise;
}
function currentRows(){return fullDb||(feed?.transfers||[])}

function updateTopStats(){
  const s=feed?.stats||{};
  const updated=$('.updated');if(updated)updated.textContent=feed?.meta?.updated_at?new Date(feed.meta.updated_at).toLocaleString('en-GB'):'Not updated yet';
  if($('.total'))$('.total').textContent=nf(s.total);
  if($('.last24stat'))$('.last24stat').textContent=nf(s.last24);
  if($('.clubs'))$('.clubs').textContent=nf(s.clubs_involved);
  if($('.tracked'))$('.tracked').textContent=nf(s.tracked_leagues||config?.leagues?.length);
  if($('.pulse-copy'))$('.pulse-copy').textContent=`${nf(s.last24)} new · ${nf(s.free24)} free transfers · ${nf(s.loans24)} loans in the last 24 hours`;
}

function showReturnBanner(){
  const b=$('.return-banner');if(!b)return;
  if(!previousVisit){b.classList.remove('show');return}
  const age=Date.now()-parseTime(previousVisit);if(age<=0||age>7*86400000){b.classList.remove('show');return}
  const count=currentRows().filter(isNewForUser).length;
  if(!count){b.classList.remove('show');return}
  $('.return-copy').textContent=`${nf(count)} new transfer${count===1?'':'s'} since your last visit`;
  b.classList.add('show');
}

const QUICK=[['England','Premier League','Premier League'],['Spain','La Liga','La Liga'],['Italy','Serie A','Serie A'],['Germany','Bundesliga','Bundesliga'],['France','Ligue 1','Ligue 1'],['Croatia','HNL','HNL'],['Brazil','Serie A','Brazil'],['Argentina','Liga Profesional','Argentina']];
function buildQuickFilters(){
  const el=$('.quick');if(!el)return;
  el.innerHTML=QUICK.map(([country,league,label])=>{
    const l=leagueObj(country,league),logo=leagueLogo(l?.id);
    return `<button class="quickbtn" data-country="${esc(country)}" data-league="${esc(league)}" type="button">${logo?`<img src="${esc(logo)}" alt="">`:''}<span>${esc(label)}</span></button>`;
  }).join('');
}

function buildDropdowns(){
  const nations=[...new Set((config?.leagues||[]).map(displayCountry).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
  const nationMenu=$('.dd-nation .dd-menu');
  if(nationMenu)nationMenu.innerHTML=`<button class="dd-item" data-value="" type="button"><span class="dd-icon">🌍</span><span>All nations</span></button>`+nations.map(n=>`<button class="dd-item" data-value="${esc(n)}" type="button"><span class="dd-icon">${flag(n)}</span><span>${esc(n)}</span></button>`).join('');
  rebuildLeagueMenu();
  const typeMenu=$('.dd-type .dd-menu');
  if(typeMenu)typeMenu.innerHTML=[['','All transfer types','↔'],['permanent','Permanent','✓'],['free','Free transfers','FREE'],['loan','Loans','L']].map(([v,l,i])=>`<button class="dd-item" data-value="${v}" type="button"><span class="dd-icon small">${i}</span><span>${l}</span></button>`).join('');
  syncDropdownLabels();
}
function rebuildLeagueMenu(){
  const menu=$('.dd-league .dd-menu');if(!menu)return;
  const leagues=(config?.leagues||[]).filter(l=>!state.nation||displayCountry(l)===state.nation).sort((a,b)=>displayCountry(a).localeCompare(displayCountry(b))||a.name.localeCompare(b.name));
  menu.innerHTML=`<button class="dd-item" data-value="" type="button"><span class="dd-icon">🏆</span><span>All leagues</span></button>`+leagues.map(l=>{
    const c=displayCountry(l),logo=leagueLogo(l.id),value=c+'|||'+l.name;
    return `<button class="dd-item" data-value="${esc(value)}" type="button">${logo?`<img class="dd-logo" src="${esc(logo)}" alt="">`:`<span class="dd-icon">${flag(c)}</span>`}<span><b>${esc(l.name)}</b>${state.nation?'':`<small>${flag(c)} ${esc(c)}</small>`}</span></button>`;
  }).join('');
}
function syncDropdownLabels(){
  const nb=$('.dd-nation .dd-button');
  if(nb)nb.innerHTML=state.nation?`<span>${flag(state.nation)}</span><span>${esc(state.nation)}</span><i>⌄</i>`:`<span>🌍</span><span>All nations</span><i>⌄</i>`;
  const lb=$('.dd-league .dd-button');
  if(lb){
    if(state.league){const [c,n]=state.league.split('|||'),l=leagueObj(c,n),logo=leagueLogo(l?.id);lb.innerHTML=`${logo?`<img src="${esc(logo)}" alt="">`:`<span>${flag(c)}</span>`}<span>${esc(n)}</span><i>⌄</i>`}
    else lb.innerHTML='<span>🏆</span><span>All leagues</span><i>⌄</i>';
  }
  const tb=$('.dd-type .dd-button');
  if(tb){const labels={permanent:'Permanent',free:'Free transfers',loan:'Loans'};tb.innerHTML=`<span>↔</span><span>${labels[state.type]||'All transfer types'}</span><i>⌄</i>`}
  $$('.quickbtn').forEach(b=>b.classList.toggle('on',state.league===`${b.dataset.country}|||${b.dataset.league}`));
  updateFilterCount();
}
function updateFilterCount(){
  const n=(state.nation?1:0)+(state.league?1:0)+(state.type?1:0)+(state.q?1:0);
  const el=$('.filter-count');if(el)el.textContent=n;
}
function closeDropdowns(except){$$('.dd.open').forEach(x=>{if(x!==except)x.classList.remove('open')})}

function applyFilters(rows){
  let a=[...rows];
  const q=state.q.trim().toLowerCase();
  if(q)a=a.filter(t=>[t.player,t.from,t.to,t.country,t.league,t.from_country,t.to_country,t.from_league,t.to_league].some(x=>(x||'').toLowerCase().includes(q)));
  if(state.nation)a=a.filter(t=>t.country===state.nation||t.from_country===state.nation||t.to_country===state.nation);
  if(state.league){const [c,n]=state.league.split('|||');a=a.filter(t=>(t.country===c&&t.league===n)||(t.from_country===c&&t.from_league===n)||(t.to_country===c&&t.to_league===n))}
  if(state.type)a=a.filter(t=>kind(t)===state.type);
  if(state.tab==='new')a=a.filter(isNewForUser);
  if(state.tab==='last24')a=a.filter(within24);
  if(state.tab==='free')a=a.filter(t=>kind(t)==='free');
  if(state.tab==='loan')a=a.filter(t=>kind(t)==='loan');
  a.sort((x,y)=>(y.date||'').localeCompare(x.date||'')||(y.first_seen_at||'').localeCompare(x.first_seen_at||'')||(y.id||'').localeCompare(x.id||''));
  return a;
}

function newBadge(t){return isNewForUser(t)?'<span class="newbadge">NEW</span>':''}
function competitionHtml(t){
  const country=rowCountry(t),league=rowLeague(t),lid=rowLeagueId(t),logo=leagueLogo(lid);
  return `<div class="competition"><div class="nationline"><span class="flag">${flag(country)}</span><button class="entity-link nation-link" data-country="${esc(country)}" type="button">${esc(country||'-')}</button></div><div class="leagueline">${logo?`<img class="league-logo" src="${esc(logo)}" alt="${esc(league)} logo" loading="lazy">`:''}<button class="entity-link league-link" data-country="${esc(country)}" data-league="${esc(league)}" type="button">${esc(league||'Unassigned league')}</button></div></div>`;
}
function moveHtml(t){
  return `<div class="move"><button class="club entity-link club-link" data-club-id="${esc(t.from_id)}" data-club="${esc(t.from)}" type="button"><img src="${esc(t.from_logo)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'"><span>${esc(t.from)}</span></button><div class="arrow">→</div><button class="club entity-link club-link" data-club-id="${esc(t.to_id)}" data-club="${esc(t.to)}" type="button"><img src="${esc(t.to_logo)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'"><span>${esc(t.to)}</span></button></div>`;
}
function rowHtml(t){
  const k=kind(t),bc=k==='loan'?'loan':k==='free'?'free':'';
  return `<div class="row"><div class="player"><img class="face" src="${esc(t.player_photo)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'"><div class="txt"><b>${esc(t.player)} ${newBadge(t)}</b><small>${esc(t.position||'Player')}</small></div></div>${moveHtml(t)}${competitionHtml(t)}<div class="date">${esc(t.date)}</div><div class="typec"><span class="badge ${bc}">${labelType(t)}</span></div></div><div class="mobile"><div class="top"><div class="player"><img class="face" src="${esc(t.player_photo)}" alt="" loading="lazy"><div class="txt"><b>${esc(t.player)} ${newBadge(t)}</b><small>${flag(rowCountry(t))} ${esc(rowCountry(t))} · ${esc(rowLeague(t))}</small></div></div><span class="badge ${bc}">${labelType(t)}</span></div>${moveHtml(t)}<div class="bottom"><span>${esc(t.date)}</span><button class="entity-link league-link" data-country="${esc(rowCountry(t))}" data-league="${esc(rowLeague(t))}" type="button">${esc(rowLeague(t))}</button></div></div>`;
}

function render(){
  if(currentView)return renderEntity();
  const rows=applyFilters(currentRows());
  const count=$('.count');if(count)count.textContent=nf(rows.length);
  const body=$('.rows');if(!body)return;
  if(state.tab==='new'&&!previousVisit){body.innerHTML='<div class="empty"><b>No previous visit stored yet.</b>Come back after the next update and this tab will show only what is new for you.</div>'}
  else body.innerHTML=rows.length?rows.slice(0,state.limit).map(rowHtml).join(''):'<div class="empty"><b>No matching transfers.</b>Try another filter or clear your current selection.</div>';
  const load=$('.load');if(load){load.hidden=fullDb?rows.length<=state.limit:false;const btn=$('.loadmore');if(btn)btn.textContent=!fullDb&&state.limit>=rows.length?'Search full database':'Load more'}
  const dbs=$('.db-state');if(dbs)dbs.textContent=fullDb?'Full database':'Fast feed';
}

function resetFilters(){state={...state,q:'',nation:'',league:'',type:'',tab:'latest',limit:50};const q=$('.q');if(q)q.value='';$$('.tab').forEach(b=>b.classList.toggle('on',b.dataset.tab==='latest'));rebuildLeagueMenu();syncDropdownLabels();render()}

function detailRows(view){
  const rows=fullDb||[];
  if(view.type==='club')return rows.filter(t=>String(t.from_id)===String(view.id)||String(t.to_id)===String(view.id));
  if(view.type==='league')return rows.filter(t=>(t.country===view.country&&t.league===view.league)||(t.from_country===view.country&&t.from_league===view.league)||(t.to_country===view.country&&t.to_league===view.league));
  return rows.filter(t=>t.country===view.country||t.from_country===view.country||t.to_country===view.country);
}
function entityHeader(view,rows){
  let icon,title,eyebrow,sub,stats;
  if(view.type==='club'){
    const m=clubMeta(view.id,rows);title=view.name||m.name;eyebrow='Club Transfer Centre';
    icon=m.logo?`<img class="detail-logo" src="${esc(m.logo)}" alt="${esc(title)} logo">`:'<div class="detail-flag">⚽</div>';
    const ll=leagueLogo(m.league_id||leagueId(m.country,m.league));
    sub=`<span>${flag(m.country)} ${esc(m.country||'')}</span>${m.league?`<span class="sep">·</span>${ll?`<img class="mini-league" src="${esc(ll)}" alt="">`:''}<span>${esc(m.league)}</span>`:''}`;
    stats=[[rows.length,'Transfers'],[rows.filter(t=>String(t.to_id)===String(view.id)).length,'Incoming'],[rows.filter(t=>String(t.from_id)===String(view.id)).length,'Outgoing'],[rows.filter(t=>kind(t)==='loan').length,'Loans']];
  }else if(view.type==='league'){
    const l=leagueObj(view.country,view.league),logo=leagueLogo(l?.id);title=view.league;eyebrow='League Transfer Centre';icon=logo?`<img class="detail-logo" src="${esc(logo)}" alt="${esc(title)} logo">`:`<div class="detail-flag">${flag(view.country)}</div>`;sub=`<span>${flag(view.country)} ${esc(view.country)}</span>`;const clubs=new Set(rows.flatMap(t=>[t.from_id,t.to_id]).filter(Boolean));stats=[[rows.length,'Transfers'],[clubs.size,'Clubs involved'],[rows.filter(t=>kind(t)==='loan').length,'Loans'],[rows.filter(t=>kind(t)==='free').length,'Free']];
  }else{
    title=view.country;eyebrow='Nation Transfer Centre';icon=`<div class="detail-flag">${flag(view.country)}</div>`;const leagues=new Set((config?.leagues||[]).filter(l=>displayCountry(l)===view.country).map(l=>l.name));sub=`<span>${nf(leagues.size)} tracked league${leagues.size===1?'':'s'}</span>`;const clubs=new Set(rows.flatMap(t=>[t.from_id,t.to_id]).filter(Boolean));stats=[[rows.length,'Transfers'],[clubs.size,'Clubs involved'],[rows.filter(t=>kind(t)==='loan').length,'Loans'],[rows.filter(t=>kind(t)==='free').length,'Free']];
  }
  return `<div class="detail-card"><div class="detail-top"><div class="detail-ident">${icon}<div><div class="detail-eyebrow">${eyebrow}</div><h3>${esc(title)}</h3><div class="detail-sub">${sub}</div></div></div><button class="detail-back" type="button">← All transfers</button></div><div class="detail-stats">${stats.map(([n,l])=>`<div><b>${nf(n)}</b><span>${l}</span></div>`).join('')}</div>${view.type==='club'?`<div class="entity-tabs"><button data-entity-tab="all" class="on">All</button><button data-entity-tab="in">Incoming</button><button data-entity-tab="out">Outgoing</button><button data-entity-tab="loan">Loans</button><button data-entity-tab="free">Free</button></div>`:''}</div>`;
}
function renderEntity(){
  let rows=detailRows(currentView);
  const header=$('.detail-view');if(header){header.classList.add('show');header.innerHTML=entityHeader(currentView,rows)}
  if(currentView.type==='club'){
    if(state.entityTab==='in')rows=rows.filter(t=>String(t.to_id)===String(currentView.id));
    if(state.entityTab==='out')rows=rows.filter(t=>String(t.from_id)===String(currentView.id));
    if(state.entityTab==='loan')rows=rows.filter(t=>kind(t)==='loan');
    if(state.entityTab==='free')rows=rows.filter(t=>kind(t)==='free');
    $$('.entity-tabs button').forEach(b=>b.classList.toggle('on',b.dataset.entityTab===state.entityTab));
  }
  rows.sort((a,b)=>(b.date||'').localeCompare(a.date||''));
  const body=$('.rows');if(body)body.innerHTML=rows.length?rows.map(rowHtml).join(''):'<div class="empty"><b>No transfers found.</b></div>';
  if($('.count'))$('.count').textContent=nf(rows.length);
  if($('.load'))$('.load').hidden=true;
  if($('.db-state'))$('.db-state').textContent='Full database · Detail view';
}
function scrollToDetail(){const el=$('.detail-view');if(!el)return;requestAnimationFrame(()=>el.scrollIntoView({behavior:'smooth',block:'start'}))}
function updateUrl(view,replace=false){
  try{const u=new URL(location.href);['club','clubName','league','nation'].forEach(k=>u.searchParams.delete(k));if(view?.type==='club'){u.searchParams.set('club',view.id);if(view.name)u.searchParams.set('clubName',view.name)}else if(view?.type==='league'){u.searchParams.set('nation',view.country);u.searchParams.set('league',view.league)}else if(view?.type==='nation')u.searchParams.set('nation',view.country);history[replace?'replaceState':'pushState']({fmbtc:view},'',u)}catch(e){}
}
async function openEntity(view,push=true){
  await loadFull();currentView=view;state.entityTab='all';renderEntity();if(push)updateUrl(view);scrollToDetail();
}
function closeEntity(push=true){
  currentView=null;state.entityTab='all';const d=$('.detail-view');if(d){d.classList.remove('show');d.innerHTML=''}if(push)updateUrl(null);render();const controls=$('.controls-shell');if(controls)requestAnimationFrame(()=>controls.scrollIntoView({behavior:'smooth',block:'start'}));
}
async function openFromUrl(){
  try{const p=new URL(location.href).searchParams;const club=p.get('club'),league=p.get('league'),nation=p.get('nation');if(club)return openEntity({type:'club',id:club,name:p.get('clubName')||''},false);if(league&&nation)return openEntity({type:'league',country:nation,league},false);if(nation)return openEntity({type:'nation',country:nation},false)}catch(e){}
}

let bound=false;
function bindDocumentEvents(){
  if(bound)return;bound=true;
  document.addEventListener('click',async e=>{
    const r=root();if(!r||!r.contains(e.target))return;
    const ddBtn=e.target.closest('.dd-button');if(ddBtn){const dd=ddBtn.closest('.dd');const open=!dd.classList.contains('open');closeDropdowns(dd);dd.classList.toggle('open',open);return}
    const item=e.target.closest('.dd-item');if(item){const dd=item.closest('.dd'),v=item.dataset.value||'';if(dd.classList.contains('dd-nation')){state.nation=v;if(state.league&&!state.league.startsWith(v+'|||'))state.league='';rebuildLeagueMenu()}else if(dd.classList.contains('dd-league'))state.league=v;else if(dd.classList.contains('dd-type'))state.type=v;dd.classList.remove('open');state.limit=50;syncDropdownLabels();await loadFull();render();return}
    closeDropdowns();
    const club=e.target.closest('.club-link');if(club){e.preventDefault();return openEntity({type:'club',id:club.dataset.clubId,name:club.dataset.club})}
    const league=e.target.closest('.league-link');if(league){e.preventDefault();return openEntity({type:'league',country:league.dataset.country,league:league.dataset.league})}
    const nation=e.target.closest('.nation-link');if(nation){e.preventDefault();return openEntity({type:'nation',country:nation.dataset.country})}
    const quick=e.target.closest('.quickbtn');if(quick){state.nation=quick.dataset.country;state.league=quick.dataset.country+'|||'+quick.dataset.league;state.limit=50;rebuildLeagueMenu();syncDropdownLabels();await loadFull();render();return}
    const tab=e.target.closest('.tab');if(tab){state.tab=tab.dataset.tab;state.limit=50;if(state.tab!=='latest')await loadFull();$$('.tab').forEach(x=>x.classList.toggle('on',x===tab));render();return}
    if(e.target.closest('.clear')){resetFilters();return}
    if(e.target.closest('.show-new')){state.tab='new';state.limit=50;await loadFull();$$('.tab').forEach(x=>x.classList.toggle('on',x.dataset.tab==='new'));render();return}
    if(e.target.closest('.filter-toggle')){r.classList.toggle('filters-open');return}
    if(e.target.closest('.loadmore')){if(!fullDb)await loadFull();state.limit+=50;render();return}
    if(e.target.closest('.detail-back')){closeEntity();return}
    const et=e.target.closest('[data-entity-tab]');if(et){state.entityTab=et.dataset.entityTab;renderEntity();scrollToDetail();return}
  },true);
  document.addEventListener('input',e=>{
    const r=root();if(!r||!r.contains(e.target)||!e.target.matches('.q'))return;state.q=e.target.value;state.limit=50;clearTimeout(window.__fmbtcSearchTimer);window.__fmbtcSearchTimer=setTimeout(async()=>{if(state.q.trim())await loadFull();syncDropdownLabels();render()},180)
  });
  window.addEventListener('popstate',()=>{currentView=null;const d=$('.detail-view');if(d){d.classList.remove('show');d.innerHTML=''}openFromUrl().then(()=>{if(!currentView)render()})});
}

function start(){boot();watchForBloggerRewrite();setTimeout(boot,250);setTimeout(boot,900)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
