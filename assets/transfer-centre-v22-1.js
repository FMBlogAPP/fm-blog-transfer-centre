(function(){
'use strict';
const BASE='https://cdn.jsdelivr.net/gh/FMBlogAPP/fm-blog-transfer-centre@main/assets/';
const FLAG={England:'gb-eng',Scotland:'gb-sct',Spain:'es',Italy:'it',Germany:'de',France:'fr',Portugal:'pt',Netherlands:'nl',Belgium:'be',Croatia:'hr',Serbia:'rs',Turkey:'tr',Austria:'at',Switzerland:'ch',Denmark:'dk',Sweden:'se',Norway:'no',Poland:'pl',Czechia:'cz',Greece:'gr',Argentina:'ar',Brazil:'br',Colombia:'co',Uruguay:'uy',Chile:'cl',Peru:'pe',USA:'us',Mexico:'mx',Canada:'ca',Japan:'jp','South Korea':'kr',Australia:'au'};
const esc=s=>String(s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const url=(country,size='24x18')=>FLAG[country]?`https://flagcdn.com/${size}/${FLAG[country]}.png`:'';
const img=(country,cls='flag-img')=>url(country)?`<img class="${cls}" src="${url(country)}" alt="${esc(country)} flag" loading="lazy">`:'';
let timer=null;
function replaceNode(node,html){if(!node||node.dataset.realFlag==='1'||!html)return;node.outerHTML=html}
function patchFlags(){
 const root=document.getElementById('fmbtc');if(!root)return;
 root.querySelectorAll('.dd-nation .dd-item[data-value]').forEach(item=>{const c=item.dataset.value;if(!c)return;const old=item.querySelector('.dd-icon');if(old)replaceNode(old,img(c,'dd-flag'))});
 const nationButton=root.querySelector('.dd-nation .dd-button');if(nationButton){const spans=nationButton.querySelectorAll('span');const c=spans.length>1?spans[1].textContent.trim():'';if(FLAG[c]){const first=nationButton.firstElementChild;if(first&&!first.matches('img.dd-flag'))replaceNode(first,img(c,'dd-flag'))}}
 root.querySelectorAll('.dd-league .dd-item[data-value]').forEach(item=>{const v=item.dataset.value||'';const c=v.split('|||')[0];const small=item.querySelector('small');if(small&&FLAG[c]&&!small.querySelector('img'))small.innerHTML=img(c,'dd-flag')+`<span>${esc(c)}</span>`});
 root.querySelectorAll('.nationline').forEach(line=>{const b=line.querySelector('.nation-link[data-country]');if(!b)return;const c=b.dataset.country;const old=line.querySelector('.flag');if(old)replaceNode(old,img(c,'flag-img'))});
 root.querySelectorAll('.mobile').forEach(card=>{const league=card.querySelector('.bottom .league-link[data-country]');const small=card.querySelector('.top .txt small');if(!league||!small)return;const c=league.dataset.country,l=league.dataset.league;if(FLAG[c]&&!small.querySelector('img'))small.innerHTML=img(c,'mobile-flag')+`<span>${esc(c)} · ${esc(l)}</span>`});
 const detail=root.querySelector('.detail-view.show .detail-card');if(detail){
   let nation='';try{nation=new URL(location.href).searchParams.get('nation')||''}catch(e){}
   const firstRowNation=root.querySelector('.rows .nation-link[data-country]');if(!nation&&firstRowNation)nation=firstRowNation.dataset.country||'';
   if(FLAG[nation]){
     const big=detail.querySelector('.detail-flag');if(big)replaceNode(big,`<img class="detail-flag-img" src="${url(nation,'w160')}" alt="${esc(nation)} flag">`);
     const sub=detail.querySelector('.detail-sub');if(sub&&!sub.querySelector('.flag-img')){const text=sub.textContent.replace(/^\s*[^\w]*\s*/,'').trim();sub.innerHTML=img(nation,'flag-img')+`<span>${esc(text)}</span>`}
   }
 }
}
function schedule(){clearTimeout(timer);timer=setTimeout(patchFlags,25)}
function startPatcher(){patchFlags();const obs=new MutationObserver(schedule);if(document.body)obs.observe(document.body,{childList:true,subtree:true});document.addEventListener('click',schedule,true)}
function loadCore(){if(window.__fmbtcCoreLoading)return;window.__fmbtcCoreLoading=true;const s=document.createElement('script');s.src=BASE+'transfer-centre-v22.js';s.defer=true;s.onload=()=>{startPatcher();setTimeout(patchFlags,250);setTimeout(patchFlags,1000)};s.onerror=()=>console.error('FM Blog Transfer Centre core failed to load');document.head.appendChild(s)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',loadCore,{once:true});else loadCore();
})();
