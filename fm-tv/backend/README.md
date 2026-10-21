# FM TV preferences backend

## Current deployment status

Verified on 21 October 2026 at 03:24 UTC. The live `fm-blog-database` Worker already contains this module and its isolated wrapper, deployed at `2026-10-21T03:17:06.001232Z`. Its current etag is `e28aedf687101bdd4b63c60dafdcfd9c2ae7594c94a9fba06b7913c84263290d`.

All 46 deployed modules match the corrected deployment dry-run inventory byte-for-byte by SHA-256, including the existing analytics guard and community/authentication modules. The preference module hash is `4290904d2a9600b7ac453990fa93cb5e44f69394c39fcfa21704e4dd8772375b`. The live `fmb_tv_preferences_v1` table exists with the schema below. No duplicate migration or redeployment was performed during the resumed verification.

The 10 backend tests pass. Raw executor HTTP requests were blocked at Cloudflare with error 1010 before reaching the Worker, so signed-in production GET/POST and cross-device persistence have not been verified by that route. Verify those through a normal authenticated site session; do not weaken site protection for testing. Source/schema verification does not establish an end-to-end signed-in sync pass.

## Scope

`fmb-tv-preferences.js` implements only `/api/fm-tv/preferences`. It reuses `cl(session)`, `ul(token, 'id')`, `$0(request)` and `bl(request)` from the current `fm-blog-database` Worker. It does not modify the community authentication flow, Firebase configuration, CORS elsewhere, security rules, secrets, or existing handlers.

Current DB binding is `DB`, database ID `0db4e400-2e0c-4eff-812a-e1b4ff73aebb`. The additive `migration.sql` is applied.

## Frontend contract

All requests originate from the existing trusted origins (main blog, apex blog, database host). Always use `credentials: 'include'` and `Authorization: Bearer <Firebase ID token>`. Also send `X-FMB-User: <current Firebase user.uid>` on GET/POST as an account-selection guard. Identity comes from the existing revocation-checked session if a cookie exists, otherwise the verified normal-provider token. The verified UID must exactly match X-FMB-User before any D1 access. A mismatched account returns 401 ACCOUNT_CHANGED with no state/read/write. An invalid existing session fails closed and never falls back to a bearer token. This supports shared-session-restored custom-provider tokens without broadening the existing bearer provider allowlist.

GET returns:

```json
{"uid":"verified-uid","version":0,"favourites":[],"watchLater":[],"watched":[],"progress":{},"updatedAt":0}
```

Before POST, GET `/api/community/csrf` with credentials, then use its `csrfToken` as `X-FMB-CSRF`.

```json
{
  "baseVersion": 0,
  "operations": [
    {"type":"favourites","id":"UCabcdefghijklmnopqrstuv","value":true},
    {"type":"watchLater","id":"abcdefghijk","value":true},
    {"type":"watched","id":"lmnopqrstuv","value":false},
    {"type":"progress","id":"abcdefghijk","value":{"seconds":120,"duration":1800}}
  ]
}
```

A successful POST returns the full authoritative state with the incremented version. A stale version or concurrent write returns HTTP 409, with exactly the same top-level state fields plus `code: 'VERSION_CONFLICT'` and `error`. Replay only pending per-item operations against the returned version; never upload stale full lists. Server writes use SQL compare-and-set, including concurrent first writes. Operations use explicit true/false (or a position/null), so a retry is idempotent in meaning.

Keep an account epoch/UID guard around all asynchronous frontend work. Drop old account pending operations on account change. Anonymous lists must not be automatically copied to each subsequent signed-in user. Do not display cloud-synced status before a successful response.

Limits: 100 operations/request, 32 KiB request, 200 favourite creators, 300 Watch later videos, latest 500 watched entries and latest 200 playback positions. Full favourite/Watch later lists return 422 `LIMIT_EXCEEDED` with no partial write. Watched/progress history evicts oldest entries. No login, emails, tokens or video titles are stored. All SQL uses bound parameters; all queries are by the primary-key UID.

## Deployment preparation

1. Re-read the current live Worker and its settings immediately before applying, since other conversations may update it.
2. Preserve every module, binding and setting. The downloaded Worker currently has about 5.3 MB and 45 modules; a tool response of about 24 KB is truncated and cannot be redeployed.
3. Run `migration.sql` once against the existing `DB`. It only creates `fmb_tv_preferences_v1` if absent.
4. Add `fmb-tv-preferences.js` as one module.
5. Append `worker-wrapper.js.txt` to the current `index.js`. Verify that `zA` is still the default handler object, `bl` the existing CSRF validator, `$0` the cookie reader, `cl` the revocation-checked session verifier and `ul` the existing token verifier. The wrapper delegates every other path unchanged. Do not append twice.
6. Parse-check the patched entrypoint and new module, upload with the complete current multipart and all current settings/bindings, then verify the isolated route and community/session routes.

Do not deploy the truncated diagnostic `worker-downloaded.multipart`. It is only a record that the first large tool response was truncated. The other `*-current`/`*-excerpt` files are diagnostic references, not deployable replacements.

## Validation already performed

`node --test preferences.test.mjs`: 10 passing tests using real SQLite statements. Covers origin/CSRF/auth rejection without writes, CORS, cross-account isolation, stale-version replay preserving concurrent lists, simultaneous first writes, invalid IDs/body size/malformed changes, list bounds without partial writes, watched eviction/progress, and temporary auth-service errors.

The original preparation subtask made no live D1 writes or Worker deployment. The current state was subsequently deployed and is recorded above.

## Safe Cloudflare deployment callback

Run `node make-deploy-callback.mjs` to regenerate `cloudflare-deploy-callback.js` from the reviewed module and wrapper. It defaults to `dryRun = true` and has already passed a real read-only Cloudflare dry run. It fetches the complete current multipart inside the Cloudflare tool runtime, validates the Worker metadata etag/modified timestamp and auth seam, preserves all original module bodies except appending the isolated wrapper to `index.js`, adds one new module, and returns SHA-256 inventory. No truncated Worker source enters the upload.

For the actual reviewed deployment, after applying the migration, use the same callback with only `dryRun = false`. It rechecks metadata and settings immediately before PUT. It uses `keep_assets: true` and `keep_bindings` for every existing binding type, including secrets and any durable object bindings, without retrieving secret values. No Durable Object migration is introduced or reset. The currently deployed Worker has no durable-object binding or migration settings. The upload does not have a true conditional-write HTTP header through this connector, so another concurrent deployment in the last instant remains a narrow race; coordinate with other active writers.

Copy only these implementation files to the GitHub repository: module, migration, wrapper, tests, README, callback generator and callback. Keep diagnostic source excerpts out of the repository.

### Multipart file correction

A production upload attempt without `filename` on downloaded module parts was rejected by Cloudflare validation (`No such module index.js`); the original Worker etag and modified timestamp remained unchanged. The callback now adds `filename` to every module Content-Disposition header and round-trips the complete multipart through `Response.formData()` before either dry-run return or upload. It verifies all 46 module fields are files, their bodies match exactly, and main_module resolves to the single index.js file. The corrected read-only dry run passed. This changes only upload framing, not Worker code or bindings.
