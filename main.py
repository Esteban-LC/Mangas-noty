import os
import sys
from scraper.utils import (
    load_yaml, save_yaml,
    send_discord_message, fmt_md_codeblock,
)
from scraper.http_client import fetch_html
from scraper.parsers import extract_last_chapter

SERIES_FILE = "series.yaml"

# --- DEBUG de configuración real que ve el runner ---
print(f"[cfg] FETCH_BACKEND={os.getenv('FETCH_BACKEND')!r}  "
      f"HTTPS_PROXY={'set' if os.getenv('HTTPS_PROXY') else 'unset'}  "
      f"HTTP_PROXY={'set' if os.getenv('HTTP_PROXY') else 'unset'}")


def main() -> int:
    data = load_yaml(SERIES_FILE)
    series = data.get("series", [])
    updated = []
    unchanged = []
    errors = []

    for s in series:
        name = s.get("name") or "(sin nombre)"
        site = s.get("site") or ""
        url = s.get("url") or ""
        last_chapter = s.get("last_chapter")

        print(f"==> {name}")
        if not url:
            print("   [skip] sin url")
            continue

        try:
            html = fetch_html(url)  # httpx → (fallback) playwright → (forzado) playwright
            chapter = extract_last_chapter(site, url, html)

            if chapter is None:
                print("   [info] no se detectó capítulo válido")
                continue

            # primera vez o cambio
            if last_chapter in (None, "", False):
                s["last_chapter"] = chapter
                print(f"   [init] last_chapter = {chapter}")
                unchanged.append((name, chapter))
            else:
                # comparar como texto (admite 163.5 etc.)
                if str(chapter) != str(last_chapter):
                    s["last_chapter"] = chapter
                    print(f"   [update] {last_chapter} → {chapter}")
                    updated.append((name, chapter))
                else:
                    print(f"   [ok] sin cambios (cap {chapter})")
                    unchanged.append((name, chapter))

        except Exception as e:
            # No romper; agregar a errores y silenciar en Discord
            msg = f"fetch: {e}"
            print(f"   [skip] {msg}")
            errors.append((name, msg))

    # Guardar YAML si hubo cambios
    save_yaml(SERIES_FILE, {"series": series})

    # Construir mensaje Discord
    lines = []
    if updated:
        lines.append("**📢 Actualizaciones**")
        for n, c in updated:
            lines.append(f"- **{n}** → **{c}**")
        lines.append("")

    # SIEMPRE listar “sin actualización … chapter: X”
    lines.append("**— Sin actualización**")
    for n, c in unchanged:
        lines.append(f"sin actualizacion \"{n}\" chapter: {c}")

    # Errores: solo en el log del job, NO enviar detalle 403 al Discord
    if errors:
        lines.append("")
        lines.append("_(Se omitieron errores de fetch en Discord; revisar logs del job)_")

    text = "\n".join(lines)
    webhook = os.getenv("DISCORD_WEBHOOK")
    if webhook:
        send_discord_message(text)
    else:
        print("[warn] DISCORD_WEBHOOK no configurado, imprimiendo mensaje:")
        print(fmt_md_codeblock(text))

    # Resumen en consola
    print("\nResumen:")
    print(f"  Actualizados: {len(updated)}")
    print(f"  Sin actualización: {len(unchanged)}")
    print(f"  Con errores (silenciados en Discord): {len(errors)}")
    for n, m in errors[:10]:
        print(f"   - {n}: {m}")
    if len(errors) > 10:
        print(f"   … +{len(errors)-10} más")
    return 0


if __name__ == "__main__":
    sys.exit(main())
