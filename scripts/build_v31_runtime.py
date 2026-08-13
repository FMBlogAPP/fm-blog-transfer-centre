#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
src_path = ROOT / "assets" / "transfer-centre-v3.js"
out_path = ROOT / "assets" / "transfer-centre-v31.js"
embed_path = ROOT / "blogger-embed.html"

src = src_path.read_text(encoding="utf-8")

needle = "function scrollTo(el){"
helper = r'''function entityHref(type,id,country=''){
  try{
    const u=cleanUrl();
    if(type==='club')u.searchParams.set('club',id);
    if(type==='player')u.searchParams.set('player',id);
    if(type==='league'){u.searchParams.set('league',id);u.searchParams.set('nation',country)}
    if(type==='nation')u.searchParams.set('nation',id);
    u.hash='fmbtc-detail';
    return u.toString();
  }catch(e){return '#fmbtc-detail'}
}
function scrollTo(el){'''
if needle not in src:
    raise SystemExit("scrollTo insertion point not found")
src = src.replace(needle, helper, 1)

move_comp_pattern = re.compile(r"function moveHtml\(t\)\{.*?\}\nfunction compHtml\(t\)\{.*?\}\nfunction rowHtml", re.S)
move_comp_repl = r'''function moveHtml(t){
  const fromHref=entityHref('club',t.from_id),toHref=entityHref('club',t.to_id);
  return `<div class="move"><a class="club entity-link" href="${esc(fromHref)}" data-entity="club" data-id="${esc(t.from_id)}" data-name="${esc(t.from)}"><img src="${esc(t.from_logo)}" alt="" loading="lazy"><span>${esc(t.from)}</span></a><span class="arrow">→</span><a class="club entity-link" href="${esc(toHref)}" data-entity="club" data-id="${esc(t.to_id)}" data-name="${esc(t.to)}"><img src="${esc(t.to_logo)}" alt="" loading="lazy"><span>${esc(t.to)}</span></a></div>`
}
function compHtml(t){
  const c=rowCountry(t),l=rowLeague(t),logo=leagueLogo(rowLeagueId(t));
  const nationHref=entityHref('nation',c),leagueHref=entityHref('league',l,c);
  return `<div class="competition"><a class="nation entity-link" href="${esc(nationHref)}" data-entity="nation" data-id="${esc(c)}">${flagImg(c)}<span>${esc(c||'-')}</span></a><a class="league entity-link" href="${esc(leagueHref)}" data-entity="league" data-country="${esc(c)}" data-id="${esc(l)}">${logo?`<img src="${logo}" alt="">`:''}<span>${esc(l||'-')}</span></a></div>`
}
function rowHtml'''
src, n = move_comp_pattern.subn(move_comp_repl, src, count=1)
if n != 1:
    raise SystemExit(f"move/competition patch failed: {n}")

row_pattern = re.compile(r"function rowHtml\(t\)\{.*?\}\nfunction render\(", re.S)
row_repl = r'''function rowHtml(t){
  const k=kind(t),bc=k==='loan'?'loan':k==='free'?'free':'';
  const playerHref=entityHref('player',t.player_id);
  const player=`<a class="player entity-link" href="${esc(playerHref)}" data-entity="player" data-id="${esc(t.player_id)}" data-name="${esc(t.player)}"><img class="face" src="${esc(t.player_photo)}" alt="" loading="lazy"><span class="txt"><b>${esc(t.player)}${newBadge(t)}</b><small>${esc(profileMeta(t))}</small></span></a>`;
  return `<div class="row ${isNew(t)?'is-new':''}">${player}${moveHtml(t)}${compHtml(t)}<div class="date">${esc(t.date)}</div><div><span class="badge ${bc}">${k==='loan'?'Loan':k==='free'?'Free':'Permanent'}</span></div></div><div class="mobile ${isNew(t)?'is-new':''}"><div class="mobile-top">${player}<span class="badge ${bc}">${k==='loan'?'Loan':k==='free'?'Free':'Permanent'}</span></div>${moveHtml(t)}<div class="mobile-bottom"><span>${esc(t.date)}</span>${compHtml(t)}</div></div>`
}
function render('''
src, n = row_pattern.subn(row_repl, src, count=1)
if n != 1:
    raise SystemExit(f"row patch failed: {n}")

open_pattern = re.compile(r"async function openEntity\(e,push=true\)\{.*?\}\nfunction closeEntity", re.S)
open_repl = r'''async function openEntity(e,push=true,fallbackHref=''){
  currentEntity=e;state.entityTab='all';
  const detail=$('.detail-view');
  if(detail){
    detail.id='fmbtc-detail';
    detail.innerHTML=`<div class="detail-card detail-loading"><div class="breadcrumb"><span>Transfer Centre</span><span>/</span><span>Loading</span></div><div class="detail-main"><div class="detail-ident"><div class="detail-fallback">…</div><div><span class="detail-eyebrow">Loading full profile</span><h3>${esc(e.name||e.id||'Transfer profile')}</h3><div class="detail-sub"><span>Loading the full transfer database…</span></div></div></div></div></div>`;
    detail.classList.add('show');
    scrollTo(detail);
  }
  try{
    await loadFull();
    renderEntityRows();
    if(push)writeUrl(e,null,true);
    scrollTo($('.detail-view'));
    return true;
  }catch(err){
    console.error('FM Blog entity navigation failed:',err);
    if(fallbackHref && fallbackHref!==location.href){location.assign(fallbackHref);return false}
    if(detail)detail.innerHTML='<div class="detail-card"><div class="empty"><b>Profile could not be loaded.</b>Please refresh the page and try again.</div></div>';
    return false;
  }
}
function closeEntity'''
src, n = open_pattern.subn(open_repl, src, count=1)
if n != 1:
    raise SystemExit(f"openEntity patch failed: {n}")

old_ent = "const ent=e.target.closest('[data-entity]');if(ent){const type=ent.dataset.entity,id=ent.dataset.id;if(!id)return;if(type==='club')openEntity({type,id,name:ent.dataset.name||''});if(type==='player')openEntity({type,id,name:ent.dataset.name||''});if(type==='nation')openEntity({type,id});if(type==='league')openEntity({type,id,country:ent.dataset.country});return}"
new_ent = "const ent=e.target.closest('[data-entity]');if(ent){const type=ent.dataset.entity,id=ent.dataset.id;if(!id)return;const href=ent.getAttribute('href')||entityHref(type,id,ent.dataset.country||'');e.preventDefault();if(type==='club')await openEntity({type,id,name:ent.dataset.name||''},true,href);if(type==='player')await openEntity({type,id,name:ent.dataset.name||''},true,href);if(type==='nation')await openEntity({type,id},true,href);if(type==='league')await openEntity({type,id,country:ent.dataset.country},true,href);return}"
if old_ent not in src:
    raise SystemExit("entity click handler not found")
src = src.replace(old_ent, new_ent, 1)

# Ensure dynamically generated action buttons never submit an outer Blogger/theme form.
src = src.replace('<button class="detail-back">', '<button type="button" class="detail-back">')
src = src.replace('<button class="detail-watch">', '<button type="button" class="detail-watch">')
src = src.replace('<button class="detail-copy">', '<button type="button" class="detail-copy">')
src = src.replace('<button class="detail-share">', '<button type="button" class="detail-share">')
src = src.replace('<button data-entity-tab=', '<button type="button" data-entity-tab=')

out_path.write_text(src, encoding="utf-8")

embed = embed_path.read_text(encoding="utf-8")
embed = embed.replace('<section class="detail-view"', '<section id="fmbtc-detail" class="detail-view"')
embed = embed.replace('#fmbtc .player,#fmbtc .club,#fmbtc .nation,#fmbtc .league{border:0;background:transparent;padding:0;color:inherit;text-align:left}', '#fmbtc .player,#fmbtc .club,#fmbtc .nation,#fmbtc .league{border:0;background:transparent;padding:0;color:inherit;text-align:left;text-decoration:none;cursor:pointer}')
embed = embed.replace('assets/transfer-centre-v3.js', 'assets/transfer-centre-v31.js')
embed_path.write_text(embed, encoding="utf-8")

print("Built V3.1 progressive entity navigation runtime and patched Blogger embed.")
