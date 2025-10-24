#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from typing import Optional, Tuple

from scraper.utils import (
    load_yaml,
    save_yaml,
    http_get,
    sanity_filter,
    comparable_tuple,
    cap_to_pretty,
)
from scraper.sites import pick_parser

SERIES_FILE = os.environ.get("SERIES_FILE", "series.yaml")
FETCH_BACKEND = os.environ.get("FETCH_BACKEND", "playwright")


def log(msg: str):
    print(msg, flush=True)


def compare_caps(prev: Optional[str], new: Optional[str]) -> int:
    """
    Devuelve:
      -1 si new < prev
       0 si iguales
       1 si new > prev
    (compara capítulo y centésimas si existen)
    """
    if not prev and new:
        return 1
    if prev and not new:
        return -1
    if not prev and not new:
        return 0
    tp = comparable_tuple(prev)
    tn = comparable_tuple(new)
    if tn > tp:
        return 1
    if tn < tp:
        return -1
    return 0


def main() -> int:
    data = load_yaml(SERIES_FILE)
    series = data.get("series", [])
    updated = 0
    same = 0
    errors = []

    log(f"[cfg] FETCH_BACKEND='{FETCH_BACKEND}'  HTTPS_PROXY={os.environ.get('HTTPS_PROXY','unset')}  HTTP_PROXY={os.environ.get('HTTP_PROXY','unset')}")

    for s in series:
        name = s.get("name") or "(sin nombre)"
        url = s.get("url")
        site = s.get("site", "")
        prev = s.get("last_chapter") or ""
        status = "ok"

        log(f"==> {name}")

        if not url:
            log("   [skip] sin url")
            continue

        try:
            html = http_get(url, backend=FETCH_BACKEND)
            log(f"   [fetch] {FETCH_BACKEND} → {url}")
        except Exception as e:
            msg = f"fetch error: {e}"
            log(f"   [skip] {msg}")
            # Silenciado: no notificar a Discord (solo queda en resumen)
            errors.append((name, f"fetch: {e}"))
            continue

        parser = pick_parser(url)
        if not parser:
            log("   [skip] sin parser registrado para este dominio")
            continue

        try:
            candidate = parser(url, html)
        except Exception as e:
            msg = f"parse error: {e}"
            log(f"   [skip] {msg}")
            errors.append((name, f"parse: {e}"))
            continue

        if not candidate:
            log("   [info] no se detectó capítulo válido")
            continue

        # Guardarraíles de cordura
        ok, sane_value, reason = sanity_filter(site, candidate, prev)
        if not ok:
            if reason == "regresion-evitada" and sane_value:
                log(f"   [keep] regresión evitada → se mantiene (cap {sane_value})")
                # mantenemos prev, no se notifica
                same += 1
                continue
            else:
                log(f"   [skip] descartado por '{reason}'")
                same += 1
                continue

        # Aceptamos valor normalizado
        new_val = sane_value
        cmp = compare_caps(prev, new_val)

        if prev and cmp == 0:
            log(f"   [ok] sin cambios (cap {cap_to_pretty(prev)})")
            same += 1
        elif cmp > 0:
            log(f"   [update] {prev or '∅'} → {cap_to_pretty(new_val)}")
            s["last_chapter"] = new_val
            updated += 1
        else:
            # cmp < 0 (más bajo) pero no fue regresión brusca (porque ya lo bloquea sanity_filter)
            # Puede pasar por normalización de formato (ej: 3.2 → 3.20)
            if prev != new_val:
                log(f"   [update] {prev} → {new_val}")
                s["last_chapter"] = new_val
                updated += 1
            else:
                log(f"   [ok] sin cambios (cap {cap_to_pretty(prev)})")
                same += 1

        # Evita ser muy agresivo con sitios delicados
        time.sleep(float(os.environ.get("SCRAPER_SLEEP", "0.2")))

    # Guardar YAML si hubo cambios
    save_yaml(SERIES_FILE, data)

    # Resumen
    log("\nResumen:")
    log(f"  Actualizados: {updated}")
    log(f"  Sin actualización: {same}")
    log(f"  Con errores (silenciados en Discord): {len(errors)}")
    for name, err in errors[:50]:
        log(f"   - {name}: {err}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
