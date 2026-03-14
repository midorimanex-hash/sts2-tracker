from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from supabase import Client, create_client

from models import SaveFilePayload

router = APIRouter(prefix="/runs", tags=["runs"])


# ============================================================
# Supabase クライアント
# ============================================================

def get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # service_role で RLS をバイパスして書き込み
    return create_client(url, key)


# ============================================================
# JWT からユーザーIDを検証
# ============================================================

def get_user_id(
    authorization: str = Header(..., description="Bearer <JWT>"),
    supabase: Client = Depends(get_supabase),
) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        response = supabase.auth.get_user(token)
        if response.user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return str(response.user.id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token verification failed")


# ============================================================
# map_point_history をフラットに展開するイテレータ
# act_idx（0始まり）・floor（1始まりの通し番号）・フロアデータを返す
# ============================================================

def _iter_floors(map_point_history: list[list[dict]]):
    floor_num = 1
    for act_idx, act_floors in enumerate(map_point_history):
        for floor_data in act_floors:
            ps_list = floor_data.get("player_stats") or []
            floor_data = {**floor_data, "_ps": ps_list[0] if ps_list else {}}
            yield act_idx, floor_num, floor_data
            floor_num += 1


# ============================================================
# パーサー群
# map_point_history の全フロアを走査して各テーブル用の行を生成する
# ============================================================

def _parse_floor_events(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for act_idx, floor_num, floor_data in _iter_floors(map_point_history):
        rows.append({
            "run_id": run_id,
            "user_id": user_id,
            "floor": floor_num,
            "act": act_idx + 1,
            "room_type": floor_data.get("map_point_type", "UNKNOWN"),
            "encounter_id": floor_data.get("encounter_id"),
            "event_id": floor_data.get("event_id"),
        })
    return rows


def _parse_floor_stats(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        ps = floor_data.get("_ps") or {}
        hp = ps.get("current_hp")
        max_hp = ps.get("max_hp")
        gold = ps.get("current_gold")
        if hp is None or max_hp is None or gold is None:
            continue
        rows.append({
            "run_id": run_id,
            "user_id": user_id,
            "floor": floor_num,
            "current_hp": hp,
            "max_hp": max_hp,
            "gold": gold,
        })
    return rows


def _parse_card_choices(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        for choice in (floor_data.get("_ps") or {}).get("card_choices") or []:
            picked = choice.get("picked")
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "picked": picked,
                "skipped": picked is None,
                "not_picked": choice.get("not_picked") or [],
            })
    return rows


def _parse_relic_choices(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        for choice in (floor_data.get("_ps") or {}).get("relic_choices") or []:
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "source": choice.get("source", "UNKNOWN"),
                "picked": choice.get("picked"),
                "not_picked": choice.get("not_picked") or [],
            })
    return rows


def _parse_potion_choices(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        for choice in (floor_data.get("_ps") or {}).get("potion_choices") or []:
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "picked": choice.get("picked"),
                "not_picked": choice.get("not_picked") or [],
            })
    return rows


def _parse_potion_events(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        ps = floor_data.get("_ps") or {}
        for potion_id in ps.get("potion_used") or []:
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "potion_id": potion_id if isinstance(potion_id, str) else potion_id.get("id", ""),
                "action": "USE",
            })
        for potion_id in ps.get("potion_discarded") or []:
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "potion_id": potion_id if isinstance(potion_id, str) else potion_id.get("id", ""),
                "action": "DISCARD",
            })
    return rows


def _parse_rest_site_choices(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        for choice in (floor_data.get("_ps") or {}).get("rest_site_choices") or []:
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "action": choice.get("action", "UNKNOWN"),
                "card_upgraded": choice.get("card_upgraded"),
            })
    return rows


def _parse_ancient_choices(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        choice = (floor_data.get("_ps") or {}).get("ancient_choice")
        if not choice:
            continue
        rows.append({
            "run_id": run_id,
            "user_id": user_id,
            "floor": floor_num,
            "ancient_id": choice.get("ancient_id", ""),
            "picked": choice.get("picked", ""),
            "not_picked": choice.get("not_picked") or [],
        })
    return rows


def _parse_event_choices(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        for choice in (floor_data.get("_ps") or {}).get("event_choices") or []:
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "event_id": choice.get("event_id", ""),
                "option_chosen": choice.get("option_chosen", ""),
                "result": choice.get("result"),
            })
    return rows


def _parse_shop_events(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        ps = floor_data.get("_ps") or {}
        for relic in ps.get("bought_relics") or []:
            relic_id = relic if isinstance(relic, str) else relic.get("id", "")
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "action": "BUY_RELIC",
                "item_id": relic_id,
                "cost": relic.get("cost", 0) if isinstance(relic, dict) else 0,
            })
        for card in ps.get("cards_removed") or []:
            card_id = card if isinstance(card, str) else card.get("id", "")
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "action": "PURGE_CARD",
                "item_id": card_id,
                "cost": card.get("cost", 0) if isinstance(card, dict) else 0,
            })
    return rows


def _parse_card_enchantments(
    run_id: str, user_id: str, map_point_history: list[list[dict]]
) -> list[dict]:
    rows = []
    for _, floor_num, floor_data in _iter_floors(map_point_history):
        ps = floor_data.get("_ps") or {}
        for card in ps.get("upgraded_cards") or []:
            card_id = card if isinstance(card, str) else card.get("id", "")
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "card_id": card_id,
                "enchantment": "UPGRADE",
                "source": card.get("source") if isinstance(card, dict) else None,
            })
        for card in ps.get("cards_enchanted") or []:
            card_id = card if isinstance(card, str) else card.get("id", "")
            rows.append({
                "run_id": run_id,
                "user_id": user_id,
                "floor": floor_num,
                "card_id": card_id,
                "enchantment": card.get("enchantment", "ENCHANT") if isinstance(card, dict) else "ENCHANT",
                "source": card.get("source") if isinstance(card, dict) else None,
            })
    return rows


def _parse_deck_cards(run_id: str, user_id: str, deck: list[dict]) -> list[dict]:
    counts: dict[tuple[str, bool], int] = {}
    for card in deck:
        card_id = card.get("id") or card.get("card_id") or ""
        upgraded = bool(card.get("upgraded", False))
        counts[(card_id, upgraded)] = counts.get((card_id, upgraded), 0) + 1
    return [
        {
            "run_id": run_id,
            "user_id": user_id,
            "card_id": card_id,
            "upgraded": upgraded,
            "count": count,
        }
        for (card_id, upgraded), count in counts.items()
    ]


def _parse_final_relics(run_id: str, user_id: str, relics: list[Any]) -> list[dict]:
    rows = []
    for i, relic in enumerate(relics):
        relic_id = relic if isinstance(relic, str) else relic.get("id") or relic.get("relic_id") or ""
        rows.append({"run_id": run_id, "user_id": user_id, "relic_id": relic_id, "slot": i})
    return rows


def _parse_final_potions(run_id: str, user_id: str, potions: list[Any]) -> list[dict]:
    rows = []
    for i, potion in enumerate(potions):
        potion_id = potion if isinstance(potion, str) else potion.get("id") or potion.get("potion_id") or ""
        rows.append({"run_id": run_id, "user_id": user_id, "potion_id": potion_id, "slot": i})
    return rows


def _bulk_insert(supabase: Client, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    supabase.table(table).insert(rows).execute()


# ============================================================
# エンドポイント
# ============================================================

@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_run(
    payload: SaveFilePayload,
    user_id: str = Depends(get_user_id),
    supabase: Client = Depends(get_supabase),
) -> dict:
    """
    セーブファイルのJSONを受け取り、Supabaseの各テーブルに保存する。
    同じ source_filename は重複挿入しない（409を返す）。
    """
    d = payload.save_data
    player: dict = (d.get("players") or [{}])[0]
    map_point_history: list[list[dict]] = d.get("map_point_history") or []

    # ---- runs テーブルに挿入 ----
    run_row = {
        "user_id": user_id,
        "source_filename": payload.source_filename,
        "character": player.get("character", "UNKNOWN"),
        "ascension": d.get("ascension", 0),
        "win": bool(d.get("win", False)),
        "was_abandoned": bool(d.get("was_abandoned", False)),
        "killed_by_encounter": d.get("killed_by_encounter"),
        "acts": d.get("acts"),
        "run_timestamp": d.get("start_time"),  # start_time をランのタイムスタンプとして使用
    }

    try:
        result = supabase.table("runs").insert(run_row).execute()
    except Exception as e:
        err = str(e)
        if "duplicate key" in err or "unique" in err.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Run already uploaded: {payload.source_filename}",
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err)

    run_id: str = result.data[0]["id"]

    # ---- 子テーブルに一括挿入 ----
    _bulk_insert(supabase, "floor_events",       _parse_floor_events(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "floor_stats",        _parse_floor_stats(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "card_choices",       _parse_card_choices(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "relic_choices",      _parse_relic_choices(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "potion_choices",     _parse_potion_choices(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "potion_events",      _parse_potion_events(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "rest_site_choices",  _parse_rest_site_choices(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "ancient_choices",    _parse_ancient_choices(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "event_choices",      _parse_event_choices(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "shop_events",        _parse_shop_events(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "card_enchantments",  _parse_card_enchantments(run_id, user_id, map_point_history))
    _bulk_insert(supabase, "deck_cards",         _parse_deck_cards(run_id, user_id, player.get("deck") or []))
    _bulk_insert(supabase, "final_relics",       _parse_final_relics(run_id, user_id, player.get("relics") or []))
    _bulk_insert(supabase, "final_potions",      _parse_final_potions(run_id, user_id, player.get("potions") or []))

    return {"run_id": run_id}
