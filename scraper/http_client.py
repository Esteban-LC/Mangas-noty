import os
import random
import time
from contextlib import asynccontextmanager

import httpx

UA_POOL = [
    # Pool de UAs reales y recientes (rotamos para reducir 403)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
]

DEFAULT_HEADERS = {
    "User-Agent": random.choice(UA_POOL),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Dest": "document",
    "Upgrade-Insecure-Requests": "1",
}

TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))
RETRIES = int(os.getenv("HTTP_RETRIES", "2"))
BACKOFF = float(os.getenv("HTTP_BACKOFF", "1.0"))
PLAYWRIGHT_ENABLED = os.getenv("FETCH_BACKEND", "auto") in ("auto", "playwright")

class FetchError(Exception):
    pass

def _sleep_backoff(i: int):
    time.sleep(BACKOFF * (2 ** i))

def fetch_html(url: str, *, headers: dict | None = None, referer: str | None = None) -> str:
    """
    Intenta con httpx primero; si 403/5xx y está habilitado, cae a Playwright.
    """
    hdrs = DEFAULT_HEADERS.copy()
    if headers:
        hdrs.update(headers)
    if referer:
        hdrs["Referer"] = referer

    last_exc = None

    # 1) httpx (rápido)
    for i in range(RETRIES):
        try:
            with httpx.Client(follow_redirects=True, headers=hdrs, timeout=TIMEOUT) as client:
                resp = client.get(url)
                if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                    return resp.text
                if resp.status_code in (403, 429) or resp.status_code >= 500:
                    last_exc = FetchError(f"HTTP {resp.status_code} for {url}")
                    _sleep_backoff(i)
                    continue
                # estados 3xx/4xx no críticos
                last_exc = FetchError(f"HTTP {resp.status_code} for {url}")
                break
        except Exception as e:
            last_exc = e
            _sleep_backoff(i)

    # 2) Fallback a Playwright (si está activado)
    if PLAYWRIGHT_ENABLED:
        try:
            return _fetch_with_playwright(url, referer=referer, headers=hdrs)
        except Exception as e:
            last_exc = e

    raise FetchError(str(last_exc) if last_exc else f"Unknown error fetching {url}")

def _fetch_with_playwright(url: str, referer: str | None, headers: dict) -> str:
    """
    Usa Chromium headless para renderizar y devolver el HTML.
    No abras/ cierres el browser por cada URL si te preocupa el tiempo: para CI está OK.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=headers.get("User-Agent", random.choice(UA_POOL)),
                                  locale="es-ES",
                                  extra_http_headers=headers)
        page = ctx.new_page()
        if referer:
            # Intento suave de setear referer previo
            page.goto(referer, wait_until="domcontentloaded", timeout=int(TIMEOUT * 1000))
        page.goto(url, wait_until="domcontentloaded", timeout=int(TIMEOUT * 1000))
        # Espera corta por sitios con JS que inyecta lista
        page.wait_for_timeout(700)
        html = page.content()
        ctx.close()
        browser.close()
        return html
