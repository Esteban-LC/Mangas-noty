import os
import random
import time
from urllib.parse import urlparse

import requests

UA_LIST = [
    # navegadores reales
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

def sleep_jitter(a=0.4, b=1.3):
    time.sleep(random.uniform(a, b))

def origin_from(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"

def fetch(url: str, timeout: int = 25) -> str:
    """
    Fetch con headers decentes y reintentos modestos.
    No lanza a Discord los errores: solo propaga excepción al caller.
    """
    headers = {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": origin_from(url),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    retries = 3
    last_exc = None
    for i in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200 and resp.text:
                return resp.text
            # 403/404/5xx: reintenta, pero no notifiques a Discord
            last_exc = RuntimeError(f"HTTP {resp.status_code} for {url}")
        except Exception as e:
            last_exc = e
        sleep_jitter()
    raise last_exc
