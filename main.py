import os
import sys
from scraper.utils import (
    load_yaml, save_yaml,
    send_discord_message, fmt_md_codeblock,
    canon_chapter,                    # <-- NUEVO
)
from scraper.http_client import fetch_html
from scraper.parsers import extract_last_chapter

SERIES_FILE = "series.yaml"

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
            html = fetch_html(url)
            chapter = extract_last_chapter(site, url, html)

            if chapter is None:
                print("   [info] no se detectó capítulo válido")
                continue

            new_canon = canon_chapter(chapter)
            old_canon = canon_chapter(last_chapter)

            if old_canon == "":
                s["last_chapter"] = new_canon
                print(f"   [init] last_chapter = {new_canon}")
                unchanged.append((name, new_canon))
            else:
                if new_canon != old_canon:
                    print(f"   [update] {old_canon} → {new_canon}")
                    s["last_chapter"] = new_canon
                    updated.append((name, new_canon))
                else:
                    print(f"   [ok] sin cambios (cap {new_canon})")
                    unchanged.append((name, new_canon))

        except Exception as e:
            msg = f"fetch: {e}"
            print(f"   [skip] {msg}")
            errors.append((name, msg))

    save_yaml(SERIES_FILE, {"series": series})

    lines = []
    if updated:
        lines.append("**📢 Actualizaciones**")
        for n, c in updated:
            lines.append(f"- **{n}** → **{c}**")
        lines.append("")

    lines.append("**— Sin actualización**")
    for n, c in unchanged:
        lines.append(f"sin actualizacion \"{n}\" chapter: {c}")

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
