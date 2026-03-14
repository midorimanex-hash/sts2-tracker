from __future__ import annotations

import json
import uuid
from pathlib import Path

CONFIG_DIR = Path.home() / ".sts2tracker"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_API_URL = "http://localhost:8000"
DASHBOARD_URL = "https://sts2tracker.pages.dev"  # Cloudflare Pagesのドメインに合わせて変更


def _load() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def _save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_or_create_user_id() -> str:
    data = _load()
    if "user_id" not in data:
        data["user_id"] = str(uuid.uuid4())
        _save(data)
    return data["user_id"]


def get_jwt() -> str | None:
    return _load().get("jwt")


def get_refresh_token() -> str | None:
    return _load().get("refresh_token")


def save_auth(user_id: str, jwt: str, refresh_token: str) -> None:
    """Supabase から返された認証情報をまとめて保存する。"""
    data = _load()
    data["user_id"] = user_id          # Supabase UUID で上書き（ローカル生成UUIDを置き換え）
    data["jwt"] = jwt
    data["refresh_token"] = refresh_token
    _save(data)


def get_api_url() -> str:
    return _load().get("api_url", DEFAULT_API_URL)


def get_dashboard_url() -> str:
    jwt = get_jwt()
    if jwt:
        return f"{DASHBOARD_URL}?token={jwt}"
    return DASHBOARD_URL
