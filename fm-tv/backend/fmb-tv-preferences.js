/* FM TV preferences v1. Reuses the deployed Worker's verified Firebase identity and CSRF. */
export const FM_TV_PREFERENCES_PATH = '/api/fm-tv/preferences';
const ORIGINS = new Set([
  'https://www.footballmanagerblog.org',
  'https://footballmanagerblog.org',
  'https://database.footballmanagerblog.org'
]);
const REQUEST_HEADERS = new Set(['authorization', 'content-type', 'x-fmb-csrf', 'x-fmb-user']);
const MAX_BODY_BYTES = 32768;
const MAX_OPERATIONS = 100;
const LIMITS = Object.freeze({favourites:200, watchLater:300, watched:500, progress:200});
const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
const CHANNEL_ID = /^UC[A-Za-z0-9_-]{22}$/;
const UID = /^[A-Za-z0-9_-]{1,128}$/;
const SELECT_SQL = 'SELECT version,state_json,updated_at FROM fmb_tv_preferences_v1 WHERE uid=?';
const INSERT_SQL = 'INSERT INTO fmb_tv_preferences_v1(uid,version,state_json,updated_at) VALUES(?,1,?,?) ON CONFLICT(uid) DO NOTHING RETURNING version,state_json,updated_at';
const UPDATE_SQL = 'UPDATE fmb_tv_preferences_v1 SET version=version+1,state_json=?,updated_at=? WHERE uid=? AND version=? RETURNING version,state_json,updated_at';

function fail(message, status=400, code='INVALID_REQUEST') {
  throw Object.assign(new Error(message), {status, code});
}
function responseHeaders(request, json=true) {
  const headers = new Headers({
    'Cache-Control':'private, no-store, max-age=0',
    'X-Content-Type-Options':'nosniff',
    'X-Robots-Tag':'noindex, nofollow',
    'Referrer-Policy':'no-referrer',
    'Vary':'Origin'
  });
  if (json) headers.set('Content-Type','application/json; charset=utf-8');
  const origin = request.headers.get('origin');
  if (ORIGINS.has(origin)) {
    headers.set('Access-Control-Allow-Origin',origin);
    headers.set('Access-Control-Allow-Credentials','true');
  }
  return headers;
}
function reply(request, value, status=200) {
  return new Response(JSON.stringify(value), {status, headers:responseHeaders(request)});
}
function blankState() { return {favourites:[], watchLater:[], watched:[], progress:{}}; }
function view(uid, row) {
  const state = row ? JSON.parse(row.state_json) : blankState();
  return {uid,version:row ? Number(row.version) : 0,...state,updatedAt:row ? Number(row.updated_at) : 0};
}
async function boundedJson(request) {
  if ((request.headers.get('content-type') || '').split(';')[0].trim().toLowerCase() !== 'application/json') {
    fail('Use a JSON request.',415,'UNSUPPORTED_MEDIA_TYPE');
  }
  if (Number(request.headers.get('content-length') || 0) > MAX_BODY_BYTES) fail('Too many changes in one request.',413,'BODY_TOO_LARGE');
  const reader = request.body?.getReader();
  if (!reader) fail('A JSON request body is required.');
  const chunks=[];let length=0;
  while (true) {
    const {done,value}=await reader.read();
    if (done) break;
    length+=value.byteLength;
    if (length>MAX_BODY_BYTES) { await reader.cancel();fail('Too many changes in one request.',413,'BODY_TOO_LARGE'); }
    chunks.push(value);
  }
  const bytes=new Uint8Array(length);let offset=0;
  for (const chunk of chunks) { bytes.set(chunk,offset);offset+=chunk.length; }
  try { return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)); }
  catch { fail('The request is not valid JSON.'); }
}
function validateRequest(body) {
  if (!body || typeof body!=='object' || Array.isArray(body) ||
      !Number.isSafeInteger(body.baseVersion) || body.baseVersion<0 ||
      !Array.isArray(body.operations) || !body.operations.length || body.operations.length>MAX_OPERATIONS ||
      Object.keys(body).some(key=>!['baseVersion','operations'].includes(key))) fail('Invalid preference changes.');
  for (const op of body.operations) {
    if (!op || typeof op!=='object' || Array.isArray(op) ||
        !Object.hasOwn(LIMITS,op.type) || typeof op.id!=='string' ||
        !(op.type==='favourites'?CHANNEL_ID:VIDEO_ID).test(op.id) ||
        Object.keys(op).some(key=>!['type','id','value'].includes(key))) fail('Invalid preference change.');
    if (op.type==='progress') {
      if (op.value===null) continue;
      if (!op.value || typeof op.value!=='object' || Array.isArray(op.value) ||
          Object.keys(op.value).some(key=>!['seconds','duration'].includes(key)) ||
          !Number.isFinite(op.value.seconds) || op.value.seconds<0 || op.value.seconds>172800 ||
          !Number.isFinite(op.value.duration) || op.value.duration<0 || op.value.duration>172800 ||
          (op.value.duration>0 && op.value.seconds>op.value.duration+2)) fail('Invalid playback position.');
    } else if (typeof op.value!=='boolean') fail('Preference values must be true or false.');
  }
  return body;
}
export function applyFmTvOperations(state,operations) {
  const sets={favourites:new Set(state.favourites),watchLater:new Set(state.watchLater),watched:new Set(state.watched)};
  const progress=new Map(Object.entries(state.progress || {}));
  for (const op of operations) {
    if (op.type==='progress') {
      progress.delete(op.id);
      if (op.value!==null) progress.set(op.id,{seconds:Math.round(op.value.seconds),duration:Math.round(op.value.duration)});
    } else {
      sets[op.type].delete(op.id);
      if (op.value) sets[op.type].add(op.id);
    }
  }
  for (const name of ['favourites','watchLater']) {
    if (sets[name].size>LIMITS[name]) fail('Your '+(name==='favourites'?'favourite creator':'Watch later')+' list is full.',422,'LIMIT_EXCEEDED');
  }
  while (sets.watched.size>LIMITS.watched) sets.watched.delete(sets.watched.values().next().value);
  while (progress.size>LIMITS.progress) progress.delete(progress.keys().next().value);
  return {favourites:[...sets.favourites],watchLater:[...sets.watchLater],watched:[...sets.watched],progress:Object.fromEntries(progress)};
}
async function verifiedUid(request,auth) {
  // This is an account-selection guard, never an authentication credential.
  const expectedUid=request.headers.get('x-fmb-user') || '';
  if (!UID.test(expectedUid)) fail('Sign in to sync your FM TV lists.',401,'SIGN_IN_REQUIRED');
  const session=auth.cookies(request).get('__Host-fmb_session');
  let claims;
  try {
    if (session) {
      // Shared-session restoration creates Firebase custom-provider ID tokens.
      // Keep the existing revocation-checked session as authority, without
      // broadening the existing ID-token validator's provider allowlist.
      claims=await auth.verifySession(session);
    } else {
      const token=request.headers.get('authorization')?.match(/^Bearer ([A-Za-z0-9_.-]{100,10000})$/)?.[1];
      if (!token) fail('Sign in to sync your FM TV lists.',401,'SIGN_IN_REQUIRED');
      claims=await auth.verifyId(token);
    }
  } catch (error) {
    if (error?.status===401) throw error;
    if (error?.name==='FirebaseServiceUnavailableError') fail('Account verification is temporarily unavailable.',503,'AUTH_UNAVAILABLE');
    // An invalid/revoked session never falls back to a bearer token.
    fail('Your sign-in has expired. Sign in again.',401,'SIGN_IN_EXPIRED');
  }
  if (!UID.test(claims?.sub || '')) fail('Invalid account.',401,'INVALID_ACCOUNT');
  if (claims.sub!==expectedUid) fail('Your signed-in account changed. Refresh before syncing.',401,'ACCOUNT_CHANGED');
  return claims.sub;
}
export async function handleFmTvPreferences(request,env,ctx,auth) {
  if (new URL(request.url).pathname!==FM_TV_PREFERENCES_PATH) return null;
  try {
    if (!ORIGINS.has(request.headers.get('origin'))) fail('Origin not allowed.',403,'ORIGIN_NOT_ALLOWED');
    if (request.method==='OPTIONS') {
      if (!['GET','POST'].includes(request.headers.get('access-control-request-method'))) fail('Method not allowed.',405,'METHOD_NOT_ALLOWED');
      const requested=request.headers.get('access-control-request-headers') || '';
      if (requested && requested.split(',').some(h=>!REQUEST_HEADERS.has(h.trim().toLowerCase()))) fail('Headers not allowed.',403,'HEADERS_NOT_ALLOWED');
      const headers=responseHeaders(request,false);
      headers.set('Access-Control-Allow-Methods','GET, POST, OPTIONS');
      headers.set('Access-Control-Allow-Headers','Authorization, Content-Type, X-FMB-CSRF, X-FMB-User');
      headers.set('Access-Control-Max-Age','600');
      return new Response(null,{status:204,headers});
    }
    if (!['GET','POST'].includes(request.method)) fail('Method not allowed.',405,'METHOD_NOT_ALLOWED');
    if (request.method==='POST') {
      try { auth.checkCsrf(request); }
      catch { fail('Security check failed. Refresh the page and try again.',403,'INVALID_CSRF'); }
    }
    const uid=await verifiedUid(request,auth);
    if (!env.DB?.prepare) fail('FM TV sync is temporarily unavailable.',503,'SYNC_UNAVAILABLE');
    const body=request.method==='POST'?validateRequest(await boundedJson(request)):null;
    // Primary session provides read-your-writes without a cross-request bookmark.
    const db=typeof env.DB.withSession==='function'?env.DB.withSession('first-primary'):env.DB;
    const row=await db.prepare(SELECT_SQL).bind(uid).first();
    const current=view(uid,row);
    if (!body) return reply(request,current);
    if (current.version!==body.baseVersion) return reply(request,{...current,code:'VERSION_CONFLICT',error:'Your lists changed elsewhere. Retry these changes using the current version.'},409);
    const next=applyFmTvOperations(current,body.operations);
    const json=JSON.stringify(next);
    if (new TextEncoder().encode(json).length>65536) fail('Your FM TV preferences are too large.',422,'LIMIT_EXCEEDED');
    const now=Date.now();
    const saved=row
      ?await db.prepare(UPDATE_SQL).bind(json,now,uid,body.baseVersion).first()
      :await db.prepare(INSERT_SQL).bind(uid,json,now).first();
    if (!saved) {
      const latest=view(uid,await db.prepare(SELECT_SQL).bind(uid).first());
      return reply(request,{...latest,code:'VERSION_CONFLICT',error:'Your lists changed elsewhere. Retry these changes using the current version.'},409);
    }
    return reply(request,view(uid,saved));
  } catch (error) {
    const status=Number(error.status)||503;
    if (status>=500) console.error('FM TV preference sync failed',{name:error.name});
    return reply(request,{error:status>=500?'FM TV sync is temporarily unavailable. Your local changes are kept.':error.message,code:error.code || 'SYNC_UNAVAILABLE'},status);
  }
}
