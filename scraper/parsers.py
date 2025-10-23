import re
from bs4 import BeautifulSoup

# Pequeña utilidad para normalizar capítulo "166", "163.5", etc.
def _first_chapter_number(strings):
    """
    Busca el primer 'Capítulo N' (o 'Chapter N') admitiendo decimales.
    Retorna str con el número (p.ej. "163.5") o None.
    """
    pat = re.compile(r"(cap[ií]tulo|chapter)\s*([0-9]+(?:\.[0-9]+)?)", re.I)
    for s in strings:
        m = pat.search(s)
        if m:
            return m.group(2)
    return None

def _bs(html: str):
    return BeautifulSoup(html, "html.parser")

# -------- Parsers por sitio --------

def parse_manga_oni(url: str, html: str) -> str | None:
    soup = _bs(html)
    # Lista dentro de #c_list → .entry-title-h2
    texts = [h.get_text(" ", strip=True) for h in soup.select("#c_list .entry-title-h2")]
    return _first_chapter_number(texts)

def parse_mangasnosekai(url: str, html: str) -> str | None:
    soup = _bs(html)
    # En tarjetas de capítulos: "Capítulo 93"
    texts = [x.get_text(" ", strip=True) for x in soup.select(".container-capitulos .text-sm, .grid-capitulos .text-sm")]
    return _first_chapter_number(texts)

def parse_zonatmo(url: str, html: str) -> str | None:
    soup = _bs(html)
    # Títulos en li.upload-link h4 .btn-collapse -> "Capítulo 1.00  Bebe ..."
    texts = [a.get_text(" ", strip=True) for a in soup.select(".chapters .upload-link h4 a")]
    return _first_chapter_number(texts)

def parse_leercapitulo(url: str, html: str) -> str | None:
    soup = _bs(html)
    # <a class="xanh" ...>Capitulo 7</a>
    texts = [a.get_text(" ", strip=True) for a in soup.select(".chapter-list a.xanh")]
    return _first_chapter_number(texts)

def parse_bokugents(url: str, html: str) -> str | None:
    soup = _bs(html)
    # diversos themes: buscar “Capítulo N” en enlaces de capítulos
    texts = [a.get_text(" ", strip=True) for a in soup.select("a, h3, li")]
    return _first_chapter_number(texts)

def parse_m440(url: str, html: str) -> str | None:
    soup = _bs(html)
    texts = [a.get_text(" ", strip=True) for a in soup.select(".chapter-list a, .wp-manga-chapter a, a")]
    return _first_chapter_number(texts)

def parse_animebbg(url: str, html: str) -> str | None:
    soup = _bs(html)
    texts = [a.get_text(" ", strip=True) for a in soup.select(".chapters a, .list-group a, a")]
    return _first_chapter_number(texts)

# -------- Router --------

def extract_last_chapter(site: str, url: str, html: str) -> str | None:
    s = (site or "").lower()
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
        # fallback genérico (muchas páginas comparten “Capítulo N”)
        return _first_chapter_number([_bs(html).get_text(" ", strip=True)])
    except Exception:
        return None
