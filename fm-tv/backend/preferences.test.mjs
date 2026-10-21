import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {handleFmTvPreferences} from './fmb-tv-preferences.js';
const origin='https://www.footballmanagerblog.org';
const url='https://database.footballmanagerblog.org/api/fm-tv/preferences';
const tokenA='a'.repeat(100),tokenB='b'.repeat(100);
const video='abcdefghijk',video2='lmnopqrstuv';
const channel='UC'+'a'.repeat(22);
function setup(){
 const raw=new DatabaseSync(':memory:');raw.exec(readFileSync(new URL('./migration.sql',import.meta.url),'utf8'));
 const env={DB:{prepare(sql){return{bind(...params){return{async first(){return raw.prepare(sql).get(...params) || null;}}}}}}};
 const auth={cookies(req){return new Map((req.headers.get('cookie')||'').split(';').map(x=>x.trim().split('=')));},async verifySession(cookie){if(cookie==='session-a')return{sub:'user-a'};if(cookie==='session-b')return{sub:'user-b'};throw new Error('Revoked session');},async verifyId(token){if(token===tokenA)return{sub:'user-a'};if(token===tokenB)return{sub:'user-b'};throw new Error('Invalid token');},checkCsrf(req){if(req.headers.get('x-fmb-csrf')!=='good')throw new Error('INVALID_CSRF')}};
 async function call(method='GET',body,extra={},token=tokenA){
  const headers={origin,authorization:'Bearer '+token,'x-fmb-user':token===tokenB?'user-b':'user-a',...(method==='POST'?{'content-type':'application/json','x-fmb-csrf':'good'}:{}),...extra};
  const req=new Request(url,{method,headers,...(body!==undefined?{body:typeof body==='string'?body:JSON.stringify(body)}:{})});
  const response=await handleFmTvPreferences(req,env,{},auth);
  return{status:response.status,headers:response.headers,data:response.status===204?null:await response.json()};
 }
 return{raw,env,auth,call};
}
const change=(type,id,value=true)=>({type,id,value});
test('anonymous and untrusted origins cannot read/write any preference data',async()=>{
 const{call,raw}=setup();
 assert.equal((await call('GET',undefined,{authorization:''})).status,401);
 const bad=await call('GET',undefined,{origin:'https://attacker.example'});assert.equal(bad.status,403);assert.equal(bad.headers.get('access-control-allow-origin'),null);
 assert.equal((await call('POST',{baseVersion:0,operations:[change('watched',video)]},{'x-fmb-csrf':'bad'})).status,403);
 assert.equal(raw.prepare('SELECT COUNT(*) AS n FROM fmb_tv_preferences_v1').get().n,0);
});
test('trusted CORS preflight permits only the needed methods/headers',async()=>{
 const{call}=setup();
 const good=await call('OPTIONS',undefined,{'access-control-request-method':'POST','access-control-request-headers':'content-type, authorization, x-fmb-csrf'});
 assert.equal(good.status,204);assert.equal(good.headers.get('access-control-allow-origin'),origin);assert.equal(good.headers.get('access-control-allow-credentials'),'true');
 assert.equal((await call('OPTIONS',undefined,{'access-control-request-method':'PUT'})).status,405);
 assert.equal((await call('OPTIONS',undefined,{'access-control-request-method':'POST','access-control-request-headers':'x-evil'})).status,403);
});
test('fresh accounts are empty; all persistence is scoped to token uid',async()=>{
 const{call}=setup();const a=await call();assert.equal(a.data.version,0);assert.deepEqual(a.data.watchLater,[]);
 const saved=await call('POST',{baseVersion:0,operations:[change('favourites',channel),change('watchLater',video)]});
 assert.equal(saved.status,200);assert.equal(saved.data.uid,'user-a');assert.equal(saved.data.version,1);assert.deepEqual(saved.data.watchLater,[video]);
 const b=await call('GET',undefined,{},tokenB);assert.equal(b.data.uid,'user-b');assert.equal(b.data.version,0);assert.deepEqual(b.data.watchLater,[]);
 assert.equal(saved.headers.get('cache-control'),'private, no-store, max-age=0');
});
test('stale versions return authoritative state; per-item replay preserves concurrent lists',async()=>{
 const{call}=setup();
 await call('POST',{baseVersion:0,operations:[change('watchLater',video)]});
 const conflict=await call('POST',{baseVersion:0,operations:[change('watched',video2)]});
 assert.equal(conflict.status,409);assert.equal(conflict.data.code,'VERSION_CONFLICT');assert.equal(conflict.data.version,1);assert.deepEqual(conflict.data.watchLater,[video]);
 const retry=await call('POST',{baseVersion:conflict.data.version,operations:[change('watched',video2)]});
 assert.equal(retry.status,200);assert.deepEqual(retry.data.watchLater,[video]);assert.deepEqual(retry.data.watched,[video2]);
 const deleted=await call('POST',{baseVersion:2,operations:[change('watchLater',video,false)]});
 assert.deepEqual(deleted.data.watchLater,[]);assert.deepEqual(deleted.data.watched,[video2]);
});
test('simultaneous first writes cannot silently overwrite one another',async()=>{
 const{call}=setup();const results=await Promise.all([
 call('POST',{baseVersion:0,operations:[change('watched',video)]}),
 call('POST',{baseVersion:0,operations:[change('watched',video2)]})]);
 assert.deepEqual(results.map(x=>x.status).sort(),[200,409]);assert.equal((await call()).data.version,1);
});
test('invalid IDs, overlarge bodies and malformed mutations fail before storage',async()=>{
 const{call,raw}=setup();
 for(const body of [null,{}, {baseVersion:0,operations:[]},{baseVersion:0,operations:[change('uid','user-b')]},{baseVersion:0,operations:[change('watched','bad-id')]},{baseVersion:0,operations:[change('watched',video,'yes')]},{baseVersion:0,operations:[change('progress',video,{seconds:100,duration:10})]},{uid:'user-b',baseVersion:0,operations:[change('watched',video)]}])assert.equal((await call('POST',body)).status,400);
 assert.equal((await call('POST','{')).status,400);
 assert.equal((await call('POST','x'.repeat(32769))).status,413);
 assert.equal(raw.prepare('SELECT COUNT(*) AS n FROM fmb_tv_preferences_v1').get().n,0);
});
test('lists are bounded without partial writes; watched history keeps the newest 500',async()=>{
 const{call,raw}=setup();const favourites=Array.from({length:200},(_,i)=>'UC'+String(i).padStart(22,'0'));
 const watched=Array.from({length:500},(_,i)=>String(i).padStart(11,'0'));
 raw.prepare('INSERT INTO fmb_tv_preferences_v1 VALUES (?,?,?,?)').run('user-a',1,JSON.stringify({favourites,watchLater:[],watched,progress:{}}),1);
 const full=await call('POST',{baseVersion:1,operations:[change('favourites',channel),change('watchLater',video)]});
 assert.equal(full.status,422);assert.equal(full.data.code,'LIMIT_EXCEEDED');assert.deepEqual((await call()).data.watchLater,[]);
 const history=await call('POST',{baseVersion:1,operations:[change('watched',video),change('progress',video,{seconds:12.4,duration:120})]});
 assert.equal(history.status,200);assert.equal(history.data.watched.length,500);assert.equal(history.data.watched.at(-1),video);assert(!history.data.watched.includes(watched[0]));assert.deepEqual(history.data.progress[video],{seconds:12,duration:120});
});
test('verification-service outage remains a temporary error, not forced sign-out',async()=>{
 const{env,auth}=setup();auth.verifyId=async()=>{throw Object.assign(new Error('unavailable'),{name:'FirebaseServiceUnavailableError'})};
 const r=await handleFmTvPreferences(new Request(url,{headers:{origin,authorization:'Bearer '+tokenA,'x-fmb-user':'user-a'}}),env,{},auth);
 assert.equal(r.status,503);assert.equal((await r.json()).code,'AUTH_UNAVAILABLE');
});

test('restored sessions accept custom bearer only under existing session and expected uid',async()=>{
 const{call,auth}=setup();auth.verifyId=async()=>{throw new Error('Must not call bearer validator');};
 const good=await call('GET',undefined,{cookie:'__Host-fmb_session=session-a',authorization:'Bearer '+'c'.repeat(100),'x-fmb-user':'user-a'});
 assert.equal(good.status,200);assert.equal(good.data.uid,'user-a');
});
test('account mismatch and revoked sessions fail before any D1 query or bearer fallback',async()=>{
 const{call,env,auth}=setup();let reads=0,bearerCalls=0;
 env.DB.prepare=()=>{reads++;throw new Error('Must not query another account');};
 const original=auth.verifyId;auth.verifyId=async token=>{bearerCalls++;return original(token)};
 assert.equal((await call('GET',undefined,{cookie:'__Host-fmb_session=session-a','x-fmb-user':'user-b'})).status,401);
 assert.equal((await call('POST',{baseVersion:0,operations:[change('watched',video)]},{cookie:'__Host-fmb_session=session-a','x-fmb-user':'user-b'})).data.code,'ACCOUNT_CHANGED');
 assert.equal((await call('GET',undefined,{cookie:'__Host-fmb_session=revoked'})).status,401);
 assert.equal(bearerCalls,0);assert.equal(reads,0);
 assert.equal((await call('GET',undefined,{'x-fmb-user':'user-b'})).data.code,'ACCOUNT_CHANGED');
 assert.equal(bearerCalls,1);assert.equal(reads,0);
 assert.equal((await call('OPTIONS',undefined,{'access-control-request-method':'GET','access-control-request-headers':'authorization,x-fmb-user'})).status,204);
});
