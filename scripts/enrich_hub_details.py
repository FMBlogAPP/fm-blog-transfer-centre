#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://v3.football.api-sports.io"
TRANSFERS_FILE = DATA / "transfers.json"
TEAMS_FILE = DATA / "teams.json"
PLAYER_DETAILS_FILE = DATA / "player_details.json"
CLUB_DETAILS_FILE = DATA / "club_details.json"
STATE_FILE = DATA / "state.json"
CONFIG_FILE = ROOT / "config.json"


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


def stale(record, days):
    stamp = parse_iso((record or {}).get("updated_at"))
    return not stamp or datetime.now(timezone.utc) - stamp >= timedelta(days=days)


KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
if not KEY:
    print("API_FOOTBALL_KEY is missing.", file=sys.stderr)
    sys.exit(2)

config = load(CONFIG_FILE, {})
season = int(config.get("season", 2026))
call_gap = float(os.getenv("HUB_CALL_GAP", config.get("seconds_between_calls", 0.4)))
max_calls = int(os.getenv("HUB_MAX_CALLS", "240"))
max_players = int(os.getenv("HUB_MAX_PLAYERS", "40"))
max_clubs = int(os.getenv("HUB_MAX_CLUBS", "20"))
refresh_days = int(os.getenv("HUB_REFRESH_DAYS", "7"))
now = datetime.now(timezone.utc)

transfers_doc = load(TRANSFERS_FILE, {"transfers": []})
teams_db = load(TEAMS_FILE, {"leagues": {}})
player_details = load(PLAYER_DETAILS_FILE, {})
club_details = load(CLUB_DETAILS_FILE, {})
state = load(STATE_FILE, {})
rows = [x for x in transfers_doc.get("transfers", []) if not x.get("demo")]

calls = 0
errors = 0
last_call_at = 0.0


def api(path, **params):
    global calls, errors, last_call_at
    if calls >= max_calls:
        return None
    if last_call_at:
        wait = call_gap - (time.monotonic() - last_call_at)
        if wait > 0:
            time.sleep(wait)
    qs = urlencode({k: v for k, v in params.items() if v is not None})
    req = Request(
        f"{BASE}/{path}?{qs}",
        headers={"x-apisports-key": KEY, "User-Agent": "FM-Blog-Transfer-Centre/4.4"},
    )
    calls += 1
    try:
        with urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        errors += 1
        body = exc.read().decode("utf-8", "ignore")[:300]
        print(f"HTTP {exc.code} for {path}: {body}", file=sys.stderr)
        return None
    except (URLError, TimeoutError) as exc:
        errors += 1
        print(f"Request failed for {path}: {exc}", file=sys.stderr)
        return None
    finally:
        last_call_at = time.monotonic()

    if payload.get("errors"):
        errors += 1
        print(f"API error for {path}: {payload.get('errors')}", file=sys.stderr)
        return None
    return payload.get("response")


# Newest transfer players first so the most visible player hubs fill in quickly.
player_latest = {}
for item in rows:
    pid = item.get("player_id")
    if not pid:
        continue
    key = str(pid)
    date = str(item.get("date") or "")
    if key not in player_latest or date > player_latest[key]:
        player_latest[key] = date

player_targets = [
    pid for pid, _ in sorted(player_latest.items(), key=lambda kv: kv[1], reverse=True)
    if stale(player_details.get(pid), refresh_days)
][:max_players]

players_done = 0
for pid in player_targets:
    if calls >= max_calls:
        break
    current = dict(player_details.get(pid, {}))

    season_rows = api("players", id=pid, season=season)
    if isinstance(season_rows, list) and season_rows:
        first = season_rows[0] or {}
        if first.get("player"):
            current["profile"] = first.get("player")
        current["statistics"] = first.get("statistics") or []

    if calls < max_calls:
        career = api("players/teams", player=pid)
        if isinstance(career, list):
            current["career"] = career

    if calls < max_calls:
        trophies = api("trophies", player=pid)
        if isinstance(trophies, list):
            current["trophies"] = trophies

    if calls < max_calls:
        sidelined = api("sidelined", player=pid)
        if isinstance(sidelined, list):
            current["sidelined"] = sidelined

    current["updated_at"] = now.isoformat()
    player_details[pid] = current
    players_done += 1


# Build a current tracked-club index with league context.
clubs = {}
for league_id, league_clubs in (teams_db.get("leagues") or {}).items():
    for club in league_clubs or []:
        team_id = club.get("id")
        if not team_id:
            continue
        item = dict(club)
        item["league_id"] = item.get("league_id") or int(league_id)
        clubs[str(team_id)] = item

# Prioritise clubs appearing in the newest transfers, then fill from the catalogue.
club_latest = {}
for item in rows:
    date = str(item.get("date") or "")
    for key in ("from_id", "to_id"):
        team_id = item.get(key)
        if not team_id or str(team_id) not in clubs:
            continue
        tid = str(team_id)
        if tid not in club_latest or date > club_latest[tid]:
            club_latest[tid] = date

ordered_clubs = [x[0] for x in sorted(club_latest.items(), key=lambda kv: kv[1], reverse=True)]
ordered_clubs.extend(tid for tid in clubs if tid not in club_latest)
club_targets = [tid for tid in ordered_clubs if stale(club_details.get(tid), refresh_days)][:max_clubs]

clubs_done = 0
for tid in club_targets:
    if calls >= max_calls:
        break
    meta = clubs.get(tid) or {}
    current = dict(club_details.get(tid, {}))

    team_rows = api("teams", id=tid)
    if isinstance(team_rows, list) and team_rows:
        first = team_rows[0] or {}
        current["team"] = first.get("team") or {}
        current["venue"] = first.get("venue") or {}

    if calls < max_calls:
        coaches = api("coachs", team=tid)
        if isinstance(coaches, list):
            current["coaches"] = coaches

    if calls < max_calls and meta.get("league_id"):
        statistics = api(
            "teams/statistics",
            league=meta.get("league_id"),
            season=season,
            team=tid,
        )
        if isinstance(statistics, dict):
            current["statistics"] = statistics

    current["updated_at"] = now.isoformat()
    club_details[tid] = current
    clubs_done += 1

state["hub_enrichment_at"] = now.isoformat()
state["hub_calls_last_run"] = calls
state["hub_errors_last_run"] = errors
state["player_hubs_detailed"] = len(player_details)
state["club_hubs_detailed"] = len(club_details)

save(PLAYER_DETAILS_FILE, player_details)
save(CLUB_DETAILS_FILE, club_details)
save(STATE_FILE, state)

print(
    f"Hub enrichment complete. Calls: {calls}; players updated: {players_done}; "
    f"clubs updated: {clubs_done}; player hubs cached: {len(player_details)}; "
    f"club hubs cached: {len(club_details)}; errors: {errors}."
)
