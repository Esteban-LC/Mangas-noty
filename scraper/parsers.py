# -*- coding: utf-8 -*-
import re
from bs4 import BeautifulSoup

def _bs(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")

def _norm_tuple(s: str):
    # "119" -> (119, -1) ; "17.3" -> (17, 30) ; "17.30" -> (17, 30)
    s = str(s).strip()
    if "." in s:
        a, b = s.split(".", 1)
        return (int(a), int(b.ljust(2, "0")[:2]))
    return (int(s), -1)

def _pick_max(nums: list[str]) -> str | None:
    if not nums:
        return None
    parsed = []
    for s in nums:
        try:
            t = _norm_tuple(s)
            parsed.append((t, s))
        except Exception:
            pass
    if not parsed:
        return None
    # descarta números absurdos (> 2000) si hay opciones razonables
    plaus = [p for p in parsed if p[0][0] <= 2000] or parsed
    best = max(plaus, key=lambda x: x[0])[1]
    if "." in best:
        a, b = best.split(".", 1)
        return f"{int(a)}.{b.ljust(2,'0')[:2]}"
    return str(int(best))

# -------- ANIMEBBG.NET --------
def parse_animebbg(url: str, html: str) -> str | None:
    """
    Solo lee los elementos del listado de capítulos:
      .structItem--resourceAlbum  .structItem-title  a[href^="/comics/capitulo/"]
    Ignora contadores 'Capítulos (N)' y números ajenos.
    """
    soup = _bs(html)
    nums = []

    for a in soup.select('.structItem--resourceAlbum .structItem-title a[href^="/comics/capitulo/"]'):
        t = a.get_text(strip=True)
        m = re.search(r'Cap[ií]tulo\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
        if m:
            nums.append(m.group(1))

    if not nums:
        # fallback: usa el texto completo del título del item
        for title in soup.select('.structItem--resourceAlbum .structItem-title'):
            t = title.get_text(" ", strip=True)
            m = re.search(r'Cap[ií]tulo\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
            if m:
                nums.append(m.group(1))

    return _pick_max(nums)

# -------- M440.IN --------
def parse_m440(url: str, html: str) -> str | None:
    """
    Fuente de verdad: <a ... data-number="N"> dentro de cada <h5>.
    Fallback: '#N' en el <h5>.
    """
    soup = _bs(html)
    nums = []

    for a in soup.select('h5 a[data-number]'):
        raw = (a.get('data-number') or "").strip()
        if re.fullmatch(r'\d+(?:\.\d+)?', raw):
            nums.append(raw)

    if not nums:
        for h5 in soup.select('li[class*="DTyuZxQygzByzNbtcmg-lis"] h5'):
            t = h5.get_text(" ", strip=True)
            m = re.search(r'#\s*([0-9]+(?:\.[0-9]+)?)\b', t)
            if m:
                nums.append(m.group(1))

    return _pick_max(nums)

# -------- ZONATMO --------
def parse_zonatmo(url: str, html: str) -> str | None:
    """
    Extrae del listado de capítulos: enlaces con texto tipo 'Capítulo N' o '#N'.
    """
    soup = _bs(html)
    nums = []
    # prueba varios selectores típicos
    for sel in [
        'a', 
        '.chapters a',
        '.chapter-list a',
        'li a',
    ]:
        for a in soup.select(sel):
            t = a.get_text(" ", strip=True)
            m = re.search(r'(?:Cap[ií]tulo|#)\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
            if m:
                nums.append(m.group(1))
    return _pick_max(nums)

# -------- MANGASNOSekai / BOKUGENTS (genérico simple) --------
def parse_generic_caplist(url: str, html: str) -> str | None:
    soup = _bs(html)
    nums = []
    for a in soup.find_all('a'):
        t = a.get_text(" ", strip=True)
        m = re.search(r'(?:Cap[ií]tulo|Capitulo|#)\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
        if m:
            nums.append(m.group(1))
    return _pick_max(nums)
