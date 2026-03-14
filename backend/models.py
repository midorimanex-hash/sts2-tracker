from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


# ============================================================
# セーブファイルのJSONをそのまま受け取るモデル
# ============================================================

class PlayerData(BaseModel):
    character: str
    deck: list[dict[str, Any]] = Field(default_factory=list)
    relics: list[dict[str, Any]] = Field(default_factory=list)
    potions: list[dict[str, Any]] = Field(default_factory=list)


class SaveFilePayload(BaseModel):
    """
    local-agentがPOSTするリクエストボディ。
    source_filename: セーブファイル名（重複防止用）
    save_data: セーブファイルのJSONをそのまま入れる
    """
    source_filename: str
    save_data: dict[str, Any]
