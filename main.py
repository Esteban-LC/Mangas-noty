import os
import sys
from pathlib import Path
from typing import List, Tuple

import requests

from scraper.core import fetch
from scraper.parsers import resolve_parser
from scraper.utils import load_yaml, save_yaml, canon_chapter

# ======== CONFIG =========
SEND_UNCHANGED = True                 # queremos "sin actualizacion ..."
SERIES_FILE = Path("series.yaml")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")  # define en GitHub Secrets
MAX_DISCORD_CHARS = 1900              # margen bajo 2000
# =========================

def fmt(num) -> str:
    return canon_chapter(num) or "?"

def chunk_text(s: str, limit: int = MAX_DISCORD_CHARS) -> List[str]:
    out, cur, cur_len = [], [], 0
    for line in s.splitlines():
        ln = len(line) + 1
        if cur_len + ln > limit and cur:
            out.append("\n".join(cur))
            cur, cur_len = [], 0
        cur.append(line)
        cur_len += ln
    if cur:
        out.append("\n".join(cur))
    return out

def notify_discord(updates: List[Tuple[str,str,str,str]], unchanged: List[Tuple[str,str]]) -> None:
    if not DISCORD_WEBHOOK:
        print("No DISCORD_WEBHOOK — saltando notificación.")
        return

    lines = []
    if updates:
        lines.append("**✅ Actualizados**")
        for name, old, new, href in updates:
            link = f" <{href}>" if href else ""
            lines.append(f'- "{name}": {old} → **{new}**{link}')

    if SEND_UNCHANGED and unchanged:
        lines.append("**➖ Sin actualización**")
        for name, cur in unchanged:
            lines.append(f'sin actualizacion "{name}" chapter: {cur}')

    if not lines:
        print("Nada para notificar.")
        return

    payloads = chunk_text("\n".join(lines))
    for part in payloads:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": part}, timeout=20)
        except Exception as e:
            print(f"Fallo al notificar Discord (silencioso): {e}")

def main() -> int:
    data = load_yaml(SERIES_FILE)
    series = data.get("series") or []

    updates: List[Tuple[str,str,str,str]] = []   # (name, old, new, href)
    unchanged: List[Tuple[str,str]] = []         # (name, cur)
    skipped_errors: List[Tuple[str,str]] = []    # logs/summary solo

    for s in series:
        name = s.get("name", "").strip()
        url  = s.get("url", "").strip()
        if not name or not url:
            continue

        stored_raw = s.get("last_chapter")
        stored = fmt(stored_raw)

        print(f"==> {name}")
        try:
            html = fetch(url)
        except Exception as e:
            print(f"   [skip] fetch error: {e}")
            skipped_errors.append((name, f"fetch: {e}"))
            # no tocamos last_chapter ni notificamos
            continue

        parser = resolve_parser(url)
        try:
            best = parser(url, html)
        except Exception as e:
            print(f"   [skip] parser error: {e}")
            skipped_errors.append((name, f"parser: {e}"))
            continue

        found_num = fmt(best.get("num"))
        found_href = best.get("href")
        if found_num == "?":
            print("   [info] no se detectó capítulo válido")
            # si ya teníamos baseline, lo marcamos como sin actualización
            if stored and stored != "?":
                unchanged.append((name, stored))
            continue

        # primera vez
        if not stored_raw:
            s["last_chapter"] = found_num
            print(f"   [init] last_chapter = {found_num}")
            unchanged.append((name, found_num))
            continue

        if found_num != stored:
            print(f"   [update] {stored} → {found_num}")
            s["last_chapter"] = found_num
            updates.append((name, stored, found_num, found_href or url))
        else:
            print(f"   [ok] sin cambios (cap {stored})")
            unchanged.append((name, stored))

    # persistimos siempre (por si hubo inicializaciones)
    save_yaml(SERIES_FILE, data)

    # Notificaciones
    if updates or (SEND_UNCHANGED and unchanged):
        notify_discord(updates, unchanged)

    # Resumen en stdout (útil en Actions)
    print("\nResumen:")
    print(f"  Actualizados: {len(updates)}")
    print(f"  Sin actualización: {len(unchanged)}")
    if skipped_errors:
        print(f"  Con errores (silenciados en Discord): {len(skipped_errors)}")
        for n, r in skipped_errors[:10]:
            print(f"   - {n}: {r}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
