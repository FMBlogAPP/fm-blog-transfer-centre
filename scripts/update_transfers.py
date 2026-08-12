#!/usr/bin/env python3
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
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
discovery_season = int(config.get("team_discovery_season", 2024))
call_gap = float(config.get("seconds_between_calls", 7.0))
max_calls = int(config.get("max_calls_per_run", 20))
teams_db = load(DATA / "teams.json", {"season": discovery_season, "leagues": {}})
players_db = load(DATA / "players.json", {})
state = load(DATA / "state.json", {})
transfer_db = load(DATA / "transfers.json", {"meta": {}, "transfers": []})
league_ids = load(DATA / "league_ids.json", {})

state.setdefault("league_cursor", 0)
state.setdefault("team_cursor", 0)
state.setdefault("team_cursors", {"1": 0, "2": 0, "3": 0})
state.setdefault("last_run", None)
state.setdefault("calls_last_run", 0)

calls = 0
last_call_at = 0.0


def api(path, **params):
    global calls, last_call_at
    if calls >= max_calls:
        print(f"Call budget reached ({max_calls}); skipping {path}.")
        return []
    if last_call_at:
        wait = call_gap - (time.monotonic() - last_call_at)
        if wait > 0:
            time.sleep(wait)
    qs = urlencode({k: v for k, v in params.items() if v is not None})
    req = Request(
        f"{BASE}/{path}?{qs}",
        headers={"x-apisports-key": KEY, "User-Agent": "FM-Blog-Transfer-Centre/2.0"},
    )
    calls += 1
    try:
        with urlopen(req, timeout=25) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:500]
        print(f"HTTP {e.code} for {path}: {body}", file=sys.stderr)
        payload = {"response": []}
    except (URLError, TimeoutError) as e:
        print(f"Request failed for {path}: {e}", file=sys.stderr)
        payload = {"response": []}
    finally:
        last_call_at = time.monotonic()

    errors = payload.get("errors")
    if errors:
        print(f"API error for {path}: {errors}", file=sys.stderr)
    return payload.get("response") or []


def norm(value):
    value = str(value or "").casefold()
    value = value.replace("ü", "u").replace("ö", "o").replace("ä", "a")
    value = value.replace("é", "e").replace("í", "i").replace("ó", "o").replace("á", "a")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def league_key(league):
    return f"{norm(league.get('country'))}|{norm(league.get('name'))}"


def resolved_league_id(league):
    if league.get("id"):
        return int(league["id"])
    cached = league_ids.get(league_key(league))
    return int(cached) if cached else None


def resolve_league_id(league):
    existing = resolved_league_id(league)
    if existing:
        return existing

    query = league.get("api_search") or league.get("name")
    country = league.get("country")
    rows = api("leagues", country=country, search=query)
    if not rows and calls < max_calls:
        rows = api("leagues", search=query)
    if not rows:
        print(f"Could not resolve league ID: {country} - {league.get('name')}")
        return None

    wanted_name = norm(query)
    wanted_country = norm(country)
    best = None
    best_score = -1.0
    for row in rows:
        info = row.get("league") or {}
        nation = row.get("country") or {}
        if info.get("type") and info.get("type") != "League":
            continue
        candidate_name = norm(info.get("name"))
        candidate_country = norm(nation.get("name"))
        score = 100 * SequenceMatcher(None, wanted_name, candidate_name).ratio()
        if wanted_country and candidate_country == wanted_country:
            score += 80
        if wanted_name == candidate_name:
            score += 50
        if score > best_score and info.get("id"):
            best_score = score
            best = int(info["id"])

    if best:
        league_ids[league_key(league)] = best
        print(f"Resolved {country} - {league.get('name')} to league ID {best}.")
    return best


def configured_leagues():
    rows = []
    for league in config.get("leagues", []):
        item = dict(league)
        item["resolved_id"] = resolved_league_id(league)
        item["display_country"] = league.get("display_country") or league.get("country")
        rows.append(item)
    return rows


def discover_leagues():
    leagues = config.get("leagues", [])
    if not leagues:
        return

    target = int(config.get("league_discoveries_per_run", 2))
    cursor = int(state.get("league_cursor", 0))
    completed = 0
    scanned = 0

    while completed < target and scanned < len(leagues) and calls < max_calls:
        league = leagues[cursor % len(leagues)]
        cursor = (cursor + 1) % len(leagues)
        scanned += 1
        lid = resolve_league_id(league)
        if not lid:
            completed += 1
            continue

        key = str(lid)
        current = teams_db.get("leagues", {}).get(key)
        if current and teams_db.get("season") == discovery_season:
            continue

        rows = api("teams", league=lid, season=discovery_season)
        club_rows = []
        for row in rows:
            t = row.get("team") or {}
            if t.get("id"):
                club_rows.append({
                    "id": t["id"],
                    "name": t.get("name", ""),
                    "logo": t.get("logo", ""),
                    "league_id": lid,
                    "league": league.get("name", ""),
                    "country": league.get("display_country") or league.get("country", ""),
                    "region": league.get("region", ""),
                    "priority": int(league.get("priority", 2)),
                })
        if club_rows:
            teams_db.setdefault("leagues", {})[key] = club_rows
            teams_db["season"] = discovery_season
            print(f"Discovered {len(club_rows)} clubs in {league.get('name')} ({league.get('country')}).")
        else:
            print(f"No teams returned for {league.get('country')} - {league.get('name')} in {discovery_season}.")
        completed += 1

    state["league_cursor"] = cursor


def all_teams():
    valid_ids = {str(x["resolved_id"]): x for x in configured_leagues() if x.get("resolved_id")}
    rows = []
    for lid, clubs in teams_db.get("leagues", {}).items():
        if lid not in valid_ids:
            continue
        league = valid_ids[lid]
        for club in clubs:
            item = dict(club)
            item["priority"] = int(league.get("priority", item.get("priority", 2)))
            item["league"] = league.get("name", item.get("league", ""))
            item["country"] = league.get("display_country", item.get("country", ""))
            item["region"] = league.get("region", item.get("region", ""))
            rows.append(item)
    return rows


def select_teams(teams):
    limit = min(int(config.get("teams_per_run", 16)), len(teams))
    if not limit:
        return []

    slots = config.get("priority_slots", {"1": 10, "2": 6, "3": 0})
    selected = []
    seen = set()
    cursors = state.setdefault("team_cursors", {"1": 0, "2": 0, "3": 0})

    for priority in (1, 2, 3):
        group = sorted(
            [t for t in teams if int(t.get("priority", 2)) == priority],
            key=lambda x: (x.get("country", ""), x.get("league", ""), x.get("name", "")),
        )
        if not group:
            continue
        want = min(int(slots.get(str(priority), 0)), len(group), limit - len(selected))
        cursor = int(cursors.get(str(priority), 0)) % len(group)
        taken = 0
        checked = 0
        while taken < want and checked < len(group):
            team = group[(cursor + checked) % len(group)]
            checked += 1
            if team.get("id") in seen:
                continue
            selected.append(team)
            seen.add(team.get("id"))
            taken += 1
        cursors[str(priority)] = (cursor + checked) % len(group)
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        rest = sorted(teams, key=lambda x: (int(x.get("priority", 2)), x.get("country", ""), x.get("name", "")))
        cursor = int(state.get("team_cursor", 0)) % len(rest)
        checked = 0
        while len(selected) < limit and checked < len(rest):
            team = rest[(cursor + checked) % len(rest)]
            checked += 1
            if team.get("id") in seen:
                continue
            selected.append(team)
            seen.add(team.get("id"))
        state["team_cursor"] = (cursor + checked) % len(rest)

    return selected


def transfer_key(player_id, tr):
    teams = tr.get("teams") or {}
    tin = teams.get("in") or {}
    tout = teams.get("out") or {}
    return f"{player_id}|{tr.get('date','')}|{tout.get('id','')}|{tin.get('id','')}|{tr.get('type','')}"


def within_window(d):
    start = config.get("window_start")
    end = config.get("window_end")
    if not d:
        return False
    return (not start or d >= start) and (not end or d <= end)


def team_meta_index():
    return {t.get("id"): t for t in all_teams() if t.get("id")}


def fetch_transfers_for_team(team, meta_index):
    out = []
    rows = api("transfers", team=team["id"])
    for item in rows:
        player = item.get("player") or {}
        pid = player.get("id")
        if not pid:
            continue
        profile = players_db.get(str(pid), {})
        for tr in item.get("transfers") or []:
            if not within_window(tr.get("date")):
                continue
            sides = tr.get("teams") or {}
            tin = sides.get("in") or {}
            tout = sides.get("out") or {}
            if team["id"] not in (tin.get("id"), tout.get("id")):
                continue

            destination_meta = meta_index.get(tin.get("id"))
            source_meta = meta_index.get(tout.get("id"))
            context = destination_meta or source_meta or team

            out.append({
                "id": transfer_key(pid, tr),
                "player_id": pid,
                "player": player.get("name") or "Unknown player",
                "player_photo": profile.get("photo") or f"https://media.api-sports.io/football/players/{pid}.png",
                "date": tr.get("date"),
                "type": tr.get("type") or "Undisclosed",
                "from_id": tout.get("id"),
                "from": tout.get("name") or "Unknown",
                "from_logo": tout.get("logo") or "",
                "to_id": tin.get("id"),
                "to": tin.get("name") or "Unknown",
                "to_logo": tin.get("logo") or "",
                "league": context.get("league", ""),
                "country": context.get("country", ""),
                "region": context.get("region", ""),
                "age": profile.get("age"),
                "position": profile.get("position"),
                "demo": False,
            })
    return out


def merge_records(new):
    current = {
        x.get("id"): x
        for x in transfer_db.get("transfers", [])
        if x.get("id") and not x.get("demo")
    }
    for item in new:
        current[item["id"]] = {**current.get(item["id"], {}), **item}
    rows = list(current.values())
    rows.sort(key=lambda x: (x.get("date") or "", x.get("id") or ""), reverse=True)
    transfer_db["transfers"] = rows[: int(config.get("max_records", 5000))]

    known = configured_leagues()
    active = sorted({x.get("league") for x in rows if x.get("league")})
    transfer_db["meta"] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "API-Football",
        "live": True,
        "clubs_known": len(all_teams()),
        "calls_last_run": calls,
        "team_discovery_season": discovery_season,
        "tracked_leagues": len(config.get("leagues", [])),
        "resolved_leagues": sum(1 for x in known if x.get("resolved_id")),
        "active_leagues": len(active),
    }


discover_leagues()
teams = all_teams()
selected = select_teams(teams)
meta_index = team_meta_index()
new = []

for idx, team in enumerate(selected, 1):
    if calls >= max_calls:
        break
    print(f"[{idx}/{len(selected)}] {team.get('country')} - {team.get('league')} - {team.get('name')}")
    new.extend(fetch_transfers_for_team(team, meta_index))

merge_records(new)
state["last_run"] = datetime.now(timezone.utc).isoformat()
state["calls_last_run"] = calls
save(DATA / "teams.json", teams_db)
save(DATA / "players.json", players_db)
save(DATA / "transfers.json", transfer_db)
save(DATA / "state.json", state)
save(DATA / "league_ids.json", league_ids)
print(f"Done. API calls: {calls}; stored transfers: {len(transfer_db.get('transfers', []))}; tracked leagues: {len(config.get('leagues', []))}")
