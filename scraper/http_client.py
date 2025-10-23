import os, random, time, urllib.parse
import httpx

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    # móvil por si ayuda
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
]

DEFAULT_HEADERS = {
    "User-Agent": random.choice(UA_POOL),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))
RETRIES = int(os.getenv("HTTP_RETRIES", "2"))
BACKOFF = float(os.getenv("HTTP_BACKOFF", "1.0"))
BACKEND = os.getenv("FETCH_BACKEND", "auto").lower()
USE_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")  # si configuras un proxy, lo toma

class FetchError(Exception):
    pass

def _sleep_backoff(i: int):
    time.sleep(BACKOFF * (2 ** i))

def _guess_referer(url: str) -> str:
    try:
        u = urllib.parse.urlsplit(url)
        return f"{u.scheme}://{u.netloc}/"
    except Exception:
        return ""

def fetch_html(url: str, *, headers: dict | None = None, referer: str | None = None) -> str:
    """
    - BACKEND=auto: intenta httpx -> si 403/429/5xx, cae a Playwright.
    - BACKEND=playwright: usa Playwright directo.
    - BACKEND=httpx: solo httpx.
    Imprime qué backend se usó para diagnosticar.
    """
    hdrs = DEFAULT_HEADERS.copy()
    if headers: hdrs.update(headers)
    if not referer: referer = _guess_referer(url)
    if referer: hdrs["Referer"] = referer

    # Forzar backend
    if BACKEND == "playwright":
        print(f"   [fetch] playwright → {url}")
        return _fetch_with_playwright(url, hdrs, referer)

    # httpx primero
    last_exc = None
    for i in range(RETRIES):
        try:
            print(f"   [fetch] httpx → {url}")
            proxies = USE_PROXY or None
            with httpx.Client(follow_redirects=True, headers=hdrs, timeout=TIMEOUT, proxies=proxies) as client:
                resp = client.get(url)
                if resp.status_code == 200 and "text/html" in resp.headers.get("content-type",""):
                    return resp.text
                status = resp.status_code
                last_exc = FetchError(f"HTTP {status} for {url}")
                if BACKEND == "auto" and (status in (403, 429) or status >= 500):
                    # cae a playwright
                    break
                # otros códigos → no reintentes
                break
        except Exception as e:
            last_exc = e
            _sleep_backoff(i)

    if BACKEND in ("auto",) :
        print(f"   [fallback] playwright → {url}")
        try:
            return _fetch_with_playwright(url, hdrs, referer)
        except Exception as e:
            last_exc = e

    raise FetchError(str(last_exc))

def _fetch_with_playwright(url: str, headers: dict, referer: str | None) -> str:
    # Playwright stealth básico
    from playwright.sync_api import sync_playwright

    ua = headers.get("User-Agent", random.choice(UA_POOL))
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        ctx = browser.new_context(
            user_agent=ua,
            locale=headers.get("Accept-Language", "es-ES"),
            viewport={"width": 1280, "height": 2000},
            extra_http_headers=headers,
        )
        # Evasión simple de webdriver
        ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['es-ES','es']});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
            if (originalQuery) {
              window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                  Promise.resolve({ state: Notification.permission }) :
                  originalQuery(parameters)
              );
            }
        """)

        page = ctx.new_page()
        if referer:
            try:
                page.goto(referer, wait_until="domcontentloaded", timeout=int(TIMEOUT*1000))
            except Exception:
                pass
        page.goto(url, wait_until="domcontentloaded", timeout=int(TIMEOUT*1000))
        page.wait_for_timeout(900)  # pequeño respiro
        html = page.content()
        ctx.close()
        browser.close()
        return html
