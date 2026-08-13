#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://v3.football.api-sports.io"
TEAMS_FILE = DATA / "teams.json"
PLAYERS_FILE = DATA / "players.json"
STATE_FILE = DATA / "state.json"


def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
if not KEY:
    print("API_FOOTBALL_KEY is missing.", file=sys.stderr)
    sys.exit(2)

teams_db = load(TEAMS_FILE, {"leagues": {}})
players_db = load(PLAYERS_FILE, {})
state = load(STATE_FILE, {})
now = datetime.now(timezone.utc)
refresh_hours = 168  # API-Football recommends about one squads call per team per week.
last_refresh = parse_iso(state.get("player_profiles_refreshed_at"))

if players_db and last_refresh and (now - last_refresh).total_seconds() < refresh_hours * 3600:
    age_hours = (now - last_refresh).total_seconds() / 3600
    print(f"Player profiles are fresh ({age_hours:.1f}h old); skipping squad refresh.")
    sys.exit(0)

team_ids = []
seen = set()
for clubs in (teams_db.get("leagues") or {}).values():
    for club in clubs or []:
        team_id = club.get("id")
        if team_id and team_id not in seen:
            seen.add(team_id)
            team_ids.append(team_id)

if not team_ids:
    print("No cached teams found; nothing to enrich.")
    sys.exit(0)

calls = 0
errors = 0
last_call_at = 0.0
call_gap = 0.4
max_calls = 650
updated_players = 0


def api(path, **params):
    global calls, errors, last_call_at
    if calls >= max_calls:
        return []
    if last_call_at:
        wait = call_gap - (time.monotonic() - last_call_at)
        if wait > 0:
            time.sleep(wait)
    qs = urlencode({k: v for k, v in params.items() if v is not None})
    req = Request(
        f"{BASE}/{path}?{qs}",
        headers={"x-apisports-key": KEY, "User-Agent": "FM-Blog-Transfer-Centre/3.0"},
    )
    calls += 1
    try:
        with urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")[:300]
        print(f"HTTP {exc.code} for {path}: {body}", file=sys.stderr)
        errors += 1
        payload = {"response": []}
    except (URLError, TimeoutError) as exc:
        print(f"Request failed for {path}: {exc}", file=sys.stderr)
        errors += 1
        payload = {"response": []}
    finally:
        last_call_at = time.monotonic()

    api_errors = payload.get("errors")
    if api_errors:
        errors += 1
        print(f"API error for {path}: {api_errors}", file=sys.stderr)
    return payload.get("response") or []


for index, team_id in enumerate(team_ids, 1):
    if calls >= max_calls:
        break
    print(f"[{index}/{len(team_ids)}] Refresh squad: team {team_id}")
    rows = api("players/squads", team=team_id)
    for row in rows:
        for player in (row.get("players") or []):
            player_id = player.get("id")
            if not player_id:
                continue
            current = dict(players_db.get(str(player_id), {}))
            current.update({
                "id": player_id,
                "name": player.get("name") or current.get("name") or "",
                "age": player.get("age") if player.get("age") is not None else current.get("age"),
                "number": player.get("number") if player.get("number") is not None else current.get("number"),
                "position": player.get("position") or current.get("position") or "",
                "photo": player.get("photo") or current.get("photo") or "",
                "team_id": team_id,
                "updated_at": now.isoformat(),
            })
            players_db[str(player_id)] = current
            updated_players += 1

state["player_profiles_refreshed_at"] = now.isoformat()
state["player_profile_calls_last_run"] = calls
state["player_profile_errors_last_run"] = errors
state["player_profiles_known"] = len(players_db)

save(PLAYERS_FILE, players_db)
save(STATE_FILE, state)
print(
    f"Player enrichment complete. Teams checked: {min(len(team_ids), calls)}; "
    f"API calls: {calls}; squad rows stored/updated: {updated_players}; "
    f"unique player profiles: {len(players_db)}; errors: {errors}."
)
