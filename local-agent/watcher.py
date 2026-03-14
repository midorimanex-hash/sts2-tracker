from __future__ import annotations

import logging
import threading
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

import offline_queue as q
import uploader

logger = logging.getLogger(__name__)

STS2_PROCESS_NAME = "SlayTheSpire2.exe"


def find_history_dirs() -> list[Path]:
    """
    AppData/Roaming/SlayTheSpire2/steam/{steamID}/profile1/saves/history/
    を全SteamIDぶん返す。
    """
    appdata = Path.home() / "AppData" / "Roaming" / "SlayTheSpire2" / "steam"
    if not appdata.exists():
        return []
    dirs = []
    for steam_dir in appdata.iterdir():
        if not steam_dir.is_dir():
            continue
        history = steam_dir / "profile1" / "saves" / "history"
        if history.exists():
            dirs.append(history)
    return dirs


class RunFileHandler(FileSystemEventHandler):
    """
    history フォルダ内の .run ファイルを監視する。
    作成・更新を検知したらキューに追加してアップロードを試みる。
    """

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory and event.src_path.endswith(".run"):
            self._handle(event.src_path)

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.is_directory and event.src_path.endswith(".run"):
            self._handle(event.src_path)

    def _handle(self, file_path: str) -> None:
        if q.is_uploaded(file_path):
            return
        logger.info(f"新しいrunファイルを検知: {Path(file_path).name}")
        q.enqueue(file_path)
        uploader.upload_file(file_path)


class STS2Watcher:
    """
    watchdog Observerのライフサイクルを管理する。
    start() / stop() で監視の開始・停止ができる。
    """

    def __init__(self) -> None:
        self._observer: Observer | None = None
        self._lock = threading.Lock()
        self._history_dirs = find_history_dirs()

    def start(self) -> None:
        with self._lock:
            if self._observer is not None:
                return  # 既に起動中
            if not self._history_dirs:
                logger.warning("historyフォルダが見つかりません。STS2を一度起動してください。")
                return

            self._observer = Observer()
            handler = RunFileHandler()
            for d in self._history_dirs:
                self._observer.schedule(handler, str(d), recursive=False)
                logger.info(f"監視開始: {d}")
            self._observer.start()

    def stop(self) -> None:
        with self._lock:
            if self._observer is None:
                return
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("監視停止")

    def is_running(self) -> bool:
        with self._lock:
            return self._observer is not None

    def scan_existing(self) -> None:
        """
        起動時に既存の未送信ファイルをキューに追加する。
        historyフォルダが後から作成された場合にも対応。
        """
        self._history_dirs = find_history_dirs()
        for d in self._history_dirs:
            for run_file in d.glob("*.run"):
                if not q.is_uploaded(str(run_file)):
                    q.enqueue(str(run_file))
        count = len(q.get_pending())
        if count:
            logger.info(f"未送信ファイル {count}件 をキューに追加しました。")
