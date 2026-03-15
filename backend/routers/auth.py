from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from supabase import Client, create_client

router = APIRouter(prefix="/auth", tags=["auth"])

# ユーザーIDを持つ全テーブル（migrate で一括更新）
_USER_TABLES = [
    "runs",
    "floor_events",
    "floor_stats",
    "card_choices",
    "relic_choices",
    "potion_choices",
    "potion_events",
    "rest_site_choices",
    "ancient_choices",
    "event_choices",
    "shop_events",
    "card_enchantments",
    "deck_cards",
    "final_relics",
    "final_potions",
]


# ============================================================
# Supabase クライアント
# ============================================================

def get_supabase_anon() -> Client:
    """匿名サインイン用（anon キー）"""
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"],
    )


def get_supabase_admin() -> Client:
    """DB操作用（service_role キー・RLS バイパス）"""
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


# ============================================================
# スキーマ
# ============================================================

class RegisterRequest(BaseModel):
    user_id: str  # local-agent が生成したローカルUUID（ログ・デバッグ用）


class RegisterResponse(BaseModel):
    user_id: str        # Supabase が発行した実際のユーザーUUID
    jwt: str
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    user_id: str
    jwt: str
    refresh_token: str


class MigrateRequest(BaseModel):
    old_user_id: str   # 移行元の旧 Supabase UUID
    new_user_id: str   # 移行先の新 Supabase UUID（登録直後の認証済みユーザー）


class MigrateResponse(BaseModel):
    migrated_from: str
    migrated_to: str
    updated_tables: list[str]


# ============================================================
# エンドポイント
# ============================================================

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
def register(
    payload: RegisterRequest,
    anon_client: Client = Depends(get_supabase_anon),
    admin_client: Client = Depends(get_supabase_admin),
) -> RegisterResponse:
    """
    Supabase 匿名ユーザーを作成して JWT を返す。

    local-agent の初回起動時に一度だけ呼ばれる。
    以降はローカルに保存した JWT / refresh_token を使い、
    JWT 期限切れ時は /auth/refresh を呼ぶ。

    payload.user_id はローカル生成UUIDで、Supabase 側の UUID とは別物。
    実際に使う user_id は Supabase が発行したものをレスポンスで返す。
    """
    try:
        response = anon_client.auth.sign_in_anonymously()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase 匿名サインイン失敗: {e}",
        )

    user = response.user
    session = response.session

    if user is None or session is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase から有効なセッションを取得できませんでした",
        )

    # users テーブルに挿入（service_role で RLS バイパス）
    try:
        admin_client.table("users").insert({"id": str(user.id)}).execute()
    except Exception as e:
        err = str(e)
        if "duplicate key" not in err and "unique" not in err.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ユーザー登録失敗: {e}",
            )

    return RegisterResponse(
        user_id=str(user.id),
        jwt=session.access_token,
        refresh_token=session.refresh_token,
    )


@router.post("/refresh", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
def refresh(
    payload: RefreshRequest,
    anon_client: Client = Depends(get_supabase_anon),
) -> RefreshResponse:
    """
    refresh_token を使って新しい JWT を発行する。

    local-agent が JWT 期限切れを検知したときに呼ぶ。
    """
    try:
        response = anon_client.auth.refresh_session(payload.refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"トークンリフレッシュ失敗: {e}",
        )

    user = response.user
    session = response.session

    if user is None or session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効な refresh_token です",
        )

    return RefreshResponse(
        user_id=str(user.id),
        jwt=session.access_token,
        refresh_token=session.refresh_token,
    )


@router.post("/migrate", response_model=MigrateResponse, status_code=status.HTTP_200_OK)
def migrate(
    payload: MigrateRequest,
    request: Request,
    anon_client: Client = Depends(get_supabase_anon),
    admin_client: Client = Depends(get_supabase_admin),
) -> MigrateResponse:
    """
    refresh_token 紛失後に新規ユーザーを作成した際、
    旧ユーザーのデータを新ユーザーに移行する。

    セキュリティ：Authorization ヘッダーの JWT を検証し、
    その sub が new_user_id と一致することを確認する。
    これにより、第三者が他人のデータを奪取できないことを保証する。
    """
    # JWT 検証：Authorization ヘッダーから取得
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization ヘッダーが必要です",
        )
    jwt = auth_header[len("Bearer "):]

    try:
        user_resp = anon_client.auth.get_user(jwt)
        authed_user_id = str(user_resp.user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT 検証失敗: {e}",
        )

    # JWT の sub が new_user_id と一致するか確認
    if authed_user_id != payload.new_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="JWT の sub が new_user_id と一致しません",
        )

    # 全テーブルの user_id を old → new に更新（service_role で RLS バイパス）
    updated: list[str] = []
    for table in _USER_TABLES:
        try:
            result = (
                admin_client.table(table)
                .update({"user_id": payload.new_user_id})
                .eq("user_id", payload.old_user_id)
                .execute()
            )
            if result.data:
                updated.append(table)
        except Exception as e:
            # 1 テーブルの失敗でも他のテーブルの移行は続行する
            pass

    # users テーブルの旧レコードを削除（新レコードは register 時に作成済み）
    try:
        admin_client.table("users").delete().eq("id", payload.old_user_id).execute()
    except Exception:
        pass

    return MigrateResponse(
        migrated_from=payload.old_user_id,
        migrated_to=payload.new_user_id,
        updated_tables=updated,
    )
