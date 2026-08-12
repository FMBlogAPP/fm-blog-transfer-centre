#!/usr/bin/env python3
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://v3.football.api-sports.io"

def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
if not KEY:
    print("API_FOOTBALL_KEY is missing. Add it as a GitHub Actions repository secret.", file=sys.stderr)
    sys.exit(2)

config = load(ROOT / "config.json", {})
teams_db = load(DATA / "teams.json", {"season": config.get("season"), "leagues": {}})
players_db = load(DATA / "players.json", {})
state = load(DATA / "state.json", {"team_cursor":0, "league_cursor":0, "last_run":None, "calls_last_run":0})
transfer_db = load(DATA / "transfers.json", {"meta":{}, "transfers":[]})
calls = 0

def api(path, **params):
    global calls
    qs = urlencode({k:v for k,v in params.items() if v is not None})
    req = Request(f"{BASE}/{path}?{qs}", headers={"x-apisports-key": KEY, "User-Agent":"FM-Blog-Transfer-Centre/1.0"})
    calls += 1
    try:
        with urlopen(req, timeout=25) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        print(f"HTTP {e.code} for {path}: {e.read().decode('utf-8', 'ignore')[:500]}", file=sys.stderr)
        return []
    except (URLError, TimeoutError) as e:
        print(f"Request failed for {path}: {e}", file=sys.stderr)
        return []
    errors = payload.get("errors")
    if errors:
        print(f"API error for {path}: {errors}", file=sys.stderr)
    return payload.get("response") or []

def discover_leagues():
    leagues = config.get("leagues", [])
    if not leagues:
        return
    count = min(config.get("league_discoveries_per_run", 1), len(leagues))
    cursor = int(state.get("league_cursor", 0))
    for _ in range(count):
        league = leagues[cursor % len(leagues)]
        key = str(league["id"])
        current = teams_db.get("leagues", {}).get(key)
        if not current or teams_db.get("season") != config.get("season"):
            rows = api("teams", league=league["id"], season=config["season"])
            club_rows = []
            for row in rows:
                t = row.get("team") or {}
                if t.get("id"):
                    club_rows.append({"id": t["id"], "name": t.get("name", ""), "logo": t.get("logo", ""), "league_id": league["id"], "league": league["name"], "country": league.get("country", ""), "priority": league.get("priority", 2)})
            if club_rows:
                teams_db.setdefault("leagues", {})[key] = club_rows
                teams_db["season"] = config["season"]
                print(f"Discovered {len(club_rows)} clubs in {league['name']}.")
        cursor += 1
    state["league_cursor"] = cursor % len(leagues)

def all_teams():
    leagues = {str(x["id"]): x for x in config.get("leagues", [])}
    rows = []
    for league_id, clubs in teams_db.get("leagues", {}).items():
        if league_id in leagues:
            rows.extend(clubs)
    return sorted(rows, key=lambda x: (x.get("priority",2), x.get("league",""), x.get("name","")))

def numeric_fee(text):
    if not text:
        return 0.0
    s = str(text).upper().replace(",", ".")
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*([MKB])?', s)
    if not m:
        return 0.0
    n = float(m.group(1)); unit = m.group(2)
    if unit == "M": return n
    if unit == "K": return n / 1000.0
    if unit == "B": return n * 1000.0
    return n / 1_000_000.0 if n > 10000 else n

def relevance(age, type_text):
    fee = numeric_fee(type_text)
    if age is not None and age <= 21: return 5
    if fee >= 50: return 5
    if fee >= 25: return 4
    if fee >= 10: return 3
    return 2

def transfer_key(player_id, tr):
    teams = tr.get("teams") or {}
    tin = teams.get("in") or {}; tout = teams.get("out") or {}
    return f"{player_id}|{tr.get('date','')}|{tout.get('id','')}|{tin.get('id','')}|{tr.get('type','')}"

def within_window(d):
    start = config.get("window_start"); end = config.get("window_end")
    if not d: return False
    return (not start or d >= start) and (not end or d <= end)

def fetch_transfers_for_team(team):
    out = []
    rows = api("transfers", team=team["id"])
    for item in rows:
        player = item.get("player") or {}
        pid = player.get("id")
        if not pid: continue
        profile = players_db.get(str(pid), {})
        for tr in item.get("transfers") or []:
            if not within_window(tr.get("date")):
                continue
            sides = tr.get("teams") or {}
            tin = sides.get("in") or {}; tout = sides.get("out") or {}
            if team["id"] not in (tin.get("id"), tout.get("id")):
                continue
            age = profile.get("age")
            out.append({"id": transfer_key(pid, tr), "player_id": pid, "player": player.get("name") or "Unknown player", "player_photo": profile.get("photo") or f"https://media.api-sports.io/football/players/{pid}.png", "date": tr.get("date"), "type": tr.get("type") or "Undisclosed", "from_id": tout.get("id"), "from": tout.get("name") or "Unknown", "from_logo": tout.get("logo") or "", "to_id": tin.get("id"), "to": tin.get("name") or "Unknown", "to_logo": tin.get("logo") or "", "league": team.get("league", ""), "country": team.get("country", ""), "age": age, "position": profile.get("position"), "fm_relevance": relevance(age, tr.get("type")), "demo": False})
    return out

def merge_records(new):
    current = {x.get("id"):x for x in transfer_db.get("transfers", []) if x.get("id") and not x.get("demo")}
    for x in new:
        current[x["id"]] = {**current.get(x["id"], {}), **x}
    rows = list(current.values())
    rows.sort(key=lambda x: (x.get("date") or "", x.get("id") or ""), reverse=True)
    transfer_db["transfers"] = rows[:int(config.get("max_records", 4000))]
    transfer_db["meta"] = {"updated_at": datetime.now(timezone.utc).isoformat(), "source": "API-Football", "live": True, "clubs_known": len(all_teams()), "calls_last_run": calls}

discover_leagues()
teams = all_teams(); new = []
if teams:
    n = min(int(config.get("teams_per_run", 22)), len(teams))
    cursor = int(state.get("team_cursor",0))
    selected = [teams[(cursor+i) % len(teams)] for i in range(n)]
    for idx, team in enumerate(selected, 1):
        print(f"[{idx}/{n}] {team['league']} - {team['name']}")
        new.extend(fetch_transfers_for_team(team))
        time.sleep(0.12)
    state["team_cursor"] = (cursor+n) % len(teams)
else:
    print("No club list yet. This run only performed league discovery.")

merge_records(new)
state["last_run"] = datetime.now(timezone.utc).isoformat()
state["calls_last_run"] = calls
save(DATA/"teams.json", teams_db)
save(DATA/"players.json", players_db)
save(DATA/"transfers.json", transfer_db)
save(DATA/"state.json", state)
print(f"Done. API calls: {calls}; stored transfers: {len(transfer_db.get('transfers',[]))}")
