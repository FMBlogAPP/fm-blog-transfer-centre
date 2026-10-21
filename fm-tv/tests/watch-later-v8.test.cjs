const test = require('node:test');
const assert = require('node:assert/strict');
const h = require('../app-v8.js');

test('Watch later includes saved other games while respecting explicit game filters', () => {
  const videos = h.hydrate({
    channels: [],
    videos: [
      { id: 'aaaaaaaaaaa', title: 'First Look at Footy Manager', publishedAt: '2026-10-20T12:00:00Z' },
      { id: 'bbbbbbbbbbb', title: 'FM27 Tactics', publishedAt: '2026-10-20T12:00:00Z' },
      { id: 'ccccccccccc', title: 'EA FC27 Career', publishedAt: '2026-10-20T12:00:00Z' }
    ]
  }).videos;
  const prefs = { favourites: [], watchLater: ['aaaaaaaaaaa', 'bbbbbbbbbbb'], watched: [] };
  const view = { ...h.defaultView(), mode: 'later' };
  const ids = extra => h.filterVideos(videos, { ...view, ...extra }, prefs, Date.parse('2026-10-21T12:00:00Z')).map(video => video.id);
  assert.deepEqual(ids({}), ['bbbbbbbbbbb', 'aaaaaaaaaaa']);
  assert.deepEqual(ids({ version: 'other' }), ['aaaaaaaaaaa']);
  assert.deepEqual(ids({ version: 'FM27' }), ['bbbbbbbbbbb']);
});
