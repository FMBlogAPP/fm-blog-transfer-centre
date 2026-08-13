#!/usr/bin/env python3
import json
import os
import re
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
PLAYERS_FILE = DATA / "players.json"
STATE_FILE = DATA / "state.json"


def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def looks_abbreviated(value):
    text = str(value or "").strip()
    if not text:
        return False
    first = text.split()[0] if text.split() else ""
    return bool(re.fullmatch(r"(?:[^\W\d_]\.){1,4}", first, flags=re.UNICODE))


def full_display_name(player):
    if not isinstance(player, dict):
        return ""
    display = str(player.get("name") or "").strip()
    if display and not looks_abbreviated(display):
        return display
    first = str(player.get("firstname") or "").strip()
    last = str(player.get("lastname") or "").strip()
    formal = " ".join(x for x in (first, last) if x).strip()
    return formal or display


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

max_calls = int(os.getenv("PLAYER_NAME_MAX_CALLS", "250"))
call_gap = float(os.getenv("PLAYER_NAME_CALL_GAP", "0.4"))
retry_after_days = int(os.getenv("PLAYER_NAME_RETRY_DAYS", "30"))
now = datetime.now(timezone.utc)

transfers_doc = load(TRANSFERS_FILE, {"transfers": []})
players_db = load(PLAYERS_FILE, {})
state = load(STATE_FILE, {})
rows = [x for x in transfers_doc.get("transfers", []) if not x.get("demo")]

# Prioritise the newest transfer for each abbreviated player so the names users
# are most likely to see are fixed first.
candidates = {}
for item in rows:
    player_id = item.get("player_id")
    label = str(item.get("player") or "").strip()
    if not player_id or not looks_abbreviated(label):
        continue
    pid = str(player_id)
    profile = players_db.get(pid) or {}
    if profile.get("full_name") and not looks_abbreviated(profile.get("full_name")):
        continue
    checked = parse_iso(profile.get("full_name_checked_at"))
    if checked and now - checked < timedelta(days=retry_after_days):
        continue
    transfer_date = str(item.get("date") or "")
    previous = candidates.get(pid)
    if not previous or transfer_date > previous[0]:
        candidates[pid] = (transfer_date, label)

targets = sorted(candidates.items(), key=lambda kv: kv[1][0], reverse=True)
print(f"Abbreviated player-name candidates waiting: {len(targets)}; call budget: {max_calls}.")

calls = 0
errors = 0
resolved = 0
last_call_at = 0.0
examples = []


def api_profile(player_id):
    global calls, errors, last_call_at
    if calls >= max_calls:
        return None
    if last_call_at:
        wait = call_gap - (time.monotonic() - last_call_at)
        if wait > 0:
            time.sleep(wait)
    qs = urlencode({"player": player_id})
    req = Request(
        f"{BASE}/players/profiles?{qs}",
        headers={"x-apisports-key": KEY, "User-Agent": "FM-Blog-Transfer-Centre/4.3"},
    )
    calls += 1
    try:
        with urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        errors += 1
        body = exc.read().decode("utf-8", "ignore")[:250]
        print(f"HTTP {exc.code} for player {player_id}: {body}", file=sys.stderr)
        return None
    except (URLError, TimeoutError) as exc:
        errors += 1
        print(f"Request failed for player {player_id}: {exc}", file=sys.stderr)
        return None
    finally:
        last_call_at = time.monotonic()
    if payload.get("errors"):
        errors += 1
        print(f"API error for player {player_id}: {payload.get('errors')}", file=sys.stderr)
        return None
    response = payload.get("response") or []
    if not response:
        return None
    first = response[0]
    return first.get("player") if isinstance(first, dict) and first.get("player") else first


for pid, (_, old_label) in targets[:max_calls]:
    profile_data = api_profile(pid)
    current = dict(players_db.get(pid, {}))
    current["full_name_checked_at"] = now.isoformat()
    if profile_data:
        name = full_display_name(profile_data)
        if name and not looks_abbreviated(name):
            current["full_name"] = name
            if profile_data.get("firstname"):
                current["firstname"] = profile_data.get("firstname")
            if profile_data.get("lastname"):
                current["lastname"] = profile_data.get("lastname")
            if profile_data.get("nationality"):
                current["nationality"] = profile_data.get("nationality")
            if profile_data.get("birth"):
                current["birth"] = profile_data.get("birth")
            if profile_data.get("height"):
                current["height"] = profile_data.get("height")
            if profile_data.get("weight"):
                current["weight"] = profile_data.get("weight")
            if profile_data.get("photo"):
                current["photo"] = profile_data.get("photo")
            if profile_data.get("age") is not None:
                current["age"] = profile_data.get("age")
            if profile_data.get("position"):
                current["position"] = profile_data.get("position")
            resolved += 1
            if len(examples) < 15 and old_label != name:
                examples.append((old_label, name))
    players_db[pid] = current

state["player_name_enrichment_at"] = now.isoformat()
state["player_name_calls_last_run"] = calls
state["player_name_errors_last_run"] = errors
state["player_full_names_known"] = sum(
    1 for p in players_db.values()
    if isinstance(p, dict) and p.get("full_name") and not looks_abbreviated(p.get("full_name"))
)

save(PLAYERS_FILE, players_db)
save(STATE_FILE, state)

print(
    f"Full-name enrichment complete. Calls: {calls}; resolved this run: {resolved}; "
    f"full names cached: {state['player_full_names_known']}; errors: {errors}."
)
if examples:
    print("Resolved name examples:")
    for old, new in examples:
        print(f"  {old} -> {new}")
