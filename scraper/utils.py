import os
import json
import yaml
import httpx

def load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {"series": []}
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {"series": []}

def save_yaml(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)

def fmt_md_codeblock(text: str) -> str:
    return f"```\n{text}\n```"

def send_discord_message(content: str) -> None:
    webhook = os.getenv("DISCORD_WEBHOOK")
    if not webhook:
        return
    # payload simple, sin embeds (más robusto)
    payload = {"content": content[:1900]}  # evitar límite de 2000
    try:
        r = httpx.post(webhook, json=payload, timeout=20)
        r.raise_for_status()
    except Exception as e:
        # no hacer raise (no queremos romper el job por Discord)
        print(f"[discord] error: {e}")
