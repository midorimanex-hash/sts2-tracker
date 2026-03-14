from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

import config
import queue as q

logger = logging.getLogger(__name__)


def upload_file(file_path: str) -> bool:
    """
    1ファイルをFastAPIにアップロードする。
    成功・重複 → True（キューから除去）
    オフライン・サーバーエラー → False（キューに残す）
    """
    jwt = config.get_jwt()
    if not jwt:
        logger.warning("JWTなし。認証後に再試行します。")
        return False

    path = Path(file_path)
    if not path.exists():
        logger.warning(f"ファイルが見つかりません（削除済み？）: {path.name}")
        q.mark_uploaded(file_path)  # 存在しないファイルはキューから除去
        return True

    try:
        save_data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"ファイル読み込み失敗: {path.name} — {e}")
        return False

    payload = {
        "source_filename": path.name,
        "save_data": save_data,
    }

    try:
        resp = httpx.post(
            f"{config.get_api_url()}/runs/upload",
            json=payload,
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=30,
        )
    except httpx.ConnectError:
        logger.warning(f"オフライン。キューに保持: {path.name}")
        return False
    except Exception as e:
        logger.error(f"アップロードエラー: {path.name} — {e}")
        return False

    if resp.status_code == 201:
        q.mark_uploaded(file_path)
        logger.info(f"アップロード完了: {path.name}")
        return True
    elif resp.status_code == 409:
        q.mark_uploaded(file_path)  # サーバー側で重複検知 → 送信済み扱い
        logger.info(f"重複スキップ: {path.name}")
        return True
    else:
        logger.error(f"アップロード失敗 {resp.status_code}: {resp.text[:200]}")
        return False


def flush_queue() -> int:
    """
    キュー内の全ファイルを再送信する。
    成功件数を返す。
    """
    pending = q.get_pending()
    if not pending:
        return 0
    logger.info(f"キュー再送信: {len(pending)}件")
    success = sum(1 for fp in pending if upload_file(fp))
    return success


def register_user(local_user_id: str) -> bool:
    """
    FastAPI /auth/register を呼んで Supabase 匿名ユーザーを作成する。
    JWT・refresh_token・Supabase user_id をローカルに保存する。
    """
    try:
        resp = httpx.post(
            f"{config.get_api_url()}/auth/register",
            json={"user_id": local_user_id},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            config.save_auth(
                user_id=data["user_id"],
                jwt=data["jwt"],
                refresh_token=data["refresh_token"],
            )
            logger.info(f"認証完了。Supabase user_id: {data['user_id']}")
            return True
        logger.error(f"ユーザー登録失敗 {resp.status_code}: {resp.text[:200]}")
        return False
    except httpx.ConnectError:
        logger.warning("サーバーに接続できません。後で再試行します。")
        return False
    except Exception as e:
        logger.error(f"ユーザー登録エラー: {e}")
        return False


def refresh_token() -> bool:
    """
    保存済み refresh_token で JWT を更新する。
    """
    rt = config.get_refresh_token()
    if not rt:
        return False
    try:
        resp = httpx.post(
            f"{config.get_api_url()}/auth/refresh",
            json={"refresh_token": rt},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            config.save_auth(
                user_id=data["user_id"],
                jwt=data["jwt"],
                refresh_token=data["refresh_token"],
            )
            logger.info("JWTリフレッシュ完了。")
            return True
        logger.error(f"リフレッシュ失敗 {resp.status_code}: {resp.text[:200]}")
        return False
    except httpx.ConnectError:
        logger.warning("サーバーに接続できません。")
        return False
    except Exception as e:
        logger.error(f"リフレッシュエラー: {e}")
        return False
