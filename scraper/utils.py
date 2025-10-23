import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

NUM_RE = re.compile(r'(\d+(?:\.\d+)?)')

def to_number(text: str) -> Optional[float]:
    if not text:
        return None
    m = NUM_RE.search(text.replace(',', '.'))
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

def canon_chapter(value) -> Optional[str]:
    """
    Representación canónica:
    - 166     -> "166"
    - 98.60   -> "98.6"
    - 163.5   -> "163.5"
    """
    if value is None:
        return None
    try:
        f = float(value)
        if f.is_integer():
            return str(int(f))
        # quita ceros a la derecha
        s = f"{f}".rstrip('0').rstrip('.')
        return s
    except Exception:
        # si llega string raro, intenta extraer número
        num = to_number(str(value))
        if num is None:
            return None
        return canon_chapter(num)

def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"series": []}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {"series": []}

def save_yaml(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh, allow_unicode=True, sort_keys=False)
