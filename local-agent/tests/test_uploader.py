"""uploader.py のユニットテスト（httpx・config をモック）"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import config
import uploader


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    config_dir = tmp_path / ".sts2tracker"
    config_file = config_dir / "config.json"
    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)
    config_dir.mkdir()
    config_file.write_text(json.dumps({
        "user_id": "supabase-uid",
        "jwt": "valid-jwt",
        "refresh_token": "valid-refresh",
        "api_url": "https://api.example.com",
    }))
    return config_file


def make_response(status_code: int, body: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    resp.text = json.dumps(body or {})
    return resp


# ============================================================
# upload_file
# ============================================================

class TestUploadFile:
    def test_success_201(self, tmp_config, tmp_path):
        save_file = tmp_path / "run1.run"
        save_file.write_text(json.dumps({"players": []}))

        with patch("httpx.post", return_value=make_response(201)) as mock_post, \
             patch("offline_queue.mark_uploaded") as mock_mark:
            result = uploader.upload_file(str(save_file))

        assert result is True
        mock_mark.assert_called_once_with(str(save_file))

    def test_duplicate_409(self, tmp_config, tmp_path):
        save_file = tmp_path / "run1.run"
        save_file.write_text(json.dumps({}))

        with patch("httpx.post", return_value=make_response(409)), \
             patch("offline_queue.mark_uploaded") as mock_mark:
            result = uploader.upload_file(str(save_file))

        assert result is True
        mock_mark.assert_called_once()

    def test_offline_connect_error(self, tmp_config, tmp_path):
        import httpx
        save_file = tmp_path / "run1.run"
        save_file.write_text(json.dumps({}))

        with patch("httpx.post", side_effect=httpx.ConnectError("unreachable")):
            result = uploader.upload_file(str(save_file))

        assert result is False

    def test_missing_file_marks_uploaded(self, tmp_config):
        with patch("offline_queue.mark_uploaded") as mock_mark:
            result = uploader.upload_file("/nonexistent/file.run")
        assert result is True
        mock_mark.assert_called_once()

    def test_no_jwt_returns_false(self, tmp_config):
        # JWT を消す
        tmp_config.write_text(json.dumps({"user_id": "uid", "api_url": "https://api.example.com"}))
        result = uploader.upload_file("/some/file.run")
        assert result is False

    def test_401_refresh_success_then_retry_201(self, tmp_config, tmp_path):
        """401 → refresh_token → リトライ成功の流れ"""
        save_file = tmp_path / "run1.run"
        save_file.write_text(json.dumps({}))

        refresh_response_data = {
            "user_id": "supabase-uid",
            "jwt": "new-jwt",
            "refresh_token": "new-refresh",
        }

        responses = [
            make_response(401),          # 初回: 401
            make_response(200, refresh_response_data),  # refresh エンドポイント
            make_response(201),          # リトライ: 成功
        ]

        with patch("httpx.post", side_effect=responses), \
             patch("offline_queue.mark_uploaded") as mock_mark:
            result = uploader.upload_file(str(save_file))

        assert result is True
        mock_mark.assert_called_once()

    def test_401_refresh_fail_returns_false(self, tmp_config, tmp_path):
        """401 → refresh_token 失敗 → False"""
        save_file = tmp_path / "run1.run"
        save_file.write_text(json.dumps({}))

        responses = [
            make_response(401),   # 初回: 401
            make_response(401),   # refresh も失敗
        ]

        with patch("httpx.post", side_effect=responses):
            result = uploader.upload_file(str(save_file))

        assert result is False

    def test_500_returns_false(self, tmp_config, tmp_path):
        save_file = tmp_path / "run1.run"
        save_file.write_text(json.dumps({}))

        with patch("httpx.post", return_value=make_response(500)):
            result = uploader.upload_file(str(save_file))

        assert result is False


# ============================================================
# refresh_token
# ============================================================

class TestRefreshToken:
    def test_success(self, tmp_config):
        data = {"user_id": "uid", "jwt": "new-jwt", "refresh_token": "new-refresh"}
        with patch("httpx.post", return_value=make_response(200, data)):
            result = uploader.refresh_token()
        assert result is True
        assert config.get_jwt() == "new-jwt"
        assert config.get_refresh_token() == "new-refresh"

    def test_no_refresh_token_returns_false(self, tmp_config):
        tmp_config.write_text(json.dumps({"user_id": "uid", "jwt": "j"}))
        result = uploader.refresh_token()
        assert result is False

    def test_server_error_returns_false(self, tmp_config):
        with patch("httpx.post", return_value=make_response(401)):
            result = uploader.refresh_token()
        assert result is False

    def test_connect_error_returns_false(self, tmp_config):
        import httpx
        with patch("httpx.post", side_effect=httpx.ConnectError("down")):
            result = uploader.refresh_token()
        assert result is False


# ============================================================
# register_user
# ============================================================

class TestRegisterUser:
    def test_success_saves_auth(self, tmp_config):
        data = {"user_id": "new-uid", "jwt": "new-jwt", "refresh_token": "new-ref"}
        with patch("httpx.post", return_value=make_response(200, data)):
            result = uploader.register_user("local-uuid")
        assert result is True
        assert config.get_user_id() == "new-uid"
        assert config.get_jwt() == "new-jwt"

    def test_server_error_returns_false(self, tmp_config):
        with patch("httpx.post", return_value=make_response(500)):
            result = uploader.register_user("local-uuid")
        assert result is False

    def test_connect_error_returns_false(self, tmp_config):
        import httpx
        with patch("httpx.post", side_effect=httpx.ConnectError("down")):
            result = uploader.register_user("local-uuid")
        assert result is False


# ============================================================
# migrate_user
# ============================================================

class TestMigrateUser:
    def test_success(self, tmp_config):
        data = {
            "migrated_from": "old-uid",
            "migrated_to": "new-uid",
            "updated_tables": ["runs", "floor_events"],
        }
        with patch("httpx.post", return_value=make_response(200, data)) as mock_post:
            result = uploader.migrate_user("old-uid", "new-uid", "new-jwt")

        assert result is True
        call_kwargs = mock_post.call_args
        # Authorization ヘッダーに新しいJWTが含まれることを確認
        assert "Bearer new-jwt" in call_kwargs.kwargs.get("headers", {}).get("Authorization", "")
        # リクエストボディに old/new が含まれることを確認
        body = call_kwargs.kwargs.get("json", {})
        assert body["old_user_id"] == "old-uid"
        assert body["new_user_id"] == "new-uid"

    def test_server_error_returns_false(self, tmp_config):
        with patch("httpx.post", return_value=make_response(403)):
            result = uploader.migrate_user("old", "new", "jwt")
        assert result is False

    def test_connect_error_returns_false(self, tmp_config):
        import httpx
        with patch("httpx.post", side_effect=httpx.ConnectError("down")):
            result = uploader.migrate_user("old", "new", "jwt")
        assert result is False
