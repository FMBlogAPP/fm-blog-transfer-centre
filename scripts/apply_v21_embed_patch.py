#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMBED = ROOT / "blogger-embed.html"
PATCH = ROOT / "patches" / "transfer-centre-v21.html"
MARKER = "<!-- FMBTC V2.1 ENTITY PATCH -->"

base = EMBED.read_text(encoding="utf-8")
patch = PATCH.read_text(encoding="utf-8").strip()

if MARKER in base:
    base = base.split(MARKER, 1)[0].rstrip()

EMBED.write_text(base + "\n" + patch + "\n", encoding="utf-8")
print("Applied FM Blog Transfer Centre V2.1 entity patch to blogger-embed.html")
