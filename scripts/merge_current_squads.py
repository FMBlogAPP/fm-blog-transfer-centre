#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HUB_FILE = DATA / "hub_profiles.json"
SQUADS_FILE = DATA / "squads.json"
PLAYERS_FILE = DATA / "players.json"


def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


hub = load(HUB_FILE, {})
squad_doc = load(SQUADS_FILE, {"teams": {}})
players_db = load(PLAYERS_FILE, {})
teams = squad_doc.get("teams") or {}

if not hub or not teams:
    print("No authoritative squad snapshots available yet; leaving existing hub squads unchanged.")
    raise SystemExit(0)

position_order = {"Goalkeeper": 0, "Defender": 1, "Midfielder": 2, "Attacker": 3}
merged = {}

for team_id, snapshot in teams.items():
    roster = []
    for raw in (snapshot or {}).get("players") or []:
        player = dict(raw)
        pid = str(player.get("id") or "")
        cached = players_db.get(pid) or {}
        if cached.get("full_name"):
            player["name"] = cached.get("full_name")
        elif cached.get("name") and not player.get("name"):
            player["name"] = cached.get("name")
        if cached.get("nationality"):
            player["nationality"] = cached.get("nationality")
        if cached.get("photo") and not player.get("photo"):
            player["photo"] = cached.get("photo")
        roster.append(player)

    roster.sort(key=lambda p: (
        position_order.get(p.get("position"), 9),
        999 if p.get("number") is None else int(p.get("number")),
        p.get("name") or "",
    ))
    merged[str(team_id)] = roster

hub["squads"] = merged
for team_id, club in (hub.get("clubs") or {}).items():
    if isinstance(club, dict):
        club["squad_count"] = len(merged.get(str(team_id), []))

meta = hub.setdefault("meta", {})
meta["current_squads_source"] = "API-Football /players/squads snapshots"
meta["squad_snapshot_updated_at"] = squad_doc.get("updated_at")
meta["squad_teams"] = len(merged)

save(HUB_FILE, hub)
print(f"Merged authoritative current squads into hub cache: {len(merged)} clubs.")
