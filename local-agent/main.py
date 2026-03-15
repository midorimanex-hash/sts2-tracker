from __future__ import annotations

import logging
import threading
import time
import webbrowser
from io import BytesIO

import psutil
import pystray
from PIL import Image, ImageDraw

import config
import offline_queue as q
import uploader
from watcher import STS2Watcher

# ============================================================
# ログ設定
# ============================================================
LOG_FILE = config.CONFIG_DIR / "sts2tracker.log"
config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ============================================================
# 定数
# ============================================================
STS2_PROCESS = "SlayTheSpire2.exe"
FLUSH_INTERVAL = 60        # キュー再送信間隔（秒）
PROCESS_CHECK_INTERVAL = 5 # STS2プロセス監視間隔（秒）


# ============================================================
# タスクトレイアイコン画像（PIL で生成）
# ============================================================

def _make_icon_image(active: bool = True) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (80, 200, 120) if active else (120, 120, 120)  # 緑=監視中・グレー=待機
    draw.ellipse([4, 4, 60, 60], fill=color)
    draw.text((18, 20), "S2", fill=(255, 255, 255))
    return img


# ============================================================
# STS2プロセス監視スレッド
# ============================================================

def _is_sts2_running() -> bool:
    return any(p.name() == STS2_PROCESS for p in psutil.process_iter(["name"]))


def _process_monitor(watcher: STS2Watcher, tray: pystray.Icon, stop_event: threading.Event) -> None:
    """
    STS2の起動・終了を監視して watchdog を制御する。
    STS2起動中のみ watcher をアクティブにする。
    """
    was_running = False
    while not stop_event.is_set():
        now_running = _is_sts2_running()

        if now_running and not was_running:
            logger.info("STS2起動を検知。監視を開始します。")
            watcher.scan_existing()  # 起動時に既存未送信ファイルをチェック
            watcher.start()
            tray.icon = _make_icon_image(active=True)
            tray.title = "STS2 Tracker — 監視中"

        elif not now_running and was_running:
            logger.info("STS2終了を検知。監視を停止します。")
            watcher.stop()
            uploader.flush_queue()  # 終了時にキューを一括送信
            tray.icon = _make_icon_image(active=False)
            tray.title = "STS2 Tracker — 待機中"

        was_running = now_running
        stop_event.wait(PROCESS_CHECK_INTERVAL)


# ============================================================
# キュー再送信スレッド（定期的にオフラインキューをフラッシュ）
# ============================================================

def _queue_flusher(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        stop_event.wait(FLUSH_INTERVAL)
        if not stop_event.is_set():
            uploader.flush_queue()


# ============================================================
# 初回セットアップ（UUID生成・ユーザー登録）
# ============================================================

def _setup() -> None:
    existing_user_id = config.get_user_id()

    if existing_user_id is None:
        # 未登録：新規ユーザー登録
        local_user_id = config.get_or_create_user_id()
        logger.info(f"初回起動。ユーザー登録を試みます。(local_id={local_user_id})")
        success = uploader.register_user(local_user_id)
        if not success:
            logger.warning("サーバーに接続できません。次回起動時に再試行します。")
    else:
        logger.info(f"ユーザーID: {existing_user_id}")
        if config.get_jwt() is None:
            # user_id は既にある → 新規登録せずJWTを復元する
            recovered = False

            # 1st: refresh_token があればリフレッシュを試みる
            if config.get_refresh_token():
                logger.info("JWTなし。リフレッシュトークンでJWT取得を試みます。")
                recovered = uploader.refresh_token()

            # 2nd: リフレッシュ失敗 or refresh_token なし → 新規登録 + データ移行
            if not recovered:
                logger.warning(
                    "リフレッシュ失敗または refresh_token なし。"
                    "新規ユーザーを作成して旧データを移行します。"
                )
                tmp_id = config.get_or_create_user_id()
                registered = uploader.register_user(tmp_id)
                if registered:
                    new_user_id = config.get_user_id()
                    new_jwt = config.get_jwt()
                    if new_user_id and new_jwt and new_user_id != existing_user_id:
                        uploader.migrate_user(existing_user_id, new_user_id, new_jwt)
                    recovered = True

            if not recovered:
                logger.warning("JWT取得失敗。次回起動時に再試行します。")


# ============================================================
# タスクトレイメニュー
# ============================================================

def _build_menu(watcher: STS2Watcher, stop_event: threading.Event) -> pystray.Menu:
    def open_dashboard(icon, item):
        webbrowser.open(config.get_dashboard_url())

    def flush_now(icon, item):
        threading.Thread(target=uploader.flush_queue, daemon=True).start()

    def quit_app(icon, item):
        logger.info("終了します。")
        stop_event.set()
        watcher.stop()
        icon.stop()

    return pystray.Menu(
        pystray.MenuItem("統計を見る", open_dashboard, default=True),
        pystray.MenuItem("今すぐ同期", flush_now),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("終了", quit_app),
    )


# ============================================================
# エントリポイント
# ============================================================

def main() -> None:
    q.init_db()
    _setup()

    watcher = STS2Watcher()
    stop_event = threading.Event()

    # STS2が既に起動中なら即座に監視開始
    if _is_sts2_running():
        logger.info("STS2が既に起動中。即座に監視を開始します。")
        watcher.scan_existing()
        watcher.start()
        initial_active = True
    else:
        initial_active = False

    # タスクトレイアイコン
    tray = pystray.Icon(
        name="STS2 Tracker",
        icon=_make_icon_image(active=initial_active),
        title="STS2 Tracker — 監視中" if initial_active else "STS2 Tracker — 待機中",
        menu=_build_menu(watcher, stop_event),
    )

    # バックグラウンドスレッド起動
    threading.Thread(
        target=_process_monitor,
        args=(watcher, tray, stop_event),
        daemon=True,
    ).start()

    threading.Thread(
        target=_queue_flusher,
        args=(stop_event,),
        daemon=True,
    ).start()

    logger.info("STS2 Tracker 起動完了。タスクトレイに常駐します。")
    tray.run()  # メインスレッドでタスクトレイを実行（ブロッキング）


if __name__ == "__main__":
    main()
