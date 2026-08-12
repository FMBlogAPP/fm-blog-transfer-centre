#!/usr/bin/env python3
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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


def norm(value):
    value = str(value or "").casefold()
    replacements = {
        "ü": "u", "ö": "o", "ä": "a", "é": "e", "í": "i",
        "ó": "o", "á": "a", "č": "c", "ć": "c", "š": "s",
        "ž": "z", "đ": "d", "ñ": "n",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def movement_class(type_text):
    text = norm(type_text)
    if "loan" in text:
        return "loan"
    if "free" in text:
        return "free"
    if "return" in text:
        return "return"
    return "permanent"


def type_quality(value):
    raw = str(value or "")
    text = norm(raw)
    if re.search(r"\d", raw) or any(symbol in raw for symbol in ("€", "£", "$")):
        return 5
    if "loan" in text or "free" in text:
        return 4
    if text not in ("", "transfer", "undisclosed", "n a", "na"):
        return 3
    if text == "transfer":
        return 2
    return 1


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def route_key(item):
    return (
        str(item.get("player_id") or ""),
        str(item.get("from_id") or ""),
        str(item.get("to_id") or ""),
        movement_class(item.get("type")),
    )


def event_id(item):
    return "|".join([
        str(item.get("player_id") or ""),
        str(item.get("date") or ""),
        str(item.get("from_id") or ""),
        str(item.get("to_id") or ""),
        movement_class(item.get("type")),
    ])


def merge_two(a, b):
    newer, older = (b, a) if (b.get("date") or "") >= (a.get("date") or "") else (a, b)
    out = dict(older)
    out.update({k: v for k, v in newer.items() if v not in (None, "")})
    out["date"] = max(a.get("date") or "", b.get("date") or "") or None
    if type_quality(b.get("type")) > type_quality(a.get("type")):
        out["type"] = b.get("type")
    else:
        out["type"] = a.get("type")
    out["type"] = out.get("type") or "Undisclosed"
    out["id"] = event_id(out)
    return out


def dedupe_records(rows, tolerance_days):
    groups = {}
    for raw in rows:
        if raw.get("demo") or not raw.get("player_id"):
            continue
        item = dict(raw)
        groups.setdefault(route_key(item), []).append(item)

    result = []
    removed = 0
    for group in groups.values():
        group.sort(key=lambda x: x.get("date") or "", reverse=True)
        kept = []
        for item in group:
            item_date = parse_date(item.get("date"))
            duplicate_at = None
            for idx, existing in enumerate(kept):
                existing_date = parse_date(existing.get("date"))
                if item_date and existing_date and abs((existing_date - item_date).days) <= tolerance_days:
                    duplicate_at = idx
                    break
                if not item_date and not existing_date:
                    duplicate_at = idx
                    break
            if duplicate_at is None:
                item["id"] = event_id(item)
                kept.append(item)
            else:
                kept[duplicate_at] = merge_two(kept[duplicate_at], item)
                removed += 1
        result.extend(kept)

    result.sort(key=lambda x: (x.get("date") or "", x.get("id") or ""), reverse=True)
    return result, removed


KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
if not KEY:
    print("API_FOOTBALL_KEY is missing. Add it as a GitHub Actions repository secret.", file=sys.stderr)
    sys.exit(2)

config = load(ROOT / "config.json", {})
discovery_season = int(config.get("team_discovery_season", config.get("season", 2026)))
call_gap = float(config.get("seconds_between_calls", 0.4))
max_calls = int(config.get("max_calls_per_run", 1200))
full_sweep = bool(config.get("full_sweep", False))
replace_on_full = bool(config.get("replace_on_complete_full_sweep", False))
dedupe_tolerance = int(config.get("dedupe_day_tolerance", 3))

teams_db = load(DATA / "teams.json", {"season": discovery_season, "leagues": {}})
players_db = load(DATA / "players.json", {})
state = load(DATA / "state.json", {})
transfer_db = load(DATA / "transfers.json", {"meta": {}, "transfers": []})
league_ids = load(DATA / "league_ids.json", {})

calls = 0
last_call_at = 0.0
quota_exhausted = False
api_errors = 0


def api(path, **params):
    global calls, last_call_at, quota_exhausted, api_errors
    if quota_exhausted or calls >= max_calls:
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
        body = exc.read().decode("utf-8", "ignore")[:500]
        print(f"HTTP {exc.code} for {path}: {body}", file=sys.stderr)
        if exc.code == 429:
            time.sleep(2)
        api_errors += 1
        payload = {"response": []}
    except (URLError, TimeoutError) as exc:
        print(f"Request failed for {path}: {exc}", file=sys.stderr)
        api_errors += 1
        payload = {"response": []}
    finally:
        last_call_at = time.monotonic()

    errors = payload.get("errors")
    if errors:
        api_errors += 1
        text = json.dumps(errors, ensure_ascii=False).casefold()
        print(f"API error for {path}: {errors}", file=sys.stderr)
        if "request limit" in text or "reached the request limit" in text:
            quota_exhausted = True
            print("Daily API quota exhausted; stopping this run early.", file=sys.stderr)
    return payload.get("response") or []


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
            score += 100
        if wanted_name == candidate_name:
            score += 60
        if score > best_score and info.get("id"):
            best_score = score
            best = int(info["id"])

    if best:
        league_ids[league_key(league)] = best
        print(f"Resolved {country} - {league.get('name')} to league ID {best}.")
    return best


def configured_leagues():
    result = []
    for league in config.get("leagues", []):
        item = dict(league)
        item["resolved_id"] = resolved_league_id(league)
        item["display_country"] = league.get("display_country") or league.get("country")
        result.append(item)
    return result


def discover_leagues():
    leagues = config.get("leagues", [])
    target = min(int(config.get("league_discoveries_per_run", len(leagues))), len(leagues))
    completed = 0

    if teams_db.get("season") != discovery_season:
        teams_db["season"] = discovery_season
        teams_db["leagues"] = {}

    for league in leagues:
        if completed >= target or quota_exhausted or calls >= max_calls:
            break
        lid = resolve_league_id(league)
        if not lid:
            completed += 1
            continue

        key = str(lid)
        current = teams_db.setdefault("leagues", {}).get(key)
        if current:
            continue

        rows = api("teams", league=lid, season=discovery_season)
        club_rows = []
        for row in rows:
            team = row.get("team") or {}
            if not team.get("id"):
                continue
            club_rows.append({
                "id": team["id"],
                "name": team.get("name", ""),
                "logo": team.get("logo", ""),
                "league_id": lid,
                "league": league.get("name", ""),
                "country": league.get("display_country") or league.get("country", ""),
                "region": league.get("region", ""),
                "priority": int(league.get("priority", 2)),
            })

        if club_rows:
            teams_db["leagues"][key] = club_rows
            print(f"Discovered {len(club_rows)} clubs in {league.get('name')} ({league.get('country')}) for {discovery_season}.")
        else:
            print(f"No teams returned for {league.get('country')} - {league.get('name')} in {discovery_season}.")
        completed += 1


def all_teams():
    valid = {str(x["resolved_id"]): x for x in configured_leagues() if x.get("resolved_id")}
    rows = []
    seen = set()
    for lid, clubs in teams_db.get("leagues", {}).items():
        if lid not in valid:
            continue
        league = valid[lid]
        for club in clubs:
            team_id = club.get("id")
            if not team_id or team_id in seen:
                continue
            seen.add(team_id)
            item = dict(club)
            item["priority"] = int(league.get("priority", item.get("priority", 2)))
            item["league"] = league.get("name", item.get("league", ""))
            item["country"] = league.get("display_country", item.get("country", ""))
            item["region"] = league.get("region", item.get("region", ""))
            rows.append(item)
    return sorted(rows, key=lambda x: (int(x.get("priority", 2)), x.get("country", ""), x.get("league", ""), x.get("name", "")))


def select_teams(teams):
    if full_sweep:
        return teams[: int(config.get("teams_per_run", 1000))]
    limit = min(int(config.get("teams_per_run", 100)), len(teams))
    cursor = int(state.get("team_cursor", 0)) % max(len(teams), 1)
    selected = [teams[(cursor + i) % len(teams)] for i in range(limit)] if teams else []
    if teams:
        state["team_cursor"] = (cursor + limit) % len(teams)
    return selected


def within_window(value):
    if not value:
        return False
    start = config.get("window_start")
    end = config.get("window_end")
    return (not start or value >= start) and (not end or value <= end)


def team_meta_index():
    return {team.get("id"): team for team in all_teams() if team.get("id")}


def fetch_transfers_for_team(team, meta_index):
    output = []
    rows = api("transfers", team=team["id"])
    for item in rows:
        player = item.get("player") or {}
        player_id = player.get("id")
        if not player_id:
            continue
        profile = players_db.get(str(player_id), {})
        for transfer in item.get("transfers") or []:
            date_value = transfer.get("date")
            if not within_window(date_value):
                continue

            sides = transfer.get("teams") or {}
            incoming = sides.get("in") or {}
            outgoing = sides.get("out") or {}
            if team["id"] not in (incoming.get("id"), outgoing.get("id")):
                continue

            destination_meta = meta_index.get(incoming.get("id"))
            source_meta = meta_index.get(outgoing.get("id"))
            context = destination_meta or source_meta or team

            record = {
                "player_id": player_id,
                "player": player.get("name") or "Unknown player",
                "player_photo": profile.get("photo") or f"https://media.api-sports.io/football/players/{player_id}.png",
                "date": date_value,
                "type": transfer.get("type") or "Undisclosed",
                "from_id": outgoing.get("id"),
                "from": outgoing.get("name") or "Unknown",
                "from_logo": outgoing.get("logo") or "",
                "to_id": incoming.get("id"),
                "to": incoming.get("name") or "Unknown",
                "to_logo": incoming.get("logo") or "",
                "league": context.get("league", ""),
                "country": context.get("country", ""),
                "region": context.get("region", ""),
                "age": profile.get("age"),
                "position": profile.get("position"),
                "demo": False,
            }
            record["id"] = event_id(record)
            output.append(record)
    return output


def merge_records(new_rows, selected_count, known_team_count):
    complete_full_sweep = (
        full_sweep
        and replace_on_full
        and selected_count == known_team_count
        and not quota_exhausted
    )

    if complete_full_sweep:
        combined = list(new_rows)
    else:
        combined = [x for x in transfer_db.get("transfers", []) if not x.get("demo")]
        combined.extend(new_rows)

    clean, removed = dedupe_records(combined, dedupe_tolerance)
    transfer_db["transfers"] = clean[: int(config.get("max_records", 12000))]

    known_leagues = configured_leagues()
    active = sorted({x.get("league") for x in transfer_db["transfers"] if x.get("league")})
    transfer_db["meta"] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "API-Football",
        "live": True,
        "clubs_known": known_team_count,
        "calls_last_run": calls,
        "api_errors_last_run": api_errors,
        "quota_exhausted": quota_exhausted,
        "team_discovery_season": discovery_season,
        "tracked_leagues": len(config.get("leagues", [])),
        "resolved_leagues": sum(1 for x in known_leagues if x.get("resolved_id")),
        "active_leagues": len(active),
        "full_sweep": full_sweep,
        "full_sweep_complete": complete_full_sweep,
        "teams_checked_last_run": selected_count,
        "duplicates_removed_last_update": removed,
    }


discover_leagues()
teams = all_teams()
selected = select_teams(teams)
meta_index = team_meta_index()
new_records = []

print(f"Starting transfer sweep: {len(selected)} of {len(teams)} known clubs across {len(config.get('leagues', []))} tracked leagues.")
for index, team in enumerate(selected, 1):
    if quota_exhausted or calls >= max_calls:
        break
    print(f"[{index}/{len(selected)}] {team.get('country')} - {team.get('league')} - {team.get('name')}")
    new_records.extend(fetch_transfers_for_team(team, meta_index))

merge_records(new_records, len(selected), len(teams))
state["last_run"] = datetime.now(timezone.utc).isoformat()
state["calls_last_run"] = calls
state["quota_exhausted"] = quota_exhausted

save(DATA / "teams.json", teams_db)
save(DATA / "players.json", players_db)
save(DATA / "transfers.json", transfer_db)
save(DATA / "state.json", state)
save(DATA / "league_ids.json", league_ids)

print(
    f"Done. API calls: {calls}; clubs known: {len(teams)}; clubs checked: {len(selected)}; "
    f"stored transfers: {len(transfer_db.get('transfers', []))}; tracked leagues: {len(config.get('leagues', []))}; "
    f"quota exhausted: {quota_exhausted}"
)
