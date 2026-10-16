const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {test}=require('node:test');
const source=fs.readFileSync(path.join(__dirname,'../assets/transfer-centre-v441.js'),'utf8');
const code=source.slice(source.indexOf('function transferDataStale()'),source.indexOf('function updateReturnBanner()'));
const now=Date.parse('2026-10-16T15:00:00Z');
class Clock extends Date {static now(){return now;}}
function render(meta){
  const elements=Object.fromEntries(['updated','total','last24stat','clubs','tracked','pulse-copy','profile-coverage'].map(k=>['.'+k,{textContent:''}]));
  const context={Date:Clock,feed:{meta,stats:{total:11699,last24:20,free24:4,loans24:12,clubs_involved:2320,tracked_leagues:32,profiled_rows:10430}},cfg:{leagues:[]},$:s=>elements[s],nf:n=>Number(n||0).toLocaleString('en-GB')};
  vm.runInNewContext(code+'\nrenderHeader();',context);
  return elements;
}
test('fresh successful feed keeps live counts',()=>{
  const e=render({updated_at:'2026-10-16T14:00:00Z',live:true,api_errors_last_run:0});
  assert.equal(e['.last24stat'].textContent,'20');
  assert.equal(e['.pulse-copy'].textContent,'20 new · 4 free · 12 loans in the last 24h');
  assert.equal(e['.total'].textContent,'11,699');
});
test('restored snapshot shows saved data and original success date',()=>{
  const e=render({updated_at:'2026-09-12T18:32:10Z',last_successful_update:'2026-09-12T18:32:10Z',recovered_at:'2026-10-16T14:55:00Z',stale:true,live:false});
  assert.equal(e['.last24stat'].textContent,'—');
  assert.match(e['.updated'].textContent,/12\/09\/2026.*last successful update/);
  assert.match(e['.pulse-copy'].textContent,/Showing saved transfer data/);
  assert.equal(e['.total'].textContent,'11,699');
});
test('failure metadata overrides an apparently fresh timestamp',()=>{
  const e=render({updated_at:'2026-10-16T14:00:00Z',api_errors_last_run:540});
  assert.equal(e['.last24stat'].textContent,'—');
  assert.match(e['.pulse-copy'].textContent,/temporarily unavailable/);
});
test('successful snapshot older than 24 hours becomes stale automatically',()=>{
  const e=render({updated_at:'2026-10-15T14:59:59Z',live:true});
  assert.equal(e['.last24stat'].textContent,'—');
});
test('missing or malformed timestamp never claims fresh live data',()=>{
  for(const updated_at of [undefined,'broken']){
    const e=render({updated_at});
    assert.equal(e['.updated'].textContent,'Not updated yet');
    assert.equal(e['.last24stat'].textContent,'—');
  }
});
