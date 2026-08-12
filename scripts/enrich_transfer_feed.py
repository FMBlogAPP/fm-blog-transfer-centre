#!/usr/bin/env python3
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TRANSFER_FILE = DATA / "transfers.json"
FIRST_SEEN_FILE = DATA / "first_seen.json"
FEED_FILE = DATA / "feed.json"
CONFIG_FILE = ROOT / "config.json"


def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def movement_class(type_text):
    text = norm(type_text)
    if "loan" in text:
        return "loan"
    if "free" in text:
        return "free"
    if "return" in text:
        return "return"
    return "permanent"


def route_key(item):
    return "|".join([
        str(item.get("player_id") or ""),
        str(item.get("from_id") or ""),
        str(item.get("to_id") or ""),
        movement_class(item.get("type")),
    ])


def fallback_seen_at(item):
    date_value = item.get("date")
    if date_value and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date_value)):
        return f"{date_value}T12:00:00+00:00"
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def unique_rows(rows):
    seen = set()
    out = []
    for item in rows:
        key = item.get("id") or route_key(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


data = load(TRANSFER_FILE, {"meta": {}, "transfers": []})
config = load(CONFIG_FILE, {})
seen_db = load(FIRST_SEEN_FILE, {"version": 1, "initialised_at": None, "items": {}})
seen_items = seen_db.setdefault("items", {})
rows = [dict(x) for x in data.get("transfers", []) if not x.get("demo")]
now = datetime.now(timezone.utc)
is_initial_seed = not seen_db.get("initialised_at")

for item in rows:
    key = route_key(item)
    seen_at = seen_items.get(key)
    if not seen_at:
        seen_at = fallback_seen_at(item) if is_initial_seed else now.isoformat()
        seen_items[key] = seen_at
    item["first_seen_at"] = seen_at

data["transfers"] = rows
meta = data.setdefault("meta", {})
meta["first_seen_tracking"] = True
meta["feed_updated_at"] = now.isoformat()

if is_initial_seed:
    seen_db["initialised_at"] = now.isoformat()
seen_db["updated_at"] = now.isoformat()

cutoff_24h = now - timedelta(hours=24)
cutoff_7d = now - timedelta(days=7)

def seen_after(item, cutoff):
    stamp = parse_iso(item.get("first_seen_at"))
    return bool(stamp and stamp >= cutoff)

latest_by_date = sorted(
    rows,
    key=lambda x: (x.get("date") or "", x.get("id") or ""),
    reverse=True,
)[:300]
recent_seen = sorted(
    [x for x in rows if seen_after(x, cutoff_7d)],
    key=lambda x: x.get("first_seen_at") or "",
    reverse=True,
)[:700]
feed_rows = unique_rows(latest_by_date + recent_seen)
feed_rows.sort(key=lambda x: (x.get("date") or "", x.get("id") or ""), reverse=True)

last24 = [x for x in rows if seen_after(x, cutoff_24h)]
clubs = {
    club_id
    for item in rows
    for club_id in (item.get("from_id"), item.get("to_id"))
    if club_id
}

feed = {
    "meta": dict(meta),
    "stats": {
        "total": len(rows),
        "last24": len(last24),
        "free24": sum(1 for x in last24 if movement_class(x.get("type")) == "free"),
        "loans24": sum(1 for x in last24 if movement_class(x.get("type")) == "loan"),
        "clubs_involved": len(clubs),
        "tracked_leagues": len(config.get("leagues", [])),
        "feed_records": len(feed_rows),
    },
    "transfers": feed_rows,
}

save(TRANSFER_FILE, data)
save(FIRST_SEEN_FILE, seen_db)
save(FEED_FILE, feed)

print(
    f"V2 feed built. Full database: {len(rows)}; fast feed: {len(feed_rows)}; "
    f"new in last 24h: {len(last24)}; initial seed: {is_initial_seed}"
)
