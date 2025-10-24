#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, yaml, re

PATH = sys.argv[1] if len(sys.argv) > 1 else "series.yaml"

with open(PATH, "r", encoding="utf-8") as fh:
    data = yaml.safe_load(fh) or {}

changed = 0
for s in data.get("series", []):
    cap = (s.get("last_chapter") or "").strip()
    if not cap:
        continue
    m = re.fullmatch(r'\d+(?:\.\d+)?', cap)
    if not m:
        s["last_chapter"] = ""
        changed += 1
        continue
    entero = int(cap.split(".", 1)[0])
    if entero > 2000:
        s["last_chapter"] = ""   # resetea para que el próximo run recalcule bien
        changed += 1

with open(PATH, "w", encoding="utf-8") as fh:
    yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)

print(f"Limpiados: {changed}")
