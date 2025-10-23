# manga-watcher

Vigila páginas de manga/manhwa que lees, guarda el último capítulo visto en `series.yaml` y notifica en Discord:

- ✅ **Actualizados**: `"Nombre": 92 → **93** <url>`
- ➖ **Sin actualización**: `sin actualizacion "Nombre" chapter: 92`

## Configuración

1) Crea un webhook de Discord y guárdalo como **Secret** en tu repo:
- `DISCORD_WEBHOOK`: URL del webhook.

2) Ajusta tu lista en `series.yaml`. Deja `last_chapter:` vacío para que se inicialice.

3) (Opcional) Cambia la frecuencia en `.github/workflows/watcher.yml` (`cron`).

## Ejecutar local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."
python main.py
