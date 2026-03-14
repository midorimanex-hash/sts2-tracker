from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client, create_client

router = APIRouter(prefix="/auth", tags=["auth"])


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
    # auth.uid() と users.id が一致する設計なので Supabase UUID をそのまま使う
    try:
        admin_client.table("users").insert({"id": str(user.id)}).execute()
    except Exception as e:
        # 万が一の重複挿入は無視（通常は発生しない）
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
        refresh_token=session.refresh_token,  # Supabase はリフレッシュのたびに新しい値を返す
    )
