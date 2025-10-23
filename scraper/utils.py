import os
import json
import yaml
import httpx
from decimal import Decimal, InvalidOperation

def load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {"series": []}
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {"series": []}

def save_yaml(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)

def fmt_md_codeblock(text: str) -> str:
    return f"```\n{text}\n```"

def send_discord_message(content: str) -> None:
    webhook = os.getenv("DISCORD_WEBHOOK")
    if not webhook:
        return
    payload = {"content": content[:1900]}
    try:
        r = httpx.post(webhook, json=payload, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"[discord] error: {e}")

# -------- Capítulos: normalización y comparación --------
def canon_chapter(ch) -> str:
    """
    Normaliza un capítulo a formato canónico para comparar/guardar:
      - '1'        -> '1'
      - '1.0'      -> '1'
      - '1.00'     -> '1'
      - '17.30'    -> '17.3'
      - '003.050'  -> '3.05'
    """
    if ch is None:
        return ""
    s = str(ch).strip()
    try:
        # Usamos Decimal para no perder precisión en 17.30 -> 17.3
        d = Decimal(s)
        # Mantener 1 o 2 decimales máx si existen (no cortar 0.05 -> 0.05)
        # Formato: quitar exponencial y ceros de más
        tup = d.as_tuple()
        # Si no hay parte decimal o es todo ceros, devolver entero
        if d == d.to_integral():
            return str(d.quantize(Decimal(1)))
        # Hay decimales no nulos; normalizar a la mínima representación
        # Convertimos a str y recortamos ceros a la derecha
        s2 = format(d, 'f')  # p.ej. '17.30'
        # recortar ceros a la derecha pero mantener al menos 1 decimal si hay punto
        if '.' in s2:
            s2 = s2.rstrip('0').rstrip('.')  # '17.30' -> '17.3', '1.00'->'1'
        return s2
    except InvalidOperation:
        # si no es número, devolver tal cual
        return s
