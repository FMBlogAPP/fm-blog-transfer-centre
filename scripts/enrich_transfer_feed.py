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
HUB_FILE = DATA / "hub_profiles.json"
TEAMS_FILE = DATA / "teams.json"
PLAYERS_FILE = DATA / "players.json"
PLAYER_DETAILS_FILE = DATA / "player_details.json"
CLUB_DETAILS_FILE = DATA / "club_details.json"
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


def looks_like_player_endpoint(endpoint_name, player_name):
    endpoint = norm(endpoint_name)
    player = norm(player_name)
    if not endpoint:
        return True
    if endpoint in {"unknown", "free agent", "without club", "released", "no club"}:
        return True
    if not player:
        return False
    if endpoint == player:
        return True
    player_tokens = [x for x in player.split() if len(x) > 1]
    endpoint_tokens = [x for x in endpoint.split() if len(x) > 1]
    return bool(endpoint_tokens and all(x in player_tokens for x in endpoint_tokens))


def normalise_free_agent_endpoints(item):
    if movement_class(item.get("type")) != "free":
        return 0

    player_name = item.get("player_full_name") or item.get("player") or ""
    changed = 0
    for side, other in (("from", "to"), ("to", "from")):
        team_id = item.get(f"{side}_id")
        logo = item.get(f"{side}_logo")
        name = item.get(side)
        other_id = item.get(f"{other}_id")
        if team_id:
            continue
        if logo:
            continue
        if not other_id and not looks_like_player_endpoint(name, player_name):
            continue

        item[side] = "Free agent"
        item[f"{side}_logo"] = ""
        item[f"{side}_free_agent"] = True
        item[f"{side}_country"] = ""
        item[f"{side}_league"] = ""
        item[f"{side}_league_id"] = None
        item[f"{side}_region"] = ""
        changed += 1
    return changed


def add_player_meta(item, players_db):
    profile = players_db.get(str(item.get("player_id") or "")) or {}
    if not profile:
        return False

    profile_name = str(profile.get("full_name") or profile.get("name") or "").strip()
    transfer_name = str(item.get("player") or "").strip()
    if profile_name:
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


def player_summary(player_id, profile, extra=None):
    profile = profile or {}
    extra = extra or {}
    birth = profile.get("birth") if isinstance(profile.get("birth"), dict) else {}
    return {
        "id": int(player_id) if str(player_id).isdigit() else player_id,
        "name": profile.get("full_name") or profile.get("name") or "",
        "firstname": profile.get("firstname") or "",
        "lastname": profile.get("lastname") or "",
        "age": profile.get("age"),
        "birth": birth,
        "nationality": profile.get("nationality") or "",
        "height": profile.get("height") or "",
        "weight": profile.get("weight") or "",
        "number": profile.get("number"),
        "position": profile.get("position") or "",
        "photo": profile.get("photo") or "",
        "team_id": profile.get("team_id"),
        "statistics": extra.get("statistics") or [],
        "career": extra.get("career") or [],
        "trophies": extra.get("trophies") or [],
        "sidelined": extra.get("sidelined") or [],
        "details_updated_at": extra.get("updated_at") or "",
    }


def build_hub_payload(rows, team_index, players_db, player_details, club_details, now):
    transfer_player_ids = {
        str(item.get("player_id"))
        for item in rows
        if item.get("player_id")
    }

    players = {}
    squads = {}
    for pid, profile in players_db.items():
        if not isinstance(profile, dict):
            continue
        extra = player_details.get(str(pid), {}) if isinstance(player_details, dict) else {}
        summary = player_summary(pid, profile, extra)
        if str(pid) in transfer_player_ids:
            players[str(pid)] = summary

        team_id = profile.get("team_id")
        if team_id:
            squads.setdefault(str(team_id), []).append({
                "id": summary["id"],
                "name": summary["name"],
                "age": summary["age"],
                "number": summary["number"],
                "position": summary["position"],
                "photo": summary["photo"],
                "nationality": summary["nationality"],
            })

    position_order = {"Goalkeeper": 0, "Defender": 1, "Midfielder": 2, "Attacker": 3}
    for team_id, squad in squads.items():
        squad.sort(key=lambda p: (
            position_order.get(p.get("position"), 9),
            999 if p.get("number") is None else int(p.get("number")),
            p.get("name") or "",
        ))

    clubs = {}
    for team_id, meta in team_index.items():
        item = dict(meta)
        extra = club_details.get(str(team_id), {}) if isinstance(club_details, dict) else {}
        if extra:
            item.update(extra)
        item["squad_count"] = len(squads.get(str(team_id), []))
        clubs[str(team_id)] = item

    return {
        "meta": {
            "updated_at": now.isoformat(),
            "players": len(players),
            "squad_teams": len(squads),
            "clubs": len(clubs),
        },
        "players": players,
        "squads": squads,
        "clubs": clubs,
    }


def age_at_most(item, limit):
    try:
        return int(item.get("age")) <= limit
    except (TypeError, ValueError):
        return False


data = load(TRANSFER_FILE, {"meta": {}, "transfers": []})
config = load(CONFIG_FILE, {})
teams_db = load(TEAMS_FILE, {"leagues": {}})
players_db = load(PLAYERS_FILE, {})
player_details = load(PLAYER_DETAILS_FILE, {})
club_details = load(CLUB_DETAILS_FILE, {})
team_index = build_team_index(teams_db)
seen_db = load(FIRST_SEEN_FILE, {"version": 1, "initialised_at": None, "items": {}})
seen_items = seen_db.setdefault("items", {})
rows = [dict(x) for x in data.get("transfers", []) if not x.get("demo")]
now = datetime.now(timezone.utc)
is_initial_seed = not seen_db.get("initialised_at")
profiled_rows = 0
name_upgrades = []
free_agent_fixes = 0

for item in rows:
    old_name = str(item.get("player") or "").strip()
    if add_player_meta(item, players_db):
        profiled_rows += 1
    full_name = str(item.get("player_full_name") or "").strip()
    if full_name and old_name and full_name != old_name and len(name_upgrades) < 12:
        name_upgrades.append((old_name, full_name))

    free_agent_fixes += normalise_free_agent_endpoints(item)
    add_endpoint_meta(item, team_index)

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
meta["free_agent_normalisation"] = True
meta["free_agent_endpoints_fixed_last_build"] = free_agent_fixes
meta["hub_profiles"] = True
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

hub = build_hub_payload(rows, team_index, players_db, player_details, club_details, now)

save(TRANSFER_FILE, data)
save(FIRST_SEEN_FILE, seen_db)
save(FEED_FILE, feed)
save(HUB_FILE, hub)

print(
    f"Product feed built. Full database: {len(rows)}; fast feed: {len(feed_rows)}; "
    f"new in last 24h: {len(last24)}; player profiles: {len(players_db)}; "
    f"profiled rows: {profiled_rows}; U21 moves: {len(u21)}; initial seed: {is_initial_seed}; "
    f"free-agent endpoints fixed: {free_agent_fixes}; squad teams: {hub['meta']['squad_teams']}"
)
if name_upgrades:
    print("Player display-name upgrades (sample):")
    for short_name, full_name in name_upgrades:
        print(f"  {short_name} -> {full_name}")
else:
    print("No differing player display names found in the current profile cache.")
