#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HUB_FILE = DATA / "hub_profiles.json"
DETAIL_FILE = DATA / "player_details.json"


def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


hub = load(HUB_FILE, {})
details = load(DETAIL_FILE, {})
players = hub.get("players") or {}

if not hub or not details:
    print("No rich player-detail cache available; nothing to merge.")
    raise SystemExit(0)

merged = 0
for pid, detail in details.items():
    if not isinstance(detail, dict):
        continue
    profile = detail.get("profile") or {}
    if not isinstance(profile, dict) or not profile:
        continue

    current = players.get(str(pid))
    if current is None:
        # Detailed hub enrichment currently targets transfer players, but keep
        # this safe if that prioritisation changes later.
        current = {"id": profile.get("id") or (int(pid) if str(pid).isdigit() else pid)}
        players[str(pid)] = current

    full_name = " ".join(
        x.strip() for x in [str(profile.get("firstname") or ""), str(profile.get("lastname") or "")]
        if x.strip()
    ).strip()

    if full_name:
        current["name"] = full_name
    elif profile.get("name"):
        current["name"] = profile.get("name")

    for key in ("firstname", "lastname", "age", "birth", "nationality", "height", "weight", "photo", "injured"):
        value = profile.get(key)
        if value not in (None, "", {}):
            current[key] = value

    # Preserve the already-built football data from enrich_transfer_feed.py.
    if detail.get("statistics") is not None:
        current["statistics"] = detail.get("statistics") or []
    if detail.get("career") is not None:
        current["career"] = detail.get("career") or []
    if detail.get("trophies") is not None:
        current["trophies"] = detail.get("trophies") or []
    if detail.get("sidelined") is not None:
        current["sidelined"] = detail.get("sidelined") or []
    current["details_updated_at"] = detail.get("updated_at") or current.get("details_updated_at") or ""
    merged += 1

hub["players"] = players
meta = hub.setdefault("meta", {})
meta["rich_player_bios"] = merged
save(HUB_FILE, hub)
print(f"Merged rich API player bios into hub cache: {merged} players.")
