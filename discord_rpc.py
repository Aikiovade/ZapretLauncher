"""G12: Discord Rich Presence — опциональная интеграция через pypresence (IPC).

Правила безопасности/тишины:
- нет библиотеки pypresence, нет client_id или Discord не запущен → тихий no-op;
- исключения глушатся, в лог ничего не пишется (не спамим);
- обновления троттлятся (не чаще min_interval секунд) и отправляется последний payload;
- поток daemon, приложение не ждёт его завершения.
"""
from __future__ import annotations

import threading
import time

try:
    from pypresence import Presence as _RPC
    PYPRESENCE_AVAILABLE = True
except Exception:
    _RPC = None  # type: ignore[assignment,misc]
    PYPRESENCE_AVAILABLE = False

DEFAULT_REPO_URL = "https://github.com/Aikiovade/ZapretLauncher"
INSTALL_BUTTON_LABEL = "Установить ZapretLauncher"
RECONNECT_BACKOFF_SEC = 60.0


class DiscordPresence:
    """Обновление presence в фоновом потоке с троттлингом и тихими ошибками."""

    def __init__(self, client_id="", min_interval=15.0, repo_url=DEFAULT_REPO_URL):
        self.client_id = str(client_id or "").strip()
        self.min_interval = max(1.0, float(min_interval))
        self.repo_url = repo_url or DEFAULT_REPO_URL
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._pending = None
        self._thread = None
        self._rpc = None
        self._last_sent = 0.0
        self._next_connect_at = 0.0
        self._stopped = False

    @property
    def available(self):
        return PYPRESENCE_AVAILABLE and bool(self.client_id) and not self._stopped

    def start(self):
        if not self.available:
            return False
        if self._thread is not None and self._thread.is_alive():
            return True
        self._thread = threading.Thread(target=self._loop, name="discord-rpc", daemon=True)
        self._thread.start()
        return True

    def update(self, details=None, state=None, start=None, buttons=True, force=False):
        """Поставить актуальный payload; поток отправит его с учётом троттлинга."""
        if not self.available:
            return False
        payload = {"details": details, "state": state}
        if start:
            payload["start"] = int(start)
        if buttons:
            payload["buttons"] = [{"label": INSTALL_BUTTON_LABEL, "url": self.repo_url}]
        with self._lock:
            self._pending = payload
            if force:
                self._last_sent = 0.0
        self.start()
        self._wake.set()
        return True

    def close(self):
        self._stopped = True
        self._wake.set()
        with self._lock:
            rpc, self._rpc = self._rpc, None
        if rpc is not None:
            try:
                rpc.clear()
            except Exception:
                pass
            try:
                rpc.close()
            except Exception:
                pass

    # ---------- worker ----------
    def _loop(self):
        while not self._stopped:
            self._wake.wait()
            self._wake.clear()
            if self._stopped:
                return
            with self._lock:
                payload = self._pending
            if payload is None:
                continue
            wait = self._last_sent + self.min_interval - time.time()
            if wait > 0:
                time.sleep(wait)
            if self._stopped:
                return
            with self._lock:
                payload = self._pending or payload
            if not self._ensure_connected():
                continue
            try:
                self._rpc.update(**payload)
                self._last_sent = time.time()
            except Exception:
                self._drop_connection()

    def _ensure_connected(self):
        if self._rpc is not None:
            return True
        if time.time() < self._next_connect_at:
            return False
        try:
            rpc = _RPC(self.client_id)
            rpc.connect()
            self._rpc = rpc
            return True
        except Exception:
            self._rpc = None
            self._next_connect_at = time.time() + RECONNECT_BACKOFF_SEC
            return False

    def _drop_connection(self):
        rpc, self._rpc = self._rpc, None
        if rpc is not None:
            try:
                rpc.close()
            except Exception:
                pass
        self._next_connect_at = time.time() + RECONNECT_BACKOFF_SEC
