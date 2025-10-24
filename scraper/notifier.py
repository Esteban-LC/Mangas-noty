# -*- coding: utf-8 -*-
import json
import os
import requests
from typing import Optional, Tuple

from .utils import comparable_tuple, cap_to_pretty

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()

# Flags de comportamiento
NOTIFY_ON_ERROR = os.environ.get("NOTIFY_ON_ERROR", "false").lower() == "true"  # por si quieres re-activar errores
NOTIFY_ON_INIT = os.environ.get("NOTIFY_ON_INIT", "false").lower() == "true"    # primera vez que guardamos cap
NOTIFY_ON_FORMAT_CHANGE = os.environ.get("NOTIFY_ON_FORMAT_CHANGE", "false").lower() == "true"
FORCE_NOTIFY_TEST = os.environ.get("FORCE_NOTIFY_TEST", "false").lower() == "true"

def _send_discord(content: str):
    if not DISCORD_WEBHOOK:
        return False, "DISCORD_WEBHOOK vacío"
    try:
        r = requests.post(
            DISCORD_WEBHOOK,
            json={"content": content},
            timeout=20,
        )
        if r.status_code in (200, 204):
            return True, "ok"
        return False, f"resp {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)

def _is_real_increase(prev: Optional[str], new: Optional[str]) -> bool:
    """
    True solo si new > prev numéricamente (no es mera normalización de formato).
    """
    if not prev or not new:
        return False
    p = comparable_tuple(prev)
    n = comparable_tuple(new)
    return n > p

def _is_pure_format_change(prev: Optional[str], new: Optional[str]) -> bool:
    """
    True si comparable_tuple es igual (mismo valor) pero la representación cambió.
    """
    if not prev or not new:
        return False
    return comparable_tuple(prev) == comparable_tuple(new) and str(prev) != str(new)

def notify_event(
    event: str,  # 'init' | 'update' | 'keep' | 'ok' | 'error' | 'info'
    name: str,
    site: str,
    url: str,
    prev_cap: Optional[str],
    new_cap: Optional[str],
    extra_msg: Optional[str] = None,
):
    """
    Centraliza la decisión de notificar + el formato del mensaje.
    """
    # 1) Ping de prueba si se pide
    if FORCE_NOTIFY_TEST:
        _send_discord("🔔 **Prueba**: webhook activo (FORCE_NOTIFY_TEST=1)")
        # seguimos con la lógica normal también

    # 2) Silenciar errores salvo que lo actives
    if event == "error" and not NOTIFY_ON_ERROR:
        return

    # 3) Silenciar 'keep' (regresión evitada) y 'ok' (sin cambios)
    if event in ("keep", "ok", "info"):
        return

    # 4) 'init' solo si lo habilitas
    if event == "init" and not NOTIFY_ON_INIT:
        return

    # 5) En 'update', decidir si es incremento real o solo cambio de formato
    if event == "update":
        if _is_pure_format_change(prev_cap, new_cap) and not NOTIFY_ON_FORMAT_CHANGE:
            # No notificar normalización si no está habilitado
            return
        # Si no es formato puro, o si está habilitado, notificamos.

    # ===== Construcción del mensaje =====
    pretty_prev = cap_to_pretty(prev_cap) if prev_cap else "—"
    pretty_new  = cap_to_pretty(new_cap) if new_cap else "—"

    if event == "init":
        emoji = "🆕"
        title = "Serie inicializada"
        body  = f"**{name}**\nSitio: `{site}`\nURL: {url}\nCapítulo guardado: **{pretty_new}**"
    elif event == "update":
        emoji = "📈" if _is_real_increase(prev_cap, new_cap) else "🛠️"
        title = "Capítulo actualizado" if emoji == "📈" else "Normalización de capítulo"
        body  = f"**{name}**\nSitio: `{site}`\nURL: {url}\n`{pretty_prev}` → **{pretty_new}**"
    elif event == "error":
        emoji = "⚠️"
        title = "Error al obtener datos"
        body  = f"**{name}**\nSitio: `{site}`\nURL: {url}\nError: {extra_msg or '—'}"
    else:
        # fallback (raro)
        emoji = "ℹ️"
        title = event
        body  = f"**{name}**\nSitio: `{site}`\nURL: {url}\nPrev: {pretty_prev}  New: {pretty_new}"

    if extra_msg and event != "error":
        body += f"\nNota: {extra_msg}"

    content = f"{emoji} **{title}**\n{body}"
    _send_discord(content)
