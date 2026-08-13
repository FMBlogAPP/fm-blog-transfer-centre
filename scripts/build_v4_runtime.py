from pathlib import Path

src_path = Path('assets/transfer-centre-v31.js')
out_path = Path('assets/transfer-centre-v4.js')
app_path = Path('transfer-centre-app-v4.html')

s = src_path.read_text(encoding='utf-8')

old = "function cleanUrl(){const u=new URL(location.href);['club','player','league','nation','view'].forEach(k=>u.searchParams.delete(k));return u}"
new = "function pageUrl(){try{if(window.parent&&window.parent!==window&&window.parent.location)return new URL(window.parent.location.href)}catch(e){}return new URL(location.href)}\nfunction cleanUrl(){const u=pageUrl();['club','player','league','nation','view'].forEach(k=>u.searchParams.delete(k));u.hash='';return u}"
if old not in s:
    raise SystemExit('cleanUrl pattern not found')
s = s.replace(old, new)

old = "history[push?'pushState':'replaceState']({fmbtc:true},'',u)"
new = "(()=>{try{const h=(window.parent&&window.parent!==window)?window.parent.history:history;h[push?'pushState':'replaceState']({fmbtc:true},'',u)}catch(x){history[push?'pushState':'replaceState']({fmbtc:true},'',u)}})()"
if old not in s:
    raise SystemExit('history pattern not found')
s = s.replace(old, new)

old = "function scrollTo(el){if(!el)return;requestAnimationFrame(()=>{const y=window.scrollY+el.getBoundingClientRect().top-78;window.scrollTo({top:Math.max(0,y),behavior:'smooth'})})}"
new = "function scrollTo(el){if(!el)return;requestAnimationFrame(()=>{try{if(window.parent&&window.parent!==window&&window.frameElement){const fr=window.frameElement.getBoundingClientRect();const y=window.parent.scrollY+fr.top+el.getBoundingClientRect().top-78;window.parent.scrollTo({top:Math.max(0,y),behavior:'smooth'});return}}catch(e){}const y=window.scrollY+el.getBoundingClientRect().top-78;window.scrollTo({top:Math.max(0,y),behavior:'smooth'})})}"
if old not in s:
    raise SystemExit('scrollTo pattern not found')
s = s.replace(old, new)

old = "copyText(location.href).then(()=>toast('Link copied'))"
new = "copyText(pageUrl().toString()).then(()=>toast('Link copied'))"
s = s.replace(old, new)

old = "navigator.share({title:document.title,url:location.href})"
new = "navigator.share({title:document.title,url:pageUrl().toString()})"
s = s.replace(old, new)

old = "function openFromUrl(push=false){let u;try{u=new URL(location.href)}catch(e){return}"
new = "function openFromUrl(push=false){let u;try{u=pageUrl()}catch(e){return}"
if old not in s:
    raise SystemExit('openFromUrl pattern not found')
s = s.replace(old, new)

old = "window.addEventListener('popstate',()=>openFromUrl(false))"
new = "window.addEventListener('popstate',()=>openFromUrl(false));try{if(window.parent&&window.parent!==window)window.parent.addEventListener('popstate',()=>openFromUrl(false))}catch(e){}"
if old not in s:
    raise SystemExit('popstate pattern not found')
s = s.replace(old, new)

out_path.write_text(s, encoding='utf-8')

app = app_path.read_text(encoding='utf-8')
app = app.replace('assets/transfer-centre-v31.js', 'assets/transfer-centre-v4.js')
app_path.write_text(app, encoding='utf-8')

print('Built frame-aware V4 runtime and updated app reference.')
