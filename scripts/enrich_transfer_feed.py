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
TEAMS_FILE = DATA / "teams.json"
PLAYERS_FILE = DATA / "players.json"
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


def build_team_index(teams_db):
    result = {}
    for clubs in (teams_db.get("leagues") or {}).values():
        for club in clubs or []:
            if club.get("id"):
                result[str(club["id"])] = club
    return result


def add_endpoint_meta(item, team_index):
    for side in ("from", "to"):
        team_id = item.get(f"{side}_id")
        meta = team_index.get(str(team_id)) if team_id else None
        if not meta:
            continue
        item[f"{side}_country"] = meta.get("country") or ""
        item[f"{side}_league"] = meta.get("league") or ""
        item[f"{side}_league_id"] = meta.get("league_id")
        item[f"{side}_region"] = meta.get("region") or ""


def add_player_meta(item, players_db):
    profile = players_db.get(str(item.get("player_id") or "")) or {}
    if not profile:
        return False

    profile_name = str(profile.get("name") or "").strip()
    transfer_name = str(item.get("player") or "").strip()
    if profile_name:
        # Keep the raw transfer-endpoint label in `player`, but expose the
        # squad-profile name separately. The frontend can prefer this richer
        # value without breaking route IDs or old records.
        item["player_full_name"] = profile_name
    elif transfer_name:
        item["player_full_name"] = transfer_name

    if profile.get("age") is not None:
        item["age"] = profile.get("age")
    if profile.get("position"):
        item["position"] = profile.get("position")
    if profile.get("photo"):
        item["player_photo"] = profile.get("photo")
    return bool(
        item.get("age") is not None
        or item.get("position")
        or item.get("player_full_name")
    )


def age_at_most(item, limit):
    try:
        return int(item.get("age")) <= limit
    except (TypeError, ValueError):
        return False


data = load(TRANSFER_FILE, {"meta": {}, "transfers": []})
config = load(CONFIG_FILE, {})
teams_db = load(TEAMS_FILE, {"leagues": {}})
players_db = load(PLAYERS_FILE, {})
team_index = build_team_index(teams_db)
seen_db = load(FIRST_SEEN_FILE, {"version": 1, "initialised_at": None, "items": {}})
seen_items = seen_db.setdefault("items", {})
rows = [dict(x) for x in data.get("transfers", []) if not x.get("demo")]
now = datetime.now(timezone.utc)
is_initial_seed = not seen_db.get("initialised_at")
profiled_rows = 0
name_upgrades = []

for item in rows:
    add_endpoint_meta(item, team_index)
    old_name = str(item.get("player") or "").strip()
    if add_player_meta(item, players_db):
        profiled_rows += 1
    full_name = str(item.get("player_full_name") or "").strip()
    if full_name and old_name and full_name != old_name and len(name_upgrades) < 12:
        name_upgrades.append((old_name, full_name))
    key = route_key(item)
    seen_at = seen_items.get(key)
    if not seen_at:
        seen_at = fallback_seen_at(item) if is_initial_seed else now.isoformat()
        seen_items[key] = seen_at
    item["first_seen_at"] = seen_at

data["transfers"] = rows
meta = data.setdefault("meta", {})
meta["first_seen_tracking"] = True
meta["endpoint_metadata"] = True
meta["player_profiles"] = len(players_db)
meta["profiled_transfer_rows"] = profiled_rows
meta["player_display_names"] = True
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
young_recent = sorted(
    [x for x in rows if age_at_most(x, 23)],
    key=lambda x: (x.get("date") or "", -(int(x.get("age") or 99))),
    reverse=True,
)[:250]
feed_rows = unique_rows(latest_by_date + recent_seen + young_recent)
feed_rows.sort(key=lambda x: (x.get("date") or "", x.get("id") or ""), reverse=True)

last24 = [x for x in rows if seen_after(x, cutoff_24h)]
clubs = {
    club_id
    for item in rows
    for club_id in (item.get("from_id"), item.get("to_id"))
    if club_id
}
u21 = [x for x in rows if age_at_most(x, 21)]
u23 = [x for x in rows if age_at_most(x, 23)]
free_u23 = [x for x in u23 if movement_class(x.get("type")) == "free"]

feed = {
    "meta": dict(meta),
    "stats": {
        "total": len(rows),
        "last24": len(last24),
        "free24": sum(1 for x in last24 if movement_class(x.get("type")) == "free"),
        "loans24": sum(1 for x in last24 if movement_class(x.get("type")) == "loan"),
        "clubs_involved": len(clubs),
        "tracked_leagues": len(config.get("leagues", [])),
        "player_profiles": len(players_db),
        "profiled_rows": profiled_rows,
        "u21": len(u21),
        "u23": len(u23),
        "free_u23": len(free_u23),
        "feed_records": len(feed_rows),
    },
    "transfers": feed_rows,
}

save(TRANSFER_FILE, data)
save(FIRST_SEEN_FILE, seen_db)
save(FEED_FILE, feed)

print(
    f"Product feed built. Full database: {len(rows)}; fast feed: {len(feed_rows)}; "
    f"new in last 24h: {len(last24)}; player profiles: {len(players_db)}; "
    f"profiled rows: {profiled_rows}; U21 moves: {len(u21)}; initial seed: {is_initial_seed}"
)
if name_upgrades:
    print("Player display-name upgrades (sample):")
    for short_name, full_name in name_upgrades:
        print(f"  {short_name} -> {full_name}")
else:
    print("No differing player display names found in the current profile cache.")
