# FM TV v8

The YouTubers Hub at `https://www.footballmanagerblog.org/p/fm-youtubers-hub.html` uses the existing FM Blog page shell with separate game-version and topic filters, searchable creators on mobile, Watch later, explicit watched status and account preference synchronisation.

## Sources and data

- `app-v8.js` and `styles-v8.css` are the editable frontend sources.
- `live-v7-backup.html` preserves the page shell used by `scripts/build_v8.py`.
- Run `python fm-tv/scripts/build_v8.py` from the repository root to generate `blogger-embed-v8.html`, `preview-v8.html` and `responsive-preview-v8.html`.
- The initial feed is `data/videos.json`. Search and filters load `data/catalog.json` on demand. Recent uploads are merged by video ID and override stale catalogue fields.
- `scripts/catalog.py` compacts shared creator metadata and derived image URLs. Both existing YouTube update workflows rebuild the catalogue and share a concurrency group.
- Videos use thumbnails until clicked. The player opens only on request. Opening a video does not mark it watched.

## Preferences

Guest choices remain in browser storage. Signed-in choices use the existing `window.FMBlogAuth` session and `/api/fm-tv/preferences` on the database host. Per-item operations, account guards and version conflicts protect independent changes from different devices. Failed sync preserves local changes and displays a retry option.

`backend/README.md` documents the deployed route, additive D1 schema, deployment safeguards and authentication contract. The preference module and schema were verified live on 21 October 2026. The backend deployment callback is retained as a reviewed deployment record with `dryRun = true` and its original expected Worker revision; do not run it against another revision without reviewing the current Worker.

## Publishing

Publish the catalogue and updater changes before updating Blogger. The target blog ID is `3612031012790362698`, page ID `4704060642968272727`. Preserve the existing page metadata and paste the complete generated `blogger-embed-v8.html` body in HTML view. The expected marker is `data-fmtv-build="v8-discovery-2026-10-21"`.

Re-read the current Blogger body before an update and compare it with the preserved shell to avoid overwriting newer work. Repository changes must preserve the newest generated feeds.

## Validation

Verified in this release:

- Frontend regression suite: `node --test fm-tv/tests/frontend-v8.test.cjs`, 12 passing tests.
- Catalogue regression suite: `python -m unittest discover -s fm-tv/scripts -p test_catalog.py`, 10 passing tests.
- Backend regression suite: `node --test fm-tv/backend/preferences.test.mjs`, 10 passing tests.
- Desktop/mobile layout and the combined FM27 + Wonderkids filters passed browser QA.
- Blogger publication was verified by reopening its full 98,817-character HTML and comparing it exactly with the generated embed. The live page exposes the V8 marker, retains the analytics exclusion and has no horizontal overflow at a 1,348-pixel viewport.

The agent environment could not load `i.ytimg.com` thumbnails. Actual thumbnail rendering therefore remains outside the confirmed visual checks. Authenticated production preference writes and cross-device persistence have not yet been checked end to end; passing local tests and verifying deployed source do not establish that result. No site security rules were weakened for testing.
