import re
from typing import Callable, Dict, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .utils import to_number, canon_chapter

Result = Dict[str, Optional[str]]
Parser = Callable[[str, str], Result]

CAP_RE = re.compile(r'(?:Cap[ií]tulo|Capitulo|Chapter|Cap)\s*([0-9]+(?:\.[0-9]+)?)', re.I)

def _pick_max_number_with_href(soup: BeautifulSoup, base_url: str) -> Result:
    """
    Fallback genérico: busca textos 'Capítulo N' y devuelve el mayor.
    """
    best_num = None
    best_href = None
    best_title = None

    # mirar links y headings
    for tag in soup.find_all(['a', 'h1', 'h2', 'h3', 'div', 'span']):
        text = (tag.get_text() or "").strip()
        m = CAP_RE.search(text)
        if not m:
            continue
        num = to_number(m.group(1))
        if num is None:
            continue
        if best_num is None or num > best_num:
            best_num = num
            best_title = text
            href = tag.get('href')
            if href:
                best_href = urljoin(base_url, href)

    return {
        "num": canon_chapter(best_num),
        "href": best_href,
        "title": best_title,
    }

# --- manga-oni.com ---
def parse_manga_oni(url: str, html: str) -> Result:
    soup = BeautifulSoup(html, "lxml")

    # patrón específico: #c_list a .entry-title span.timeago[data-num]
    nums = []
    for a in soup.select("#c_list a"):
        timeago = a.select_one(".entry-title .timeago")
        n = None
        if timeago and timeago.has_attr("data-num"):
            n = to_number(timeago["data-num"])
        else:
            # fallback por <h3>Capítulo 166</h3>
            h3 = a.select_one("h3")
            if h3:
                m = CAP_RE.search(h3.get_text())
                if m:
                    n = to_number(m.group(1))
        if n is not None:
            nums.append((n, a.get("href"), a.get_text(strip=True)))

    if nums:
        n, href, title = max(nums, key=lambda t: t[0])
        return {"num": canon_chapter(n), "href": urljoin(url, href or ""), "title": title}
    return _pick_max_number_with_href(soup, url)

# --- mangasnosekai.com ---
def parse_mangasnosekai(url: str, html: str) -> Result:
    soup = BeautifulSoup(html, "lxml")

    # sección lista de capítulos (miniaturas)
    candidates = []
    for card in soup.select(".container-capitulos .contenedor-capitulo-miniatura"):
        text = card.get_text(" ", strip=True)
        m = CAP_RE.search(text)
        if m:
            n = to_number(m.group(1))
            href = None
            a = card.select_one("a[href]")
            if a:
                href = a["href"]
            if n is not None:
                candidates.append((n, href, text))
    if candidates:
        n, href, title = max(candidates, key=lambda t: t[0])
        return {"num": canon_chapter(n), "href": urljoin(url, href or ""), "title": title}

    return _pick_max_number_with_href(soup, url)

# --- zonatmo.com ---
def parse_zonatmo(url: str, html: str) -> Result:
    soup = BeautifulSoup(html, "lxml")

    # el HTML lista "Capítulo X" en headers y elementos
    return _pick_max_number_with_href(soup, url)

# --- leercapitulo.co ---
def parse_leercapitulo(url: str, html: str) -> Result:
    soup = BeautifulSoup(html, "lxml")
    lst = soup.select(".chapter-list a.xanh")
    best = None
    for a in lst:
        text = a.get_text(" ", strip=True)
        m = CAP_RE.search(text)
        if not m:
            continue
        n = to_number(m.group(1))
        if n is None:
            continue
        if best is None or n > best[0]:
            best = (n, urljoin(url, a.get("href", "")), text)
    if best:
        n, href, title = best
        return {"num": canon_chapter(n), "href": href, "title": title}
    return _pick_max_number_with_href(soup, url)

# --- m440.in / mm440.in / lmtos (alias) ---
def parse_m440(url: str, html: str) -> Result:
    soup = BeautifulSoup(html, "lxml")
    return _pick_max_number_with_href(soup, url)

# --- fallback por dominio ---
def resolve_parser(url: str) -> Parser:
    host = urlparse(url).netloc.lower()

    if "manga-oni.com" in host:
        return parse_manga_oni
    if "mangasnosekai.com" in host:
        return parse_mangasnosekai
    if "zonatmo.com" in host:
        return parse_zonatmo
    if "leercapitulo.co" in host:
        return parse_leercapitulo
    if "m440.in" in host or "mm440.in" in host or "lmtos" in host:
        return parse_m440

    # por defecto: genérico
    return lambda u, h: _pick_max_number_with_href(BeautifulSoup(h, "lxml"), u)
