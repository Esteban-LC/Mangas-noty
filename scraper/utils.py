# -*- coding: utf-8 -*-
import os
import re
import time
import yaml
import random
import requests
from typing import Optional, Tuple

# ------- YAML IO -------
def load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {"series": []}
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {"series": []}

def save_yaml(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)

# ------- HTTP Fetch -------
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
]

def http_get(url: str, backend: str = "playwright", timeout: int = 40) -> str:
    """
    backend='playwright' | 'requests'
    Intenta playwright primero (si está disponible) y cae a requests.
    Respeta HTTP(S)_PROXY si están definidas.
    """
    backend = (backend or "").lower()
    if backend == "playwright":
        try:
            html = _fetch_playwright(url, timeout=timeout)
            if html and len(html) > 200:
                return html
        except Exception:
            # fallback a requests
            pass
    return _fetch_requests(url, timeout=timeout)

def _fetch_requests(url: str, timeout: int = 40) -> str:
    headers = {
        "User-Agent": random.choice(UA_POOL),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }
    proxies = {}
    if os.environ.get("HTTPS_PROXY"):
        proxies["https"] = os.environ["HTTPS_PROXY"]
    if os.environ.get("HTTP_PROXY"):
        proxies["http"] = os.environ["HTTP_PROXY"]

    r = requests.get(url, headers=headers, timeout=timeout, proxies=proxies, allow_redirects=True)
    r.raise_for_status()
    return r.text

def _fetch_playwright(url: str, timeout: int = 40) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("playwright no disponible") from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice(UA_POOL),
            java_script_enabled=True,
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()
        page.set_default_navigation_timeout(timeout * 1000)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        html = page.content()
        context.close()
        browser.close()
        return html

# ------- Normalización y cordura -------
def _cap_to_tuple(s: str) -> Tuple[int, int]:
    s = str(s).strip()
    if "." in s:
        a, b = s.split(".", 1)
        return (int(a), int(b.ljust(2, "0")[:2]))
    return (int(s), -1)

def comparable_tuple(s: str) -> Tuple[int, int]:
    if not s:
        return (-1, -1)
    return _cap_to_tuple(s)

def cap_to_pretty(s: str) -> str:
    a, b = comparable_tuple(s)
    return f"{a}.{str(b).zfill(2)}" if b >= 0 else str(a)

def sanity_filter(site: str, new_cap: Optional[str], prev_cap: Optional[str]) -> Tuple[bool, Optional[str], str]:
    """
    (aceptar, valor_normalizado, motivo)
    Reglas:
      - descarta >2000
      - descarta saltos enormes (new >= prev*5 y diff >=200)
      - evita regresiones fuertes (prev - new >=5): mantiene prev
      - normaliza centésimas a 2 dígitos
    """
    if not new_cap:
        return (False, None, "no-detectado")

    try:
        n = _cap_to_tuple(new_cap)
    except Exception:
        return (False, None, "parse-invalido")

    if n[0] > 2000:
        return (False, None, "cap-demasiado-grande")

    if prev_cap:
        try:
            p = _cap_to_tuple(prev_cap)
        except Exception:
            p = None

        if p:
            if (n[0] >= p[0] * 5) and (n[0] - p[0] >= 200):
                return (False, None, "salto-sospechoso")
            if (n[0] < p[0]) and ((p[0] - n[0]) >= 5):
                return (False, cap_to_pretty(prev_cap), "regresion-evitada")

    val = f"{n[0]}" if n[1] < 0 else f"{n[0]}.{str(n[1]).zfill(2)}"
    return (True, cap_to_pretty(val), "ok")
