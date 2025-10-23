import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# --- Utilidades de extracción ---

# encuentra TODAS las apariciones de "Capítulo/Chapter N(.M)?" en una cadena
_RE_CAP_GENERIC = re.compile(
    r"(?:cap[ií]tulo|chapter)\s*([0-9]+(?:\.[0-9]+)?)",
    re.I
)

# patrones comunes en URLs: /capitulo/123/, /chapter-12-5, /capitulo-7.1, etc.
_RE_URL_NUM = re.compile(
    r"(?:cap[ií]tulo|chapter|chap|ep|c(?:ap)?)[-_/ ]*([0-9]+(?:\.[0-9]+)?)",
    re.I
)

def _bs(html: str):
    return BeautifulSoup(html, "html.parser")

def _collect_numbers_from_texts(texts):
    nums = []
    for t in texts:
        for m in _RE_CAP_GENERIC.finditer(t):
            nums.append(m.group(1))
    return nums

def _collect_numbers_from_links(soup: BeautifulSoup):
    nums = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # del texto del enlace
        txt = a.get_text(" ", strip=True)
        for m in _RE_CAP_GENERIC.finditer(txt):
            nums.append(m.group(1))
        # del href
        for m in _RE_URL_NUM.finditer(href):
            nums.append(m.group(1))
    return nums

def _pick_max(nums):
    """
    nums: lista de strings numéricos ('1', '17.3', '119.00')
    devuelve el mayor como string normalizado (sin ceros de más) p.ej. '119' o '17.3'
    """
    if not nums:
        return None
    # ordenar por valor float con cuidado por decimales
    def _key(x):
        try:
            return float(x)
        except Exception:
            return -1.0
    best = max(nums, key=_key)
    # normalización ligera: quitar ceros redundantes
    if "." in best:
        best = best.rstrip("0").rstrip(".")
    return best

# --- Parsers por dominio (extraen muchos textos, luego eligen el máximo) ---

def parse_manga_oni(url: str, html: str) -> str | None:
    soup = _bs(html)
    texts = [h.get_text(" ", strip=True) for h in soup.select("#c_list .entry-title-h2, #c_list a")]
    nums = _collect_numbers_from_texts(texts)
    nums += _collect_numbers_from_links(soup)
    return _pick_max(nums)

def parse_mangasnosekai(url: str, html: str) -> str | None:
    soup = _bs(html)
    texts = [x.get_text(" ", strip=True) for x in soup.select(
        ".container-capitulos * , .grid-capitulos * , #section-list-cap * , #section-sinopsis *"
    )]
    nums = _collect_numbers_from_texts(texts)
    nums += _collect_numbers_from_links(soup)
    return _pick_max(nums)

def parse_zonatmo(url: str, html: str) -> str | None:
    soup = _bs(html)
    # h4 del upload-link + cualquier <a> bajo chapter-list
    texts = [a.get_text(" ", strip=True) for a in soup.select(".chapters .upload-link h4 a, .chapters .chapter-list a, .list-group a")]
    nums = _collect_numbers_from_texts(texts)
    nums += _collect_numbers_from_links(soup)
    return _pick_max(nums)

def parse_leercapitulo(url: str, html: str) -> str | None:
    soup = _bs(html)
    texts = [a.get_text(" ", strip=True) for a in soup.select(".chapter-list a, .chapter-list h4, a.xanh")]
    nums = _collect_numbers_from_texts(texts)
    nums += _collect_numbers_from_links(soup)
    return _pick_max(nums)

def parse_bokugents(url: str, html: str) -> str | None:
    soup = _bs(html)
    texts = [a.get_text(" ", strip=True) for a in soup.select("a, h1, h2, h3, li, .wp-manga-chapter, .chapter-release-date, .list-chap")]
    nums = _collect_numbers_from_texts(texts)
    nums += _collect_numbers_from_links(soup)
    return _pick_max(nums)

def parse_m440(url: str, html: str) -> str | None:
    soup = _bs(html)
    texts = [a.get_text(" ", strip=True) for a in soup.select(
        ".chapter-list a, .wp-manga-chapter a, .listing-chapters_wrap a, a, h3, li"
    )]
    nums = _collect_numbers_from_texts(texts)
    nums += _collect_numbers_from_links(soup)
    return _pick_max(nums)

def parse_animebbg(url: str, html: str) -> str | None:
    soup = _bs(html)
    texts = [a.get_text(" ", strip=True) for a in soup.select(".chapters a, .list-group a, a, h3, li")]
    nums = _collect_numbers_from_texts(texts)
    nums += _collect_numbers_from_links(soup)
    return _pick_max(nums)

# --- Router ---

def extract_last_chapter(site: str, url: str, html: str) -> str | None:
    u = (url or "").lower()
    try:
        if "manga-oni.com" in u:
            return parse_manga_oni(u, html)
        if "mangasnosekai.com" in u:
            return parse_mangasnosekai(u, html)
        if "zonatmo.com" in u:
            return parse_zonatmo(u, html)
        if "leercapitulo.co" in u:
            return parse_leercapitulo(u, html)
        if "bokugents.com" in u:
            return parse_bokugents(u, html)
        if "m440.in" in u:
            return parse_m440(u, html)
        if "animebbg.net" in u:
            return parse_animebbg(u, html)

        # Fallback súper genérico: escanear todo el HTML por texto + hrefs
        soup = _bs(html)
        all_text = [soup.get_text(" ", strip=True)]
        nums = _collect_numbers_from_texts(all_text)
        nums += _collect_numbers_from_links(soup)
        return _pick_max(nums)
    except Exception:
        return None
