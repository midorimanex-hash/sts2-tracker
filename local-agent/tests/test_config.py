"""config.py のユニットテスト"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import config


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """CONFIG_DIR / CONFIG_FILE を一時ディレクトリに差し替える"""
    config_dir = tmp_path / ".sts2tracker"
    config_file = config_dir / "config.json"
    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)
    return config_file


# ============================================================
# get_user_id
# ============================================================

class TestGetUserId:
    def test_returns_none_when_config_missing(self, tmp_config):
        assert config.get_user_id() is None

    def test_returns_none_when_user_id_key_absent(self, tmp_config):
        tmp_config.parent.mkdir(parents=True)
        tmp_config.write_text(json.dumps({"jwt": "tok"}))
        assert config.get_user_id() is None

    def test_returns_saved_user_id(self, tmp_config):
        tmp_config.parent.mkdir(parents=True)
        tmp_config.write_text(json.dumps({"user_id": "abc-123"}))
        assert config.get_user_id() == "abc-123"


# ============================================================
# get_or_create_user_id
# ============================================================

class TestGetOrCreateUserId:
    def test_creates_uuid_on_first_call(self, tmp_config):
        uid = config.get_or_create_user_id()
        assert len(uid) == 36  # UUID4 の長さ
        # ファイルに保存されている
        saved = json.loads(tmp_config.read_text())
        assert saved["user_id"] == uid

    def test_returns_existing_user_id(self, tmp_config):
        tmp_config.parent.mkdir(parents=True)
        tmp_config.write_text(json.dumps({"user_id": "existing-id"}))
        assert config.get_or_create_user_id() == "existing-id"

    def test_does_not_overwrite_existing(self, tmp_config):
        tmp_config.parent.mkdir(parents=True)
        tmp_config.write_text(json.dumps({"user_id": "do-not-change"}))
        config.get_or_create_user_id()
        saved = json.loads(tmp_config.read_text())
        assert saved["user_id"] == "do-not-change"


# ============================================================
# save_auth / get_jwt / get_refresh_token
# ============================================================

class TestSaveAuth:
    def test_saves_all_fields(self, tmp_config):
        config.save_auth(user_id="uid-1", jwt="jwt-tok", refresh_token="ref-tok")
        saved = json.loads(tmp_config.read_text())
        assert saved["user_id"] == "uid-1"
        assert saved["jwt"] == "jwt-tok"
        assert saved["refresh_token"] == "ref-tok"

    def test_get_jwt_returns_saved(self, tmp_config):
        config.save_auth(user_id="u", jwt="my-jwt", refresh_token="r")
        assert config.get_jwt() == "my-jwt"

    def test_get_jwt_returns_none_when_missing(self, tmp_config):
        assert config.get_jwt() is None

    def test_get_refresh_token_returns_saved(self, tmp_config):
        config.save_auth(user_id="u", jwt="j", refresh_token="my-refresh")
        assert config.get_refresh_token() == "my-refresh"

    def test_save_auth_overwrites_user_id(self, tmp_config):
        """register 後にローカルUUIDがSupabase UUIDで上書きされることを確認"""
        tmp_config.parent.mkdir(parents=True)
        tmp_config.write_text(json.dumps({"user_id": "local-uuid"}))
        config.save_auth(user_id="supabase-uuid", jwt="j", refresh_token="r")
        assert config.get_user_id() == "supabase-uuid"


# ============================================================
# get_dashboard_url
# ============================================================

class TestGetDashboardUrl:
    def test_returns_base_url_without_user_id(self, tmp_config):
        url = config.get_dashboard_url()
        assert url == config.DASHBOARD_URL

    def test_returns_url_with_uid_param(self, tmp_config):
        config.save_auth(user_id="uid-xyz", jwt="j", refresh_token="r")
        url = config.get_dashboard_url()
        assert url == f"{config.DASHBOARD_URL}/me?uid=uid-xyz"

    def test_no_jwt_in_url(self, tmp_config):
        """JWTがURLに含まれないことを確認（セキュリティ）"""
        config.save_auth(user_id="uid-xyz", jwt="super-secret-jwt", refresh_token="r")
        url = config.get_dashboard_url()
        assert "super-secret-jwt" not in url
        assert "token=" not in url
