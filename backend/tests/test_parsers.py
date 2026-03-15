"""
backend/routers/runs.py のパーサー関数ユニットテスト
Supabase・FastAPI への接続は不要（純粋なデータ変換のみ）
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from routers.runs import (
    _get,
    _iter_floors,
    _parse_ancient_choices,
    _parse_card_choices,
    _parse_card_enchantments,
    _parse_deck_cards,
    _parse_event_choices,
    _parse_final_potions,
    _parse_final_relics,
    _parse_floor_events,
    _parse_floor_stats,
    _parse_potion_choices,
    _parse_potion_events,
    _parse_relic_choices,
    _parse_rest_site_choices,
    _parse_shop_events,
)

RUN_ID = "run-001"
USER_ID = "user-001"


# ============================================================
# ヘルパー関数
# ============================================================

def make_history(*floor_ps_list: dict) -> list[list[dict]]:
    """player_stats を持つフロアのリストを1アクトとして返す"""
    act = [{"map_point_type": "MONSTER", "player_stats": [ps]} for ps in floor_ps_list]
    return [act]


def make_floor(**ps_fields) -> dict:
    """player_stats フィールドを持つフロアデータを返す"""
    return {"map_point_type": "MONSTER", "player_stats": [ps_fields]}


# ============================================================
# _get
# ============================================================

class TestGet:
    def test_string_returns_itself(self):
        assert _get("STRIKE") == "STRIKE"

    def test_dict_first_key_hit(self):
        assert _get({"id": "STRIKE", "card_id": "X"}, "id", "card_id") == "STRIKE"

    def test_dict_second_key_hit(self):
        assert _get({"card_id": "DEFEND"}, "id", "card_id") == "DEFEND"

    def test_dict_no_key_returns_default(self):
        assert _get({"x": 1}, "id") is None
        assert _get({"x": 1}, "id", default="?") == "?"

    def test_none_returns_default(self):
        assert _get(None, "id") is None


# ============================================================
# _iter_floors
# ============================================================

class TestIterFloors:
    def test_floor_numbers_increment_across_acts(self):
        history = [
            [{"player_stats": []}, {"player_stats": []}],   # act 1: floor 1,2
            [{"player_stats": []}],                          # act 2: floor 3
        ]
        results = list(_iter_floors(history))
        assert [(act, floor) for act, floor, _ in results] == [(0, 1), (0, 2), (1, 3)]

    def test_empty_history(self):
        assert list(_iter_floors([])) == []

    def test_ps_injected_as_first_player_stat(self):
        history = [[{"player_stats": [{"current_hp": 42}]}]]
        _, _, floor_data = list(_iter_floors(history))[0]
        assert floor_data["_ps"]["current_hp"] == 42

    def test_missing_player_stats_yields_empty_ps(self):
        history = [[{"player_stats": []}]]
        _, _, floor_data = list(_iter_floors(history))[0]
        assert floor_data["_ps"] == {}


# ============================================================
# _parse_floor_events
# ============================================================

class TestParseFloorEvents:
    def test_basic(self):
        history = [[
            {"map_point_type": "MONSTER", "encounter_id": "GREMLIN", "player_stats": []},
            {"map_point_type": "EVENT",   "event_id": "MUSHROOMS",  "player_stats": []},
        ]]
        rows = _parse_floor_events(RUN_ID, USER_ID, history)
        assert len(rows) == 2
        assert rows[0]["room_type"] == "MONSTER"
        assert rows[0]["encounter_id"] == "GREMLIN"
        assert rows[1]["event_id"] == "MUSHROOMS"
        assert rows[1]["act"] == 1
        assert rows[1]["floor"] == 2

    def test_empty(self):
        assert _parse_floor_events(RUN_ID, USER_ID, []) == []


# ============================================================
# _parse_floor_stats
# ============================================================

class TestParseFloorStats:
    def test_basic(self):
        rows = _parse_floor_stats(RUN_ID, USER_ID, make_history(
            {"current_hp": 50, "max_hp": 80, "current_gold": 120},
        ))
        assert len(rows) == 1
        assert rows[0]["current_hp"] == 50
        assert rows[0]["max_hp"] == 80
        assert rows[0]["gold"] == 120

    def test_skips_floor_with_missing_values(self):
        rows = _parse_floor_stats(RUN_ID, USER_ID, make_history(
            {"current_hp": 50, "max_hp": 80},          # gold なし → スキップ
            {"current_hp": 30, "max_hp": 70, "current_gold": 99},
        ))
        assert len(rows) == 1
        assert rows[0]["gold"] == 99


# ============================================================
# _parse_card_choices
# ============================================================

class TestParseCardChoices:
    def test_dict_format(self):
        rows = _parse_card_choices(RUN_ID, USER_ID, make_history(
            {"card_choices": [{"picked": "STRIKE", "not_picked": ["DEFEND", "BASH"]}]},
        ))
        assert rows[0]["picked"] == "STRIKE"
        assert rows[0]["not_picked"] == ["DEFEND", "BASH"]
        assert rows[0]["skipped"] is False

    def test_string_format(self):
        rows = _parse_card_choices(RUN_ID, USER_ID, make_history(
            {"card_choices": ["STRIKE"]},
        ))
        assert rows[0]["picked"] == "STRIKE"
        assert rows[0]["skipped"] is False

    def test_skipped(self):
        rows = _parse_card_choices(RUN_ID, USER_ID, make_history(
            {"card_choices": [{"picked": None, "not_picked": ["DEFEND"]}]},
        ))
        assert rows[0]["skipped"] is True

    def test_empty(self):
        assert _parse_card_choices(RUN_ID, USER_ID, make_history({})) == []


# ============================================================
# _parse_relic_choices
# ============================================================

class TestParseRelicChoices:
    def test_dict_format(self):
        rows = _parse_relic_choices(RUN_ID, USER_ID, make_history(
            {"relic_choices": [{"picked": "BURNING_BLOOD", "not_picked": ["RING_OF_SNAKE"], "source": "BOSS"}]},
        ))
        assert rows[0]["picked"] == "BURNING_BLOOD"
        assert rows[0]["source"] == "BOSS"

    def test_string_format(self):
        rows = _parse_relic_choices(RUN_ID, USER_ID, make_history(
            {"relic_choices": ["BURNING_BLOOD"]},
        ))
        assert rows[0]["picked"] == "BURNING_BLOOD"
        assert rows[0]["source"] == "UNKNOWN"


# ============================================================
# _parse_rest_site_choices
# ============================================================

class TestParseRestSiteChoices:
    def test_string_format(self):
        """'SMITH' のような文字列が直接 action になるケース"""
        rows = _parse_rest_site_choices(RUN_ID, USER_ID, make_history(
            {"rest_site_choices": ["SMITH"]},
        ))
        assert rows[0]["action"] == "SMITH"
        assert rows[0]["card_upgraded"] is None

    def test_dict_format(self):
        rows = _parse_rest_site_choices(RUN_ID, USER_ID, make_history(
            {"rest_site_choices": [{"action": "SMITH", "card_upgraded": "STRIKE+1"}]},
        ))
        assert rows[0]["action"] == "SMITH"
        assert rows[0]["card_upgraded"] == "STRIKE+1"

    def test_rest_action(self):
        rows = _parse_rest_site_choices(RUN_ID, USER_ID, make_history(
            {"rest_site_choices": [{"action": "REST"}]},
        ))
        assert rows[0]["action"] == "REST"
        assert rows[0]["card_upgraded"] is None


# ============================================================
# _parse_ancient_choices  ← 過去にバグがあった箇所
# ============================================================

class TestParseAncientChoices:
    def test_list_format(self):
        """
        実際のセーブファイル形式：
        ancient_choice が {TextKey, was_chosen} のリスト
        """
        history = make_history({
            "ancient_choice": [
                {"TextKey": "BOOMING_CONCH",      "was_chosen": False},
                {"TextKey": "ARCANE_SCROLL",       "was_chosen": True},
                {"TextKey": "PRECARIOUS_SHEARS",   "was_chosen": False},
            ]
        })
        rows = _parse_ancient_choices(RUN_ID, USER_ID, history)
        assert len(rows) == 1
        assert rows[0]["picked"] == "ARCANE_SCROLL"
        assert "BOOMING_CONCH" in rows[0]["not_picked"]
        assert "PRECARIOUS_SHEARS" in rows[0]["not_picked"]
        assert "ARCANE_SCROLL" not in rows[0]["not_picked"]
        assert rows[0]["ancient_id"] == ""

    def test_list_format_none_chosen(self):
        """was_chosen=True がない場合 picked は空文字"""
        history = make_history({
            "ancient_choice": [
                {"TextKey": "BOOMING_CONCH",    "was_chosen": False},
                {"TextKey": "ARCANE_SCROLL",     "was_chosen": False},
            ]
        })
        rows = _parse_ancient_choices(RUN_ID, USER_ID, history)
        assert rows[0]["picked"] == ""
        assert len(rows[0]["not_picked"]) == 2

    def test_string_format(self):
        rows = _parse_ancient_choices(RUN_ID, USER_ID, make_history(
            {"ancient_choice": "ARCANE_SCROLL"},
        ))
        assert rows[0]["picked"] == "ARCANE_SCROLL"
        assert rows[0]["not_picked"] == []
        assert rows[0]["ancient_id"] == ""

    def test_dict_format(self):
        rows = _parse_ancient_choices(RUN_ID, USER_ID, make_history(
            {"ancient_choice": {"ancient_id": "WATCHER", "picked": "A", "not_picked": ["B"]}},
        ))
        assert rows[0]["ancient_id"] == "WATCHER"
        assert rows[0]["picked"] == "A"
        assert rows[0]["not_picked"] == ["B"]

    def test_missing_returns_empty(self):
        assert _parse_ancient_choices(RUN_ID, USER_ID, make_history({})) == []

    def test_falsy_value_skipped(self):
        assert _parse_ancient_choices(RUN_ID, USER_ID, make_history({"ancient_choice": None})) == []


# ============================================================
# _parse_potion_events
# ============================================================

class TestParsePotionEvents:
    def test_use_and_discard(self):
        rows = _parse_potion_events(RUN_ID, USER_ID, make_history(
            {"potion_used": ["FIRE_POTION"], "potion_discarded": ["EXPLOSIVE_POTION"]},
        ))
        actions = {r["action"]: r["potion_id"] for r in rows}
        assert actions["USE"] == "FIRE_POTION"
        assert actions["DISCARD"] == "EXPLOSIVE_POTION"

    def test_dict_potion(self):
        rows = _parse_potion_events(RUN_ID, USER_ID, make_history(
            {"potion_used": [{"id": "FIRE_POTION"}]},
        ))
        assert rows[0]["potion_id"] == "FIRE_POTION"


# ============================================================
# _parse_event_choices
# ============================================================

class TestParseEventChoices:
    def test_dict_format(self):
        rows = _parse_event_choices(RUN_ID, USER_ID, make_history(
            {"event_choices": [{"event_id": "MUSHROOMS", "option_chosen": "EAT", "result": "HP_GAIN"}]},
        ))
        assert rows[0]["event_id"] == "MUSHROOMS"
        assert rows[0]["option_chosen"] == "EAT"
        assert rows[0]["result"] == "HP_GAIN"

    def test_string_format(self):
        rows = _parse_event_choices(RUN_ID, USER_ID, make_history(
            {"event_choices": ["EAT"]},
        ))
        assert rows[0]["option_chosen"] == "EAT"
        assert rows[0]["event_id"] == ""


# ============================================================
# _parse_shop_events
# ============================================================

class TestParseShopEvents:
    def test_buy_relic_string(self):
        rows = _parse_shop_events(RUN_ID, USER_ID, make_history(
            {"bought_relics": ["BURNING_BLOOD"]},
        ))
        assert rows[0]["action"] == "BUY_RELIC"
        assert rows[0]["item_id"] == "BURNING_BLOOD"

    def test_buy_relic_dict_with_cost(self):
        rows = _parse_shop_events(RUN_ID, USER_ID, make_history(
            {"bought_relics": [{"id": "BURNING_BLOOD", "cost": 150}]},
        ))
        assert rows[0]["cost"] == 150

    def test_purge_card(self):
        rows = _parse_shop_events(RUN_ID, USER_ID, make_history(
            {"cards_removed": ["STRIKE"]},
        ))
        assert rows[0]["action"] == "PURGE_CARD"
        assert rows[0]["item_id"] == "STRIKE"


# ============================================================
# _parse_card_enchantments
# ============================================================

class TestParseCardEnchantments:
    def test_upgraded_string(self):
        rows = _parse_card_enchantments(RUN_ID, USER_ID, make_history(
            {"upgraded_cards": ["STRIKE"]},
        ))
        assert rows[0]["enchantment"] == "UPGRADE"
        assert rows[0]["card_id"] == "STRIKE"

    def test_enchanted_dict(self):
        rows = _parse_card_enchantments(RUN_ID, USER_ID, make_history(
            {"cards_enchanted": [{"id": "DEFEND", "enchantment": "ETHEREAL"}]},
        ))
        assert rows[0]["enchantment"] == "ETHEREAL"
        assert rows[0]["card_id"] == "DEFEND"


# ============================================================
# _parse_deck_cards
# ============================================================

class TestParseDeckCards:
    def test_counts_duplicates(self):
        deck = [
            {"id": "STRIKE", "upgraded": False},
            {"id": "STRIKE", "upgraded": False},
            {"id": "STRIKE", "upgraded": True},
            {"id": "DEFEND", "upgraded": False},
        ]
        rows = _parse_deck_cards(RUN_ID, USER_ID, deck)
        by_key = {(r["card_id"], r["upgraded"]): r["count"] for r in rows}
        assert by_key[("STRIKE", False)] == 2
        assert by_key[("STRIKE", True)] == 1
        assert by_key[("DEFEND", False)] == 1

    def test_card_id_fallback(self):
        deck = [{"card_id": "BASH", "upgraded": False}]
        rows = _parse_deck_cards(RUN_ID, USER_ID, deck)
        assert rows[0]["card_id"] == "BASH"

    def test_empty_deck(self):
        assert _parse_deck_cards(RUN_ID, USER_ID, []) == []


# ============================================================
# _parse_final_relics / _parse_final_potions
# ============================================================

class TestParseFinalInventory:
    def test_relics_string(self):
        rows = _parse_final_relics(RUN_ID, USER_ID, ["BURNING_BLOOD", "RING_OF_SNAKE"])
        assert rows[0] == {"run_id": RUN_ID, "user_id": USER_ID, "relic_id": "BURNING_BLOOD", "slot": 0}
        assert rows[1]["slot"] == 1

    def test_relics_dict(self):
        rows = _parse_final_relics(RUN_ID, USER_ID, [{"id": "BURNING_BLOOD"}])
        assert rows[0]["relic_id"] == "BURNING_BLOOD"

    def test_relics_relic_id_key(self):
        rows = _parse_final_relics(RUN_ID, USER_ID, [{"relic_id": "ANCHOR"}])
        assert rows[0]["relic_id"] == "ANCHOR"

    def test_potions_string(self):
        rows = _parse_final_potions(RUN_ID, USER_ID, ["FIRE_POTION"])
        assert rows[0]["potion_id"] == "FIRE_POTION"

    def test_potions_dict(self):
        rows = _parse_final_potions(RUN_ID, USER_ID, [{"potion_id": "EXPLOSIVE_POTION"}])
        assert rows[0]["potion_id"] == "EXPLOSIVE_POTION"


# ============================================================
# 実際のセーブファイルに近いJSONサンプルを使った統合的なパーステスト
# ============================================================

SAMPLE_HISTORY = [
    # Act 1
    [
        {
            "map_point_type": "MONSTER",
            "encounter_id": "GREMLIN_GANG",
            "event_id": None,
            "player_stats": [{
                "current_hp": 60,
                "max_hp": 80,
                "current_gold": 100,
                "card_choices": [{"picked": "STRIKE", "not_picked": ["DEFEND", "BASH"]}],
                "relic_choices": [],
                "potion_choices": [],
                "potion_used": [],
                "potion_discarded": [],
                "rest_site_choices": [],
                "ancient_choice": None,
                "event_choices": [],
                "bought_relics": [],
                "cards_removed": [],
                "upgraded_cards": [],
                "cards_enchanted": [],
            }]
        },
        {
            "map_point_type": "REST",
            "encounter_id": None,
            "event_id": None,
            "player_stats": [{
                "current_hp": 70,
                "max_hp": 80,
                "current_gold": 100,
                "card_choices": [],
                "relic_choices": [],
                "potion_choices": [],
                "potion_used": [],
                "potion_discarded": [],
                "rest_site_choices": ["SMITH"],
                "ancient_choice": None,
                "event_choices": [],
                "bought_relics": [],
                "cards_removed": [],
                "upgraded_cards": ["STRIKE"],
                "cards_enchanted": [],
            }]
        },
        {
            "map_point_type": "ANCIENT",
            "encounter_id": None,
            "event_id": None,
            "player_stats": [{
                "current_hp": 70,
                "max_hp": 80,
                "current_gold": 80,
                "card_choices": [],
                "relic_choices": [],
                "potion_choices": [],
                "potion_used": [],
                "potion_discarded": [],
                "rest_site_choices": [],
                "ancient_choice": [
                    {"TextKey": "BOOMING_CONCH",    "was_chosen": False},
                    {"TextKey": "ARCANE_SCROLL",     "was_chosen": True},
                    {"TextKey": "PRECARIOUS_SHEARS", "was_chosen": False},
                ],
                "event_choices": [],
                "bought_relics": [],
                "cards_removed": [],
                "upgraded_cards": [],
                "cards_enchanted": [],
            }]
        },
    ]
]


class TestSampleHistory:
    def test_floor_count(self):
        rows = _parse_floor_events(RUN_ID, USER_ID, SAMPLE_HISTORY)
        assert len(rows) == 3

    def test_floor_numbers(self):
        rows = _parse_floor_events(RUN_ID, USER_ID, SAMPLE_HISTORY)
        assert [r["floor"] for r in rows] == [1, 2, 3]

    def test_card_choice_on_floor1(self):
        rows = _parse_card_choices(RUN_ID, USER_ID, SAMPLE_HISTORY)
        assert len(rows) == 1
        assert rows[0]["floor"] == 1
        assert rows[0]["picked"] == "STRIKE"

    def test_rest_site_on_floor2(self):
        rows = _parse_rest_site_choices(RUN_ID, USER_ID, SAMPLE_HISTORY)
        assert len(rows) == 1
        assert rows[0]["floor"] == 2
        assert rows[0]["action"] == "SMITH"

    def test_upgrade_on_floor2(self):
        rows = _parse_card_enchantments(RUN_ID, USER_ID, SAMPLE_HISTORY)
        assert len(rows) == 1
        assert rows[0]["floor"] == 2
        assert rows[0]["card_id"] == "STRIKE"

    def test_ancient_choice_on_floor3(self):
        rows = _parse_ancient_choices(RUN_ID, USER_ID, SAMPLE_HISTORY)
        assert len(rows) == 1
        assert rows[0]["floor"] == 3
        assert rows[0]["picked"] == "ARCANE_SCROLL"
        assert set(rows[0]["not_picked"]) == {"BOOMING_CONCH", "PRECARIOUS_SHEARS"}


# ============================================================
# played_at 変換ロジック（run_row 生成の単体テスト）
# ============================================================

def _build_played_at(save_data: dict) -> str:
    """runs.py の run_row 内の played_at 生成ロジックをそのまま抜き出した関数"""
    d = save_data
    return (
        datetime.fromtimestamp(d["start_time"], tz=timezone.utc).isoformat()
        if d.get("start_time") is not None
        else datetime.now(tz=timezone.utc).isoformat()
    )


class TestPlayedAt:
    def test_start_time_converted_to_iso(self):
        ts = 1773543372
        result = _build_played_at({"start_time": ts})
        expected = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        assert result == expected

    def test_start_time_zero_is_valid(self):
        result = _build_played_at({"start_time": 0})
        assert "1970-01-01" in result

    def test_missing_start_time_falls_back_to_now(self):
        before = datetime.now(tz=timezone.utc)
        result = _build_played_at({})
        after = datetime.now(tz=timezone.utc)
        dt = datetime.fromisoformat(result)
        assert before <= dt <= after

    def test_null_start_time_falls_back_to_now(self):
        before = datetime.now(tz=timezone.utc)
        result = _build_played_at({"start_time": None})
        after = datetime.now(tz=timezone.utc)
        dt = datetime.fromisoformat(result)
        assert before <= dt <= after

    def test_result_is_utc(self):
        result = _build_played_at({"start_time": 1773543372})
        assert "+00:00" in result or result.endswith("Z")
