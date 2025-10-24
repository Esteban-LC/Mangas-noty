# -*- coding: utf-8 -*-
from urllib.parse import urlsplit

from .parsers import (
    parse_animebbg,
    parse_m440,
    parse_zonatmo,
    parse_generic_caplist,
)

SITES = {
    "animebbg.net": parse_animebbg,
    "m440.in": parse_m440,
    "zonatmo.com": parse_zonatmo,
    # genérico
    "bokugents.com": parse_generic_caplist,
    "mangasnosekai.com": parse_generic_caplist,
    "animebbg.net": parse_animebbg,
    "leercapitulo.co": parse_generic_caplist,
}

def pick_parser(url: str):
    host = urlsplit(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    # busca match exacto o subdominio
    for base, func in SITES.items():
        if host == base or host.endswith("." + base):
            return func
    return parse_generic_caplist
