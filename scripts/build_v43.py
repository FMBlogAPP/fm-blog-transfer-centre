from pathlib import Path

src = Path('assets/transfer-centre-v42.js')
out = Path('assets/transfer-centre-v43.js')
app_path = Path('transfer-centre-app-v4.html')

s = src.read_text(encoding='utf-8')

# Richer player display names from the profile-enriched transfer feed.
old = "const age=t=>{const n=Number(t.age);return Number.isFinite(n)&&n>0?n:null};\nconst flagUrl="
new = "const age=t=>{const n=Number(t.age);return Number.isFinite(n)&&n>0?n:null};\nconst displayPlayer=t=>String(t?.player_full_name||t?.player||'Unknown player');\nconst flagUrl="
if old not in s:
    raise SystemExit('displayPlayer insertion point not found')
s = s.replace(old, new, 1)

# Use vector flags for the large nation profile instead of stretching 24x18 PNGs.
old = "const flagImg=(c,cls='flag-img')=>flagUrl(c)?`<img class=\"${cls}\" src=\"${flagUrl(c)}\" alt=\"${esc(c)} flag\" loading=\"lazy\">`:'';"
new = "const flagSvg=c=>FLAG[c]?`https://flagcdn.com/${FLAG[c]}.svg`:'';\nconst flagImg=(c,cls='flag-img',large=false)=>{const u=large?flagSvg(c):flagUrl(c);return u?`<img class=\"${cls}\" src=\"${u}\" alt=\"${esc(c)} flag\" loading=\"lazy\">`:''};"
if old not in s:
    raise SystemExit('flagImg pattern not found')
s = s.replace(old, new, 1)

# Search should understand both raw API labels and richer profile names.
s = s.replace("[t.player,t.from,t.to,t.country,t.league,t.from_country,t.to_country,t.position]", "[displayPlayer(t),t.player,t.from,t.to,t.country,t.league,t.from_country,t.to_country,t.position]", 1)

# Render full player display names in rows and entity links.
old = "const player=`<a class=\"player entity-link\" href=\"${esc(playerHref)}\" data-entity=\"player\" data-id=\"${esc(t.player_id)}\" data-name=\"${esc(t.player)}\"><img class=\"face\" src=\"${esc(t.player_photo)}\" alt=\"\" loading=\"lazy\"><span class=\"txt\"><b>${esc(t.player)}${newBadge(t)}</b><small>${esc(profileMeta(t))}</small></span></a>`;"
new = "const playerName=displayPlayer(t);\n  const player=`<a class=\"player entity-link\" href=\"${esc(playerHref)}\" data-entity=\"player\" data-id=\"${esc(t.player_id)}\" data-name=\"${esc(playerName)}\"><img class=\"face\" src=\"${esc(t.player_photo)}\" alt=\"\" loading=\"lazy\"><span class=\"txt\"><b>${esc(playerName)}${newBadge(t)}</b><small>${esc(profileMeta(t))}</small></span></a>`;"
if old not in s:
    raise SystemExit('row player pattern not found')
s = s.replace(old, new, 1)

s = s.replace("title=t.player||e.name||'Player'", "title=displayPlayer(t)||e.name||'Player'", 1)
s = s.replace("meta.label=t.player||meta.label", "meta.label=displayPlayer(t)||meta.label", 1)

# Large nation profile gets the SVG flag.
s = s.replace("icon=flagImg(e.id,'detail-flag');", "icon=flagImg(e.id,'detail-flag',true);", 1)

# Replace the dropdown handler: Nation/League selections are profile navigation,
# while Transfer Type remains a global filter.
start = s.index("const item=e.target.closest('.dd-item');if(item){")
end = s.index("const quick=e.target.closest('.quickbtn');", start)
new_dropdown = """const item=e.target.closest('.dd-item');if(item){
  const box=item.closest('.dd'),v=item.dataset.value||'';
  box.classList.remove('open');state.limit=50;
  if(box.classList.contains('dd-type')){
    leaveEntityView();state.type=v;syncDropdowns();writeUrl(null,state.mode,true);await loadFull();render();scrollTo($('.workspace'));return;
  }
  if(box.classList.contains('dd-nation')){
    leaveEntityView();state.nation=v;state.league='';rebuildLeague();syncDropdowns();await loadFull();
    if(v){await openEntity({type:'nation',id:v},true,entityHref('nation',v));}
    else{writeUrl(null,state.mode,true);render();scrollTo($('.workspace'));}
    return;
  }
  if(box.classList.contains('dd-league')){
    leaveEntityView();state.league=v;
    if(v){const parts=v.split('|||'),c=parts[0],l=parts.slice(1).join('|||');state.nation=c;rebuildLeague();syncDropdowns();await loadFull();await openEntity({type:'league',id:l,country:c},true,entityHref('league',l,c));}
    else{syncDropdowns();await loadFull();if(state.nation){await openEntity({type:'nation',id:state.nation},true,entityHref('nation',state.nation));}else{writeUrl(null,state.mode,true);render();scrollTo($('.workspace'));}}
    return;
  }
}"""
s = s[:start] + new_dropdown + s[end:]

# Quick Leagues now open the full League Transfer Centre instead of only filtering.
start = s.index("const quick=e.target.closest('.quickbtn');if(quick){")
end = s.index("const mode=e.target.closest('[data-mode]');", start)
new_quick = """const quick=e.target.closest('.quickbtn');if(quick){
  leaveEntityView();const c=quick.dataset.country,l=quick.dataset.league;state.nation=c;state.league=`${c}|||${l}`;state.limit=50;rebuildLeague();syncDropdowns();await loadFull();await openEntity({type:'league',id:l,country:c},true,entityHref('league',l,c));return;
}"""
s = s[:start] + new_quick + s[end:]

out.write_text(s, encoding='utf-8')

app = app_path.read_text(encoding='utf-8')
if 'assets/transfer-centre-v42.js' not in app:
    raise SystemExit('V4.2 app runtime reference not found')
app = app.replace('assets/transfer-centre-v42.js', 'assets/transfer-centre-v43.js', 1)

# Nation flags should look like flags, not square app icons. Also allow longer
# player names to wrap naturally rather than clipping them to one line.
css_patch = """
<style id="fmbtc-v43-polish">
#fmbtc .detail-flag{width:88px!important;height:60px!important;object-fit:cover!important;padding:0!important;border-radius:10px!important;background:#090d13!important}
#fmbtc .txt b{white-space:normal!important;overflow:visible!important;text-overflow:clip!important;line-height:1.18!important;flex-wrap:wrap!important}
@media(max-width:680px){#fmbtc .detail-flag{width:72px!important;height:50px!important}}
</style>
"""
app = app.replace('</head>', css_patch + '</head>', 1)
app_path.write_text(app, encoding='utf-8')
print('Built V4.3: profile navigation, vector nation flags, richer player names.')
