#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "transfers.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def canonical_key(item):
    return "|".join([
        str(item.get("player_id") or ""),
        str(item.get("from_id") or ""),
        str(item.get("to_id") or ""),
        movement_class(item.get("type")),
    ])


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


def merge(a, b):
    newer, older = (b, a) if (b.get("date") or "") >= (a.get("date") or "") else (a, b)
    out = dict(older)
    out.update({k: v for k, v in newer.items() if v not in (None, "")})
    out["date"] = max(a.get("date") or "", b.get("date") or "") or None
    out["type"] = b.get("type") if type_quality(b.get("type")) > type_quality(a.get("type")) else a.get("type")
    out["type"] = out.get("type") or "Undisclosed"
    out["id"] = canonical_key(out)
    return out


data = load(DATA_FILE)
rows = [x for x in data.get("transfers", []) if not x.get("demo") and x.get("player_id")]
before = len(rows)
clean = {}

for item in rows:
    item = dict(item)
    key = canonical_key(item)
    item["id"] = key
    clean[key] = merge(clean[key], item) if key in clean else item

result = list(clean.values())
result.sort(key=lambda x: (x.get("date") or "", x.get("id") or ""), reverse=True)
data["transfers"] = result
meta = data.setdefault("meta", {})
meta["duplicates_removed_last_cleanup"] = before - len(result)
meta["dedupe_cleaned_at"] = datetime.now(timezone.utc).isoformat()
save(DATA_FILE, data)

print(f"Duplicate cleanup complete. Before: {before}; after: {len(result)}; removed: {before - len(result)}")
