-- Additive migration. Run once against the existing Worker DB binding before deploying the module.
CREATE TABLE IF NOT EXISTS fmb_tv_preferences_v1 (
  uid TEXT PRIMARY KEY NOT NULL CHECK(length(uid) BETWEEN 1 AND 128),
  version INTEGER NOT NULL CHECK(version >= 1),
  state_json TEXT NOT NULL CHECK(length(state_json) <= 65536),
  updated_at INTEGER NOT NULL
);
