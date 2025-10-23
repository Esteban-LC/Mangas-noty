import os
import time
import httpx

BACKEND = os.getenv("FETCH_BACKEND", "auto").lower()
USE_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "35"))
RETRIES = int(os.getenv("HTTP_RETRIES", "2"))
BACKOFF = float(os.getenv("HTTP_BACKOFF", "1.5"))

UA = os.getenv("HTTP_UA", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

def _fetch_with_httpx(url: str) -> str:
    print(f"   [fetch] httpx → {url}")
    proxies = USE_PROXY or None
    last_err = None
    delay = 0.5
    for i in range(RETRIES + 1):
        try:
            with httpx.Client(proxies=proxies, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as cli:
                r = cli.get(url)
                if r.status_code == 403:
                    raise RuntimeError(f"HTTP 403 for {url}")
                r.raise_for_status()
                return r.text
        except Exception as e:
            last_err = e
            if i < RETRIES:
                time.sleep(delay)
                delay *= BACKOFF
            else:
                raise last_err

def _fetch_with_playwright(url: str) -> str:
    print(f"   [fetch] playwright → {url}")
    from playwright.sync_api import sync_playwright
    # Proxy para playwright
    proxy = None
    if USE_PROXY:
        proxy = {"server": USE_PROXY}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=UA,
            proxy=proxy,
            locale="es-ES",
            viewport={"width": 1280, "height": 1024},
        )
        page = context.new_page()
        page.set_default_timeout(int(TIMEOUT * 1000))

        page.goto(url, wait_until="domcontentloaded")

        # Esperas específicas por dominio
        u = url.lower()
        try:
            if "mangasnosekai.com" in u:
                page.wait_for_selector(".container-capitulos, #section-list-cap, #section-sinopsis", timeout=5000)
            elif "zonatmo.com" in u:
                page.wait_for_selector("#chapters, .chapter-list, .list-group", timeout=5000)
            elif "m440.in" in u:
                page.wait_for_selector(".chapter-list, .wp-manga-chapter, .listing-chapters_wrap", timeout=5000)
            elif "animebbg.net" in u:
                page.wait_for_selector(".chapters, .entry-content, .list-group", timeout=5000)
            elif "manga-oni.com" in u:
                page.wait_for_selector("#c_list, .entry-title-h2", timeout=5000)
            elif "leercapitulo.co" in u:
                page.wait_for_selector(".chapter-list, .xanh", timeout=5000)
        except Exception:
            pass  # si no aparece, seguimos con el HTML cargado

        html = page.content()
        context.close()
        browser.close()
        return html

def fetch_html(url: str) -> str:
    """
    Estrategia:
      - 'playwright': siempre Playwright
      - 'httpx': siempre httpx
      - 'auto' (default):
           httpx → si 403/anti-bot → fallback a Playwright
    """
    if BACKEND == "playwright":
        return _fetch_with_playwright(url)
    if BACKEND == "httpx":
        return _fetch_with_httpx(url)

    # auto
    try:
        return _fetch_with_httpx(url)
    except Exception as e:
        msg = str(e)
        if "HTTP 403" in msg or "captcha" in msg.lower():
            print(f"   [fallback] playwright → {url}")
            return _fetch_with_playwright(url)
        raise
