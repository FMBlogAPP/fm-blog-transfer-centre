const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const h = require('../app-v8.js');
const prefs = { favourites: [], watchLater: [], watched: [] };
const normalise = videos => h.hydrate({channels:[{id:'channel',name:'Creator'}],videos}).videos;
const v = (id, title, extra = {}) => ({ id, title, channelId:'channel',publishedAt:'2026-10-20T12:00:00Z',durationSeconds:300,views:100,...extra });
const now = Date.parse('2026-10-21T12:00:00Z');

test('recent videos survive catalogue loading and their current counts win', () => {
  const old = [v('aaaaaaaaaaa','Old', {views:40}), v('bbbbbbbbbbb','Archive only')];
  const recent = [v('aaaaaaaaaaa','Updated', {views:300}), v('ccccccccccc','New upload')];
  const merged = h.mergeVideos(recent, old);
  assert.deepEqual(merged.map(x=>x.id).sort(),['aaaaaaaaaaa','bbbbbbbbbbb','ccccccccccc']);
  assert.equal(merged.find(x=>x.id==='aaaaaaaaaaa').views,300);
  assert.equal(merged.find(x=>x.id==='aaaaaaaaaaa').title,'Updated');
});
test('FM27 and Wonderkids filters intersect, independent of legacy FM27 category', () => {
  const videos=normalise([v('aaaaaaaaaaa','FM27 USA Wonderkid Watch',{category:'FM27'}),v('bbbbbbbbbbb','FM26 Wonderkids'),v('ccccccccccc','FM27 Tactics')]);
  const view={...h.defaultView(),version:'FM27',category:'Wonderkids'};
  assert.deepEqual(h.filterVideos(videos,view,prefs,now).map(x=>x.id),['aaaaaaaaaaa']);
});
test('Training and Tactics can both match the same video', () => {
  const meta=h.classify(v('aaaaaaaaaaa','Breaking down the biggest FM27 changes: Training & Tactics',{category:'FM27'}));
  assert.equal(meta.gameVersion,'FM27');
  assert.ok(meta.topics.includes('Training')); assert.ok(meta.topics.includes('Tactics'));
});
test('Other football games are excluded by default and explicitly discoverable', () => {
  const videos=normalise([v('aaaaaaaaaaa','First Look at Footy Manager'),v('bbbbbbbbbbb','Our Form Makes No Sense'),v('ccccccccccc','FM27 vs EA FC27')]);
  assert.deepEqual(h.filterVideos(videos,h.defaultView(),prefs,now).map(x=>x.id).sort(),['bbbbbbbbbbb','ccccccccccc']);
  assert.deepEqual(h.filterVideos(videos,{...h.defaultView(),version:'other'},prefs,now).map(x=>x.id),['aaaaaaaaaaa']);
});
test('Older FM excludes unknown versions, FM26 and FM27 but includes FM24', () => {
  const videos=normalise([v('aaaaaaaaaaa','FM24 Rebuild'),v('bbbbbbbbbbb','A new save'),v('ccccccccccc','FM26 Rebuild')]);
  assert.deepEqual(h.filterVideos(videos,{...h.defaultView(),version:'older'},prefs,now).map(x=>x.id),['aaaaaaaaaaa']);
});
test('compact rows hydrate metadata from their channel without duplicated video fields', () => {
  const compact={schemaVersion:1,channels:[{id:'channel',name:'Creator',avatar:'avatar'}],fields:['id','title','channelIndex','publishedAt','durationSeconds','views','views24h','category','gameVersion','topics','isFm','description'],videos:[['aaaaaaaaaaa','FM27 Wonderkid',0,'2026-10-20T12:00:00Z',75,100,20,'FM27','FM27',['Wonderkids'],true,'Text']]};
  const out=h.hydrate(compact).videos[0];
  assert.equal(out.channelName,'Creator'); assert.equal(out.channelId,'channel'); assert.equal(out.duration,'1:15');
  assert.match(out.thumbnail,/aaaaaaaaaaa\/hqdefault\.jpg$/); assert.deepEqual(out.topics,['Wonderkids']);
});
test('explicit preference operations replay without resurrecting deleted favourites', () => {
  const server={favourites:['first','second'],watchLater:['aaaaaaaaaaa'],watched:[]};
  const next=h.applyOperations(server,[{type:'favourites',id:'first',value:false},{type:'watchLater',id:'bbbbbbbbbbb',value:true},{type:'watchLater',id:'aaaaaaaaaaa',value:false}]);
  assert.deepEqual(next.favourites,['second']); assert.deepEqual(next.watchLater,['bbbbbbbbbbb']); assert.deepEqual(next.watched,[]);
  assert.deepEqual(server.favourites,['first','second']);
});
test('Watch later filters only saved videos in most recently saved order', () => {
  const videos=normalise([v('aaaaaaaaaaa','First'),v('bbbbbbbbbbb','Second'),v('ccccccccccc','Third')]);
  const mine={...prefs,watchLater:['aaaaaaaaaaa','ccccccccccc']};
  assert.deepEqual(h.filterVideos(videos,{...h.defaultView(),mode:'later'},mine,now).map(x=>x.id),['ccccccccccc','aaaaaaaaaaa']);
});
test('opening a video does not call a watched mutation', () => {
  const source=fs.readFileSync(path.join(__dirname,'../app-v8.js'),'utf8');
  const open=source.slice(source.indexOf('function openVideo('),source.indexOf('async function openRequestedVideo'));
  assert.doesNotMatch(open,/setPreference|markWatched|applyOperations/);
  assert.match(source,/data-watched/);
});
test('generated embed has every required element once and no old feed application', () => {
  const embed=fs.readFileSync(path.join(__dirname,'../blogger-embed-v8.html'),'utf8');
  for(const id of ['fmtv-app','fmtv-version','fmtv-creators-modal','fmtv-creators-list','fmtv-creators-search','fmtv-player-actions','fmtv-related','fmtv-status','fmtv-sync-status','fmtv-later-count','fmtv-pick-heading']){
    assert.equal((embed.match(new RegExp('id="'+id+'"','g'))||[]).length,1,id);
  }
  assert.doesNotMatch(embed,/ARCHIVE=.*archive\.json/);
  assert.match(embed,/v8-discovery-2026-10-21/);
});
test('duration, watched and text filters remain combinable', () => {
  const videos=normalise([v('aaaaaaaaaaa','FM27 Tactics Guide',{durationSeconds:400}),v('bbbbbbbbbbb','FM27 Tactics Guide',{durationSeconds:700})]);
  const mine={...prefs,watched:['aaaaaaaaaaa']};
  const view={...h.defaultView(),query:'tactics guide',version:'FM27',filters:{...h.defaultFilters(),duration:'under10',watched:'watched'}};
  assert.deepEqual(h.filterVideos(videos,view,mine,now).map(x=>x.id),['aaaaaaaaaaa']);
});
test('real checked-in recent uploads are not lost after catalogue hydration', () => {
  const base=path.join(__dirname,'../data');
  const recent=h.hydrate(JSON.parse(fs.readFileSync(path.join(base,'videos.json'),'utf8')));
  const catalog=h.hydrate(JSON.parse(fs.readFileSync(path.join(base,'catalog.json'),'utf8')));
  const merged=h.mergeVideos(recent.videos,catalog.videos), ids=new Set(merged.map(x=>x.id));
  for(const video of recent.videos) assert.ok(ids.has(video.id),video.title);
  assert.equal(ids.size,merged.length);
});
