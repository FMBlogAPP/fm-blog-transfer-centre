(function () {
  'use strict';

  // The pure data helpers also run in Node's regression suite.
  var TOPICS = {
    Tactics: /\b(?:tactic\w*|formation\w*|gegenpress\w*|tiki[ -]taka)\b/i,
    Rebuilds: /\b(?:rebuild\w*|road\s+to\s+glory|rtg|takeover)\b/i,
    Wonderkids: /\b(?:wonderkid\w*|young\s+players|prospect\w*|hidden\s+gems)\b/i,
    Experiments: /\b(?:experiment\w*|simulation\w*|simulated|what\s+if|(?:100|50|20)\s+years)\b/i,
    Saves: /\b(?:episode\w*|ep\.?\s*\d+|career\w*|save\w*|journeyman|glory\s+hunter|park\s+to\s+prem|pentagon|zero\s+to\s+hero)\b/i,
    News: /\b(?:update\w*|patch\w*|feature\w*|release\w*|beta|announcement\w*|news|preview\w*)\b/i,
    Guides: /\b(?:guide\w*|tutorial\w*|how\s+to|beginner\w*|tips)\b/i,
    Training: /\b(?:training|development|developing)\b/i
  };
  function classify(video) {
    var title = String(video.title || ''), legacy = String(video.category || '');
    var version = title.match(/\b(?:fm|football\s+manager)\s*[-:]?\s*(?:20)?(\d{2})\b/i);
    var topics = Object.keys(TOPICS).filter(function (name) { return TOPICS[name].test(title); });
    if (TOPICS[legacy] && topics.indexOf(legacy) < 0) topics.push(legacy);
    var fmTitle = /\b(?:fm(?:\s*(?:20)?\d{2})?|football\s+manager)\b/i.test(title);
    var other = /\b(?:proper\s+football\s+boss|footy\s+manager|(?:ea\s+sports\s+)?fc\s*2[4-9]|fifa\s*(?:20)?\d{2}|football\s+chairman|we\s+are\s+football|soccer\s+manager|football\s+life\s*(?:20)?\d{2}|efootball|pro\s+evolution\s+soccer)\b/i.test(title);
    return { gameVersion: version ? 'FM' + version[1] : (/^FM\d{2}$/.test(legacy) ? legacy : ''), topics: topics, isFm: !(other && !fmTitle) };
  }
  function duration(seconds) {
    var n = Math.max(0, Number(seconds) || 0), h = Math.floor(n / 3600), m = Math.floor(n % 3600 / 60), s = Math.floor(n % 60);
    return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(s).padStart(2, '0');
  }
  function normaliseVideo(video, channels) {
    var c = channels.get(video.channelId) || {}, inferred = classify(video);
    return Object.assign({}, video, {
      gameVersion: video.gameVersion == null ? inferred.gameVersion : video.gameVersion,
      topics: Array.isArray(video.topics) ? video.topics : inferred.topics,
      isFm: typeof video.isFm === 'boolean' ? video.isFm : inferred.isFm,
      duration: video.duration || duration(video.durationSeconds),
      thumbnail: video.thumbnail || 'https://i.ytimg.com/vi/' + encodeURIComponent(video.id) + '/hqdefault.jpg',
      channelName: video.channelName || c.name || 'FM creator', channelAvatar: video.channelAvatar || c.avatar || '',
      channelUrl: video.channelUrl || c.channelUrl || 'https://www.youtube.com/channel/' + encodeURIComponent(video.channelId || '')
    });
  }
  function hydrate(feed) {
    if (!feed || !Array.isArray(feed.videos) || !Array.isArray(feed.channels)) throw new Error('Invalid video feed');
    var channels = new Map(feed.channels.map(function (c) { return [c.id, c]; }));
    var compact = feed.schemaVersion === 1 && Array.isArray(feed.fields);
    var videos = feed.videos.map(function (row) {
      if (!compact) return row;
      var v = {}; feed.fields.forEach(function (field, i) { v[field] = row[i]; });
      var c = feed.channels[v.channelIndex]; v.channelId = c ? c.id : ''; return v;
    }).filter(function (v) { return v && /^[A-Za-z0-9_-]{11}$/.test(v.id || ''); });
    return Object.assign({}, feed, { videos: videos.map(function (v) { return normaliseVideo(v, channels); }) });
  }
  function mergeVideos(recent, archive) {
    var map = new Map(); (archive || []).forEach(function (v) { map.set(v.id, v); });
    (recent || []).forEach(function (v) { map.set(v.id, Object.assign({}, map.get(v.id) || {}, v)); });
    return Array.from(map.values());
  }
  function defaultFilters() { return { duration: 'any', date: 'any', watched: 'all', sort: 'relevance' }; }
  function defaultView() { return { mode: 'latest', category: '', version: '', creator: '', query: '', filters: defaultFilters() }; }
  function emptyPreferences() { return { favourites: [], watchLater: [], watched: [] }; }
  function applyOperations(prefs, operations) {
    function validIds(key) { return Array.isArray(prefs[key]) ? Array.from(new Set(prefs[key].filter(function (id) { return typeof id === 'string' && /^[A-Za-z0-9_-]{1,80}$/.test(id); }))) : []; }
    var next = { favourites: validIds('favourites'), watchLater: validIds('watchLater'), watched: validIds('watched') };
    (operations || []).forEach(function (op) {
      if (!Object.prototype.hasOwnProperty.call(next, op.type)) return;
      next[op.type] = next[op.type].filter(function (id) { return id !== op.id; });
      if (op.value) next[op.type].push(op.id);
    });
    next.watched = next.watched.slice(-500); return next;
  }
  function filterVideos(videos, view, prefs, now) {
    var query = String(view.query || '').trim().toLowerCase();
    var terms = query.split(/\s+/).filter(Boolean), filters = view.filters || defaultFilters();
    var sets = { favourites: new Set(prefs.favourites || []), watchLater: new Set(prefs.watchLater || []), watched: new Set(prefs.watched || []) };
    var list = videos.filter(function (v) {
      if (view.version === 'other' ? v.isFm !== false : v.isFm === false && !(view.mode === 'later' && !view.version)) return false;
      if (view.version && view.version !== 'other' && view.version !== 'older' && v.gameVersion !== view.version) return false;
      if (view.version === 'older' && (!/^FM\d{2}$/.test(v.gameVersion || '') || Number(v.gameVersion.slice(2)) >= 26)) return false;
      if (view.creator && v.channelId !== view.creator) return false;
      if (view.category && (v.topics || []).indexOf(view.category) < 0) return false;
      if (view.mode === 'favourites' && !sets.favourites.has(v.channelId)) return false;
      if (view.mode === 'later' && !sets.watchLater.has(v.id)) return false;
      if (terms.length) {
        var text = (v.title + ' ' + v.channelName + ' ' + (v.topics || []).join(' ') + ' ' + v.gameVersion + ' ' + (v.description || '')).toLowerCase();
        if (!terms.every(function (t) { return text.indexOf(t) >= 0 || (t.length > 4 && t.endsWith('s') && text.indexOf(t.slice(0, -1)) >= 0); })) return false;
      }
      var n = Number(v.durationSeconds) || 0;
      if (filters.duration === 'under10' && n >= 600) return false;
      if (filters.duration === '10to30' && (n < 600 || n >= 1800)) return false;
      if (filters.duration === '30to60' && (n < 1800 || n >= 3600)) return false;
      if (filters.duration === 'over60' && n < 3600) return false;
      var ages = { today: 864e5, week: 6048e5, month: 2592e6, year: 31536e6 };
      if (ages[filters.date] && now - Date.parse(v.publishedAt) > ages[filters.date]) return false;
      if (filters.watched === 'watched' && !sets.watched.has(v.id)) return false;
      if (filters.watched === 'unwatched' && sets.watched.has(v.id)) return false;
      return true;
    });
    function relevance(v) { var title = v.title.toLowerCase(); return (title === query ? 120 : 0) + (title.indexOf(query) >= 0 ? 55 : 0) + terms.reduce(function (n, t) { return n + (title.indexOf(t) >= 0 ? 10 : 0); }, 0); }
    list.sort(function (a, b) {
      var tie = Date.parse(b.publishedAt) - Date.parse(a.publishedAt);
      if (view.mode === 'trending' || filters.sort === 'trending') return (b.views24h == null ? -1 : b.views24h) - (a.views24h == null ? -1 : a.views24h) || (b.trendingScore || 0) - (a.trendingScore || 0) || tie;
      if (filters.sort === 'popularity') return (b.views || 0) - (a.views || 0) || tie;
      if (query && filters.sort === 'relevance') return relevance(b) - relevance(a) || tie;
      if (view.mode === 'later' && filters.sort === 'relevance') return prefs.watchLater.indexOf(b.id) - prefs.watchLater.indexOf(a.id);
      return tie;
    }); return list;
  }
  var helpers = { classify: classify, hydrate: hydrate, mergeVideos: mergeVideos, filterVideos: filterVideos, applyOperations: applyOperations, defaultFilters: defaultFilters, defaultView: defaultView };
  if (typeof module === 'object' && module.exports) { module.exports = helpers; return; }
  var root = document.getElementById('fmtv-app'); if (!root) return;
  var $ = function (selector) { return root.querySelector(selector); };
  var DATA = 'https://raw.githubusercontent.com/FMBlogAPP/fm-blog-transfer-centre/main/fm-tv/data/';
  var API = 'https://database.footballmanagerblog.org/api/fm-tv/preferences';
  var CSRF = 'https://database.footballmanagerblog.org/api/community/csrf';
  var PICK = 'BFx05-AMBcU', CACHE_KEY = 'fmTvRecentCacheV8';
  var state = Object.assign(defaultView(), { data: null, archive: null, shown: 12, loading: false, archiveLoading: false, archiveError: false, stale: false, creatorQuery: '', currentVideo: null, draftFilters: null });
  var prefs = emptyPreferences(), account = null, accountEpoch = 0, accountVersion = null, pending = [], syncBusy = 0, syncLoadEpoch = 0, syncTimer = null, syncMessage = 'Saved in this browser only', csrfToken = '', authUnsubscribe = null;
  var activeDialog = null, dialogFocus = null, previousOverflow = '', requestedWatch = '', searchTimer = null, catalogPromise = null;
  var el = {};
  ['search','search-btn','creator-search','creator-list','mobile-creators','cats','channel-head','home-only','feature','updated','trend-note','trending-row','fav-shelf','fav-grid','fav-count','grid-title','grid-note','count','grid-a','grid-b','feed-ad','grid-section','load','filter-open','filter-count','filter-modal','filter-close','filter-apply','filter-clear','filter-summary','modal','modal-title','player','close','version','later-count','status','sync-status','creators-modal','creators-search','creators-list','creators-close','player-actions','related'].forEach(function (id) { el[id] = $('#fmtv-' + id); });
  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmt(n) { n = Number(n) || 0; return n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1).replace('.0', '') + 'M' : n >= 1e3 ? (n / 1e3).toFixed(n >= 1e5 ? 0 : 1).replace('.0', '') + 'K' : String(n); }
  function relative(date) { var seconds = Math.max(1, (Date.now() - Date.parse(date)) / 1000); if (!Number.isFinite(seconds)) return ''; if (seconds < 3600) return Math.max(1, Math.floor(seconds / 60)) + 'm ago'; if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago'; if (seconds < 2592000) return Math.floor(seconds / 86400) + 'd ago'; return Math.floor(seconds / 2592000) + 'mo ago'; }
  function localKey(uid) { return 'fmTvPrefsV8:' + (uid || 'guest'); }
  function readLocal(uid) {
    try { var v = JSON.parse(localStorage.getItem(localKey(uid)) || 'null'); if (v) return { preferences: applyOperations(v.preferences || {}, []), pending: Array.isArray(v.pending) ? v.pending.slice(-1000) : [] }; } catch (e) {}
    var initial = emptyPreferences();
    if (!uid) { try { initial.favourites = JSON.parse(localStorage.getItem('fmTvFavouriteCreatorsV1') || '[]'); } catch (e) {} }
    // V1 "watched" meant opened, so it is intentionally not migrated as watched.
    return { preferences: applyOperations(initial, []), pending: [] };
  }
  function writeLocal() { try { localStorage.setItem(localKey(account && account.uid), JSON.stringify({ preferences: prefs, pending: pending })); } catch (e) { syncMessage = 'Browser storage is unavailable'; } }
  function has(type, id) { return (prefs[type] || []).indexOf(id) >= 0; }
  function setPreference(type, id, value) {
    var limits = { favourites: 200, watchLater: 300 };
    if (value && !has(type, id) && limits[type] && prefs[type].length >= limits[type]) { syncMessage = type === 'watchLater' ? 'Watch later is full. Remove a video to save another.' : 'Your channel list is full.'; renderSync(); return; }
    var focusAttribute = type === 'favourites' ? 'data-star' : type === 'watchLater' ? 'data-later' : 'data-watched';
    var restoreActionFocus = document.activeElement && document.activeElement.getAttribute(focusAttribute) === id;
    var op = { type: type, id: id, value: value }; prefs = applyOperations(prefs, [op]);
    if (account) { pending.push(op); syncMessage = 'Saving to your account...'; }
    writeLocal(); renderAll(false); renderPlayerActions();
    if (restoreActionFocus) { var nextFocus = (activeDialog || root).querySelector('[' + focusAttribute + '="' + id + '"]'); if (nextFocus) nextFocus.focus(); }
    if (account) { clearTimeout(syncTimer); syncTimer = setTimeout(flushSync, 250); }
  }
  function renderSync() {
    if (!el['sync-status']) return;
    el['sync-status'].textContent = syncMessage;
    el['sync-status'].dataset.state = /could not|unavailable|full/i.test(syncMessage) ? 'error' : '';
    var retry = $('#fmtv-sync-retry'); if (retry) retry.hidden = !(account && /could not/.test(syncMessage));
  }
  async function syncRequest(method, body, user) {
    var headers = { Authorization: 'Bearer ' + await user.getIdToken(), 'X-FMB-User': user.uid };
    if (method === 'POST') {
      if (!csrfToken) { var c = await fetch(CSRF, { credentials: 'include' }); if (!c.ok) throw new Error('CSRF unavailable'); csrfToken = (await c.json()).csrfToken; }
      if (!csrfToken) throw new Error('CSRF unavailable');
      headers['Content-Type'] = 'application/json'; headers['X-FMB-CSRF'] = csrfToken;
    }
    var r = await fetch(API, { method: method, credentials: 'include', headers: headers, body: body ? JSON.stringify(body) : undefined });
    var data = await r.json(); if (!r.ok && !(r.status === 409 && data.code === 'VERSION_CONFLICT')) { if (r.status === 403) csrfToken = ''; throw new Error(data.code || 'Sync unavailable'); }
    if (data.uid !== user.uid || !Number.isInteger(data.version)) throw new Error('Account mismatch'); return { status: r.status, data: data };
  }
  async function loadSync(epoch) {
    var user = account, loaded = false; if (!user || syncLoadEpoch === epoch || syncBusy === epoch) return;
    syncLoadEpoch = epoch;
    try {
      var response = await syncRequest('GET', null, user); if (epoch !== accountEpoch || (accountVersion != null && response.data.version < accountVersion)) return;
      accountVersion = response.data.version; prefs = applyOperations(response.data, pending); writeLocal();
      syncMessage = pending.length ? 'Saving to your account...' : 'Synced with your FM Blog account'; renderAll(false); renderPlayerActions();
      loaded = true;
    } catch (e) { if (epoch === accountEpoch) { syncMessage = 'Saved here. Account sync could not connect.'; renderSync(); } }
    finally { if (syncLoadEpoch === epoch) syncLoadEpoch = 0; if (loaded && epoch === accountEpoch && pending.length) flushSync(); }
  }
  async function flushSync() {
    if (!account || syncBusy === accountEpoch || syncLoadEpoch === accountEpoch) return; if (accountVersion == null) { loadSync(accountEpoch); return; }
    if (!pending.length) return;
    var epoch = accountEpoch, user = account, conflicts = 0; syncBusy = epoch;
    try {
      while (pending.length && epoch === accountEpoch) {
        var batch = pending.slice(0, 100), response = await syncRequest('POST', { baseVersion: accountVersion, operations: batch }, user);
        if (epoch !== accountEpoch) return;
        accountVersion = response.data.version;
        if (response.status === 409) { if (++conflicts > 3) throw new Error('Version conflict'); }
        else { pending.splice(0, batch.length); conflicts = 0; }
        prefs = applyOperations(response.data, pending); writeLocal();
      }
      if (epoch === accountEpoch) { syncMessage = 'Synced with your FM Blog account'; renderAll(false); renderPlayerActions(); }
    } catch (e) { if (epoch === accountEpoch) { syncMessage = 'Saved here. Account sync could not connect.'; writeLocal(); renderSync(); } }
    finally { if (syncBusy === epoch) syncBusy = 0; }
  }
  function changeAccount(user) {
    var uid = user && user.uid; if ((account && account.uid) === uid && accountEpoch) return;
    accountEpoch++; account = user || null; accountVersion = null; csrfToken = ''; syncBusy = 0; clearTimeout(syncTimer);
    var saved = readLocal(uid); prefs = saved.preferences; pending = uid ? saved.pending : [];
    syncMessage = uid ? 'Connecting your FM Blog account...' : 'Saved in this browser only'; renderAll(false); renderPlayerActions();
    if (uid) loadSync(accountEpoch);
  }
  async function connectAuth() {
    var bridge = window.FMBlogAuth; if (!bridge || !bridge.auth || authUnsubscribe) return;
    changeAccount(bridge.user || null);
    try { var sdk = await import('https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js'); if (!authUnsubscribe) authUnsubscribe = sdk.onAuthStateChanged(bridge.auth, changeAccount); } catch (e) { /* Local mode remains usable if the shared auth SDK is unavailable. */ }
  }
  function channels() { var map = new Map(); ((state.archive && state.archive.channels) || []).forEach(function (c) { map.set(c.id, c); }); ((state.data && state.data.channels) || []).forEach(function (c) { map.set(c.id, Object.assign({}, map.get(c.id), c)); }); return Array.from(map.values()); }
  function channelById(id) { return channels().find(function (c) { return c.id === id; }); }
  function allVideos() { return mergeVideos((state.data && state.data.videos) || [], (state.archive && state.archive.videos) || []); }
  function findVideo(id) { return allVideos().find(function (v) { return v.id === id; }); }
  function wantsCatalog() { return !!(state.creator || state.category || state.version || state.query.trim().length >= 2 || state.mode === 'favourites' || state.mode === 'later' || filterCount()); }
  function pool() { return wantsCatalog() ? allVideos() : ((state.data && state.data.videos) || []); }
  function results() { return filterVideos(pool(), state, prefs, Date.now()); }
  function filterCount() { var f = state.filters; return Number(f.duration !== 'any') + Number(f.date !== 'any') + Number(f.watched !== 'all') + Number(f.sort !== 'relevance'); }
  function setHash() {
    var p = new URLSearchParams(); ['creator','category','version','query'].forEach(function (key) { if (state[key]) p.set(key === 'query' ? 'q' : key, state[key]); });
    if (state.mode !== 'latest') p.set('mode', state.mode);
    Object.keys(defaultFilters()).forEach(function (k) { if (state.filters[k] !== defaultFilters()[k]) p.set(k, state.filters[k]); });
    if (state.currentVideo) p.set('watch', state.currentVideo.id);
    var hash = p.toString(); if (location.hash !== (hash ? '#' + hash : '')) history.replaceState(null, '', location.pathname + location.search + (hash ? '#' + hash : ''));
  }
  function readHash() {
    var p = new URLSearchParams(location.hash.slice(1)), view = defaultView();
    view.creator = p.get('creator') || ''; view.query = p.get('q') || '';
    if (TOPICS[p.get('category')]) view.category = p.get('category');
    var oldCategory = p.get('category'); view.version = ['FM27','FM26','older','other'].indexOf(p.get('version')) >= 0 ? p.get('version') : (/^FM\d{2}$/.test(oldCategory || '') ? (Number(oldCategory.slice(2)) < 26 ? 'older' : oldCategory) : '');
    if (['trending','favourites','later'].indexOf(p.get('mode')) >= 0) view.mode = p.get('mode');
    var allowed = { duration: ['any','under10','10to30','30to60','over60'], date: ['any','today','week','month','year'], watched: ['all','watched','unwatched'], sort: ['relevance','newest','popularity','trending'] };
    Object.keys(allowed).forEach(function (k) { if (allowed[k].indexOf(p.get(k)) >= 0) view.filters[k] = p.get(k); });
    Object.assign(state, view); requestedWatch = p.get('watch') || ''; el.search.value = state.query; el.version.value = state.version;
  }
  function closeDialog(skipHash) {
    if (!activeDialog) return; var previous = activeDialog; previous.classList.remove('open'); previous.setAttribute('aria-hidden', 'true'); activeDialog = null;
    document.documentElement.style.overflow = previousOverflow;
    if (previous === el.modal) { el.player.innerHTML = ''; state.currentVideo = null; if (skipHash !== true) setHash(); }
    if (dialogFocus && dialogFocus.isConnected) dialogFocus.focus();
  }
  function openDialog(node, focus) {
    if (activeDialog) closeDialog(); dialogFocus = document.activeElement; previousOverflow = document.documentElement.style.overflow;
    activeDialog = node; node.classList.add('open'); node.setAttribute('aria-hidden', 'false'); document.documentElement.style.overflow = 'hidden'; (focus || node.querySelector('button,input')).focus();
  }
  function goHome() { Object.assign(state, defaultView(), { shown: 12 }); el.search.value = ''; el.version.value = ''; renderAll(); }
  function viewChanged() { state.shown = 24; renderAll(); if (wantsCatalog()) ensureCatalog(); }
  function creatorRow(c) {
    return '<div class="yt-channel-row ' + (state.creator === c.id ? 'active' : '') + '"><img src="' + esc(c.avatar || '') + '" alt="" loading="lazy"><button class="yt-creator-select" data-creator="' + esc(c.id) + '" type="button"><span class="yt-channel-name">' + esc(c.name) + '</span><span class="yt-channel-subs">' + (c.subscriberCount == null ? 'FM creator' : fmt(c.subscriberCount) + ' subscribers') + '</span></button><button class="yt-star ' + (has('favourites', c.id) ? 'on' : '') + '" type="button" data-star="' + esc(c.id) + '" aria-pressed="' + has('favourites', c.id) + '" aria-label="' + (has('favourites', c.id) ? 'Unfollow ' : 'Follow ') + esc(c.name) + '">&#9733;</button></div>';
  }
  function sortedChannels(query) { return channels().filter(function (c) { return c.name.toLowerCase().indexOf(query.toLowerCase()) >= 0; }).sort(function (a, b) { return Number(has('favourites', b.id)) - Number(has('favourites', a.id)) || (b.subscriberCount || 0) - (a.subscriberCount || 0) || a.name.localeCompare(b.name); }); }
  function creatorList(query) {
    var list = sortedChannels(query), fav = list.filter(function (c) { return has('favourites', c.id); }), rest = list.filter(function (c) { return !has('favourites', c.id); });
    return '<button class="yt-all-channels" type="button" data-creator="">All channels <span>' + channels().length + ' creators</span></button>' + (fav.length ? '<div class="yt-side-section">Your channels</div>' + fav.map(creatorRow).join('') : '') + '<div class="yt-side-section">All creators</div>' + (rest.map(creatorRow).join('') || (!fav.length ? '<p class="yt-empty-small">No creators match this search.</p>' : ''));
  }
  function renderSidebar() {
    el['creator-list'].innerHTML = creatorList(el['creator-search'].value || '');
    var fav = sortedChannels('').filter(function (c) { return has('favourites', c.id); });
    el['mobile-creators'].innerHTML = '<button class="yt-all-creators-button" data-creators-open type="button">All creators <span>' + channels().length + '</span></button>' + fav.slice(0, 8).map(function (c) { return '<button class="yt-mobile-creator" data-creator="' + esc(c.id) + '" type="button"><img src="' + esc(c.avatar || '') + '" alt="" loading="lazy"><span>' + esc(c.name) + '</span></button>'; }).join('');
    if (activeDialog === el['creators-modal']) el['creators-list'].innerHTML = creatorList(el['creators-search'].value || '');
    el['fav-count'].textContent = prefs.favourites.length; el['later-count'].textContent = prefs.watchLater.length;
  }
  function renderCats() {
    el.cats.innerHTML = [''].concat(Object.keys(TOPICS)).map(function (t) { return '<button class="yt-chip ' + (state.category === t ? 'active' : '') + '" type="button" data-topic="' + esc(t) + '" aria-pressed="' + (state.category === t) + '">' + esc(t || 'All topics') + '</button>'; }).join('');
    root.querySelectorAll('[data-mode]').forEach(function (b) { b.classList.toggle('active', b.dataset.mode === state.mode); b.setAttribute('aria-pressed', String(b.dataset.mode === state.mode)); });
    el.version.value = state.version;
  }
  function thumbnail(v, cls, extra) { return '<div class="' + cls + '" data-play="' + esc(v.id) + '" role="button" tabindex="0" aria-label="Watch ' + esc(v.title) + '"><img data-video-image="' + esc(v.id) + '" src="' + esc(v.thumbnail) + '" alt="' + esc(v.title) + '" loading="lazy" decoding="async">' + (extra || '') + '<span class="yt-duration">' + esc(v.duration) + '</span></div>'; }
  function videoActions(v) { return '<div class="yt-card-actions"><button type="button" class="yt-save-button ' + (has('watchLater', v.id) ? 'saved' : '') + '" data-later="' + esc(v.id) + '" aria-pressed="' + has('watchLater', v.id) + '" aria-label="' + (has('watchLater', v.id) ? 'Remove ' : 'Save ') + esc(v.title) + (has('watchLater', v.id) ? ' from Watch later' : ' to Watch later') + '">' + (has('watchLater', v.id) ? '&#10003; Saved' : '+ Watch later') + '</button></div>'; }
  function card(v) {
    var badges = (Date.now() - Date.parse(v.publishedAt) < 864e5 ? '<span class="yt-new">New</span>' : '') + (has('watched', v.id) ? '<span class="yt-watched-badge">Watched</span>' : '');
    return '<article class="yt-video">' + thumbnail(v, 'yt-thumb', badges) + '<div class="yt-info"><img src="' + esc(v.channelAvatar) + '" alt="" loading="lazy"><div><button class="yt-video-title" type="button" data-play="' + esc(v.id) + '">' + esc(v.title) + '</button><button class="yt-video-channel" type="button" data-creator="' + esc(v.channelId) + '">' + esc(v.channelName) + '</button><div class="yt-video-meta">' + fmt(v.views) + ' views \u00b7 ' + relative(v.publishedAt) + '</div>' + (v.views24h == null ? '' : '<div class="yt-video-gain">+' + fmt(v.views24h) + ' views in 24h</div>') + '<div class="yt-video-tags">' + esc([v.gameVersion || (v.isFm === false ? 'Other football games' : ''), (v.topics || []).slice(0, 2).join(' / ')].filter(Boolean).join(' \u00b7 ')) + '</div>' + videoActions(v) + '</div></div></article>';
  }
  function renderFeature() {
    var ranked = filterVideos((state.data && state.data.videos) || [], Object.assign(defaultView(), { mode: 'trending' }), prefs, Date.now());
    var v = ranked[0], show = !!v;
    var label = v && v.views24h != null ? '\uD83D\uDD25 Most watched in the last 24h' : '\uD83D\uDD25 Trending now';
    var badge = v && v.views24h != null ? 'No. 1 in 24h' : 'Trending now';
    var gain = v && v.views24h != null ? '+' + fmt(v.views24h) + ' views in 24h' : '24-hour tracking is warming up';
    el.feature.innerHTML = show ? '<div class="yt-feature">' + thumbnail(v, 'yt-feature-media', '<span class="yt-feature-play"></span>') + '<div class="yt-feature-copy"><span class="yt-badge">' + badge + '</span><div class="yt-feature-title">' + esc(v.title) + '</div><div class="yt-creator-line"><img src="' + esc(v.channelAvatar) + '" alt=""><button type="button" data-creator="' + esc(v.channelId) + '">' + esc(v.channelName) + '</button></div><div class="yt-feature-meta">' + fmt(v.views) + ' views \u00b7 ' + relative(v.publishedAt) + '</div><div class="yt-gain">' + gain + '</div>' + videoActions(v) + '</div></div>' : '';
    $('#fmtv-pick-heading h3').textContent = label;
    $('#fmtv-pick-heading').hidden = !show; el.feature.dataset.pick = show ? v.id : '';
  }
  function renderTrending() {
    var view = Object.assign(defaultView(), { mode: 'trending' });
    var ranked = filterVideos((state.data && state.data.videos) || [], view, prefs, Date.now());
    el['trend-note'].textContent = state.data.views24hReady ? 'Actual views gained over the last 24 hours' : 'Recent momentum while 24-hour tracking builds';
    el['trending-row'].innerHTML = ranked.map(function (v, i) { return { video: v, rank: i + 1 }; }).filter(function (x) { return x.video.id !== el.feature.dataset.pick; }).slice(0, 3).map(function (x) {
      var v = x.video; return '<article class="yt-trend-item">' + thumbnail(v, 'yt-trend-thumb', '<span class="yt-rank">' + String(x.rank).padStart(2, '0') + '</span>') + '<button type="button" class="yt-trend-title" data-play="' + esc(v.id) + '">' + esc(v.title) + '</button><div class="yt-trend-by">' + esc(v.channelName) + '</div><div class="yt-trend-gain">' + (v.views24h == null ? 'Recent momentum' : '+' + fmt(v.views24h) + ' views in 24h') + '</div></article>';
    }).join('');
  }
  function renderChannelHead() {
    var home = !state.creator && !state.query && !state.category && !state.version && state.mode === 'latest' && !filterCount();
    el['home-only'].hidden = !home; el['home-only'].style.display = home ? 'block' : 'none';
    if (state.creator) {
      var c = channelById(state.creator); if (!c) { el['channel-head'].innerHTML = ''; return; }
      el['channel-head'].innerHTML = '<section class="yt-channel-head"><button class="yt-back" type="button" data-home>&#8592; FM TV home</button><div class="yt-channel-top"><img class="yt-channel-avatar" src="' + esc(c.avatar) + '" alt=""><div class="yt-channel-main"><h2 class="yt-channel-title">' + esc(c.name) + '</h2><div class="yt-channel-stats">' + (c.subscriberCount == null ? 'Football Manager creator' : fmt(c.subscriberCount) + ' subscribers') + '</div></div><div class="yt-channel-actions"><button class="yt-channel-fav ' + (has('favourites', c.id) ? 'on' : '') + '" data-star="' + esc(c.id) + '" aria-pressed="' + has('favourites', c.id) + '" type="button">' + (has('favourites', c.id) ? '&#9733; Following' : '&#9734; Follow') + '</button><a class="yt-subscribe" href="' + esc(c.channelUrl) + '" target="_blank" rel="noopener noreferrer">YouTube channel</a></div></div>' + (c.description ? '<p class="yt-channel-desc">' + esc(c.description) + '</p>' : '') + '</section>';
    } else el['channel-head'].innerHTML = home ? '' : '<button class="yt-back" type="button" data-home>&#8592; FM TV home</button>';
  }
  function renderGrid() {
    var list = results(), shown = list.slice(0, state.shown), split = Math.min(6, shown.length), mode = state.mode;
    root.classList.remove('search-view'); // One consistent grid avoids a second, jumpy search layout.
    var title = state.query ? 'Results for “' + state.query + '”' : mode === 'trending' ? '\uD83D\uDD25 Most watched in the last 24h' : mode === 'later' ? 'Watch later' : mode === 'favourites' ? 'Latest from your channels' : state.creator ? (channelById(state.creator) || {}).name + ' videos' : state.category ? state.category + ' videos' : state.version === 'other' ? 'Other football games' : state.version ? (state.version === 'older' ? 'Older Football Manager' : state.version) + ' videos' : 'Latest from the FM community';
    el['grid-title'].textContent = title;
    var note = state.archiveLoading ? 'Loading the full catalogue. Recent videos stay available.' : state.archiveError ? 'The full catalogue could not load. Showing recent videos.' : state.mode === 'later' ? (account ? (syncMessage === 'Synced with your FM Blog account' ? 'Your saved FM TV videos, synced with your FM Blog account.' : 'Your saved FM TV videos. Account sync is pending.') : 'Your saved FM TV videos. This list is stored in this browser only.') : state.mode === 'favourites' && !prefs.favourites.length ? 'Choose All creators and follow the channels you enjoy.' : state.archive && wantsCatalog() ? 'Searching recent uploads and the past-year catalogue.' : '';
    el['grid-note'].textContent = note;
    var empty = mode === 'later' ? (prefs.watchLater.length ? (state.creator || state.category || state.version || state.query.trim() || filterCount() ? 'No saved videos match these filters.' : state.archiveLoading ? 'Loading your saved videos...' : 'Your saved videos are not available in the current catalogue.') : 'Your Watch later list is empty. Use + Watch later on any video.') : mode === 'favourites' && !prefs.favourites.length ? 'Follow a creator to build your own feed.' : 'No videos match these filters. Try another topic or game version.';
    el['grid-a'].innerHTML = shown.length ? shown.slice(0, split).map(card).join('') : '<div class="yt-empty">' + empty + '</div>';
    el['grid-b'].innerHTML = shown.slice(split).map(card).join(''); el['feed-ad'].style.display = shown.length > split ? 'block' : 'none';
    el.count.textContent = list.length + ' video' + (list.length === 1 ? '' : 's');
    el.load.hidden = !(list.length > state.shown || state.archiveError);
    el.load.style.display = el.load.hidden ? 'none' : 'inline-block'; el.load.disabled = state.archiveLoading;
    el.load.textContent = state.archiveLoading ? 'Loading...' : state.archiveError ? 'Retry full catalogue' : 'Show more';
    updateFilterUI();
  }
  function renderFavShelf() {
    var view = Object.assign(defaultView(), { mode: 'favourites' });
    var list = filterVideos(state.data.videos, view, prefs, Date.now()).slice(0, 3);
    el['fav-shelf'].hidden = !list.length; el['fav-grid'].innerHTML = list.map(card).join('');
  }
  function updateFilterUI() {
    var f = state.draftFilters || state.filters;
    root.querySelectorAll('[data-filter-group]').forEach(function (b) { var on = f[b.dataset.filterGroup] === b.dataset.filterValue; b.classList.toggle('active', on); b.setAttribute('aria-pressed', String(on)); });
    el['filter-count'].textContent = filterCount(); el['filter-open'].classList.toggle('has-filters', filterCount() > 0);
    var count = Number(f.duration !== 'any') + Number(f.date !== 'any') + Number(f.watched !== 'all') + Number(f.sort !== 'relevance');
    el['filter-summary'].textContent = count ? count + ' filter' + (count === 1 ? '' : 's') + ' selected' : 'No extra filters applied';
  }
  function renderAll(updateHash) {
    renderSync(); if (!state.data) return;
    renderSidebar(); renderCats(); renderChannelHead(); renderFeature(); renderTrending(); renderFavShelf(); renderGrid();
    el.updated.textContent = (state.stale ? 'Saved feed \u00b7 ' : 'Updated ') + relative(state.data.generatedAt);
    if (updateHash !== false) setHash();
  }
  function relatedLinks(v) {
    var links = [];
    if (v.id === PICK) links.push({ title: 'Read the FM27 gameplay breakdown', href: 'https://www.footballmanagerblog.org/2026/10/fm27-gameplay-preview-new-features-in.html' });
    if (v.gameVersion === 'FM26' && (v.topics || []).indexOf('Wonderkids') >= 0) links.push({ title: 'Explore the FM26 wonderkids shortlist', href: 'https://www.footballmanagerblog.org/2025/10/fm26-wonderkids-pa-price-position.html' });
    if ((v.topics || []).indexOf('Tactics') >= 0) links.push({ title: 'Browse Football Manager tactics', href: 'https://www.footballmanagerblog.org/p/football-manager-tactics.html' });
    if ((v.topics || []).some(function (t) { return t === 'Saves' || t === 'Rebuilds'; })) links.push({ title: 'Find your next Football Manager save', href: 'https://www.footballmanagerblog.org/p/football-manager-save-ideas.html' });
    if ((v.topics || []).some(function (t) { return t === 'Guides' || t === 'Training'; })) links.push({ title: 'Browse Football Manager guides', href: 'https://www.footballmanagerblog.org/p/fm-game-guides-hub.html' });
    if (v.gameVersion === 'FM27' && !links.length) links.push({ title: 'Read the latest FM27 coverage', href: 'https://www.footballmanagerblog.org/p/football-manager-2027.html' });
    return links.slice(0, 2);
  }
  function renderPlayerActions() {
    var v = state.currentVideo; if (!v) return;
    el['player-actions'].innerHTML = '<button type="button" class="yt-save-button ' + (has('watchLater', v.id) ? 'saved' : '') + '" data-later="' + esc(v.id) + '" aria-pressed="' + has('watchLater', v.id) + '">' + (has('watchLater', v.id) ? '&#10003; Saved for later' : '+ Watch later') + '</button><button type="button" class="yt-save-button" data-watched="' + esc(v.id) + '" aria-pressed="' + has('watched', v.id) + '">' + (has('watched', v.id) ? '&#10003; Watched' : 'Mark as watched') + '</button><a href="https://www.youtube.com/watch?v=' + encodeURIComponent(v.id) + '" target="_blank" rel="noopener noreferrer">Watch on YouTube &#8599;</a>';
    var links = relatedLinks(v); el.related.innerHTML = links.length ? '<span>Related on FM Blog</span>' + links.map(function (link) { return '<a href="' + esc(link.href) + '">' + esc(link.title) + ' &#8594;</a>'; }).join('') : '';
    el.related.hidden = !links.length;
  }
  function openVideo(video) {
    if (!video) return; if (activeDialog) closeDialog(true); state.currentVideo = video; el['modal-title'].textContent = video.title;
    el.player.innerHTML = '<iframe src="https://www.youtube.com/embed/' + encodeURIComponent(video.id) + '?autoplay=1&rel=0" title="' + esc(video.title) + '" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>';
    renderPlayerActions(); openDialog(el.modal, el.close); setHash();
  }
  async function openRequestedVideo() {
    if (!requestedWatch) return; var id = requestedWatch, video = findVideo(id);
    if (!video && !state.archive) { await ensureCatalog(); video = findVideo(id); }
    if (requestedWatch !== id) return; requestedWatch = ''; if (video) openVideo(video);
    else showStatus('That video is no longer in the current catalogue. You can still browse the latest uploads.', false);
  }
  function showStatus(message, retry) { el.status.hidden = !message; el.status.innerHTML = message ? '<span>' + esc(message) + '</span>' + (retry ? '<button type="button" data-retry-feed>Retry</button>' : '') : ''; }
  function ensureCatalog(reload) {
    if (state.archiveLoading) return catalogPromise;
    if (state.archive && !reload) return Promise.resolve();
    state.archiveLoading = true; state.archiveError = false; if (state.data) renderGrid();
    catalogPromise = (async function () {
      try { var response = await fetch(DATA + 'catalog.json', { cache: reload ? 'reload' : 'default' }); if (!response.ok) throw new Error('Catalogue unavailable'); state.archive = hydrate(await response.json()); }
      catch (e) { state.archiveError = true; }
      finally { state.archiveLoading = false; renderAll(false); }
    })();
    return catalogPromise;
  }
  async function loadFeed(reload) {
    if (state.loading) return; state.loading = true;
    try {
      var response = await fetch(DATA + 'videos.json', { cache: reload ? 'reload' : 'default' }); if (!response.ok) throw new Error('Feed unavailable');
      var raw = await response.json(), candidate = hydrate(raw); if (!candidate.videos.length) throw new Error('Empty feed'); state.data = candidate;
      state.stale = false; try { localStorage.setItem(CACHE_KEY, JSON.stringify(raw)); } catch (e) {}
      showStatus('', false); renderAll(false); if (requestedWatch) openRequestedVideo(); else { setHash(); if (wantsCatalog()) ensureCatalog(); }
    } catch (e) {
      if (!state.data) { try { state.data = hydrate(JSON.parse(localStorage.getItem(CACHE_KEY) || 'null')); } catch (ignored) {} }
      state.stale = true;
      showStatus(state.data ? 'The live feed could not refresh. Showing the last saved feed from ' + new Date(state.data.generatedAt).toLocaleString('en-GB') + '.' : 'The video feed could not load. Please try again.', true);
      renderAll(false);
    } finally { state.loading = false; }
  }
  root.addEventListener('click', function (event) {
    var target = event.target.closest('button,[data-play]'); if (!target || !root.contains(target)) return;
    if (target.hasAttribute('data-star')) { setPreference('favourites', target.dataset.star, !has('favourites', target.dataset.star)); return; }
    if (target.hasAttribute('data-later')) { setPreference('watchLater', target.dataset.later, !has('watchLater', target.dataset.later)); return; }
    if (target.hasAttribute('data-watched')) { setPreference('watched', target.dataset.watched, !has('watched', target.dataset.watched)); return; }
    if (target.hasAttribute('data-play')) { openVideo(findVideo(target.dataset.play)); return; }
    if (target.hasAttribute('data-creator')) { if (activeDialog === el['creators-modal']) closeDialog(); state.creator = target.dataset.creator; state.mode = 'latest'; state.query = ''; el.search.value = ''; viewChanged(); return; }
    if (target.hasAttribute('data-mode')) { if (target.dataset.mode === 'later') { Object.assign(state, defaultView()); el.version.value = ''; } state.mode = target.dataset.mode; state.creator = ''; state.query = ''; el.search.value = ''; viewChanged(); return; }
    if (target.hasAttribute('data-topic')) { state.category = target.dataset.topic; viewChanged(); return; }
    if (target.hasAttribute('data-home')) { goHome(); return; }
    if (target.hasAttribute('data-creators-open')) { el['creators-search'].value = ''; el['creators-list'].innerHTML = creatorList(''); openDialog(el['creators-modal'], el['creators-search']); return; }
    if (target.hasAttribute('data-retry-feed')) { loadFeed(true); return; }
    if (target.id === 'fmtv-sync-retry') { if (pending.length && accountVersion != null) flushSync(); else loadSync(accountEpoch); return; }
    if (target.dataset.filterGroup) { state.draftFilters[target.dataset.filterGroup] = target.dataset.filterValue; updateFilterUI(); }
  });
  root.addEventListener('keydown', function (event) { var node = event.target.closest('[data-play]'); if (node && node.tagName !== 'BUTTON' && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); node.click(); } });
  document.addEventListener('keydown', function (event) {
    if (!activeDialog) return;
    if (event.key === 'Escape') { event.preventDefault(); closeDialog(); return; }
    if (event.key !== 'Tab') return;
    var items = Array.from(activeDialog.querySelectorAll('button:not([disabled]),a[href],input,select,iframe,[tabindex="0"]')).filter(function (n) { return n.getClientRects().length; });
    if (!items.length) return; var first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  [el.modal, el['filter-modal'], el['creators-modal']].forEach(function (node) { node.addEventListener('click', function (event) { if (event.target === node) closeDialog(); }); });
  [el.close, el['filter-close'], el['creators-close']].forEach(function (node) { node.addEventListener('click', closeDialog); });
  el['filter-open'].addEventListener('click', function () { state.draftFilters = Object.assign({}, state.filters); updateFilterUI(); openDialog(el['filter-modal'], el['filter-close']); });
  el['filter-clear'].addEventListener('click', function () { state.draftFilters = defaultFilters(); updateFilterUI(); });
  el['filter-apply'].addEventListener('click', function () { state.filters = Object.assign({}, state.draftFilters); state.draftFilters = null; closeDialog(); viewChanged(); });
  el.version.addEventListener('change', function () { state.version = el.version.value; viewChanged(); });
  function runSearch() { clearTimeout(searchTimer); state.query = el.search.value.trim(); state.creator = ''; state.mode = 'latest'; viewChanged(); }
  el.search.addEventListener('input', function () { clearTimeout(searchTimer); searchTimer = setTimeout(runSearch, 180); });
  el.search.addEventListener('keydown', function (event) { if (event.key === 'Enter') { event.preventDefault(); runSearch(); } });
  el['search-btn'].addEventListener('click', runSearch);
  el['creator-search'].addEventListener('input', function () { el['creator-list'].innerHTML = creatorList(el['creator-search'].value); });
  el['creators-search'].addEventListener('input', function () { el['creators-list'].innerHTML = creatorList(el['creators-search'].value); });
  el.load.addEventListener('click', function () { if (state.archiveError) ensureCatalog(true); else { state.shown += 12; renderGrid(); } });
  root.addEventListener('error', function (event) {
    var image = event.target; if (!image || image.tagName !== 'IMG' || !image.dataset.videoImage) return;
    var id = image.dataset.videoImage, candidates = ['https://i.ytimg.com/vi/' + id + '/hqdefault.jpg', 'https://i.ytimg.com/vi/' + id + '/mqdefault.jpg'];
    var tried = (image.dataset.tried || '').split('|'); tried.push(image.src); image.dataset.tried = tried.join('|');
    var next = candidates.find(function (url) { return tried.indexOf(url) < 0; });
    if (next) image.src = next; else { image.style.visibility = 'hidden'; image.parentElement.classList.add('yt-image-unavailable'); }
  }, true);
  window.addEventListener('hashchange', function () { if (activeDialog) closeDialog(true); readHash(); state.shown = 24; renderAll(false); if (requestedWatch) openRequestedVideo(); else if (wantsCatalog()) ensureCatalog(); });
  window.addEventListener('fmb:auth-ready', connectAuth);
  window.addEventListener('online', function () { if (account) loadSync(accountEpoch); if (state.stale) loadFeed(true); });
  document.addEventListener('visibilitychange', function () { if (!document.hidden && account && !syncBusy) loadSync(accountEpoch); });
  changeAccount(null); readHash(); connectAuth(); loadFeed(false);
})();
