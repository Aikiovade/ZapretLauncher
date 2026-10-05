"""ZapretLauncher Web UI (A7 spike): pywebview + WebView2.

Запуск (от администратора): python webapp.py
Общая логика службы берётся из zapret_new_win.py; конфиг — общий.
"""
import ctypes
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time

import discord_rpc
import zapret_new_win as core

try:
    import webview
except Exception:
    webview = None  # type: ignore[assignment]

PROXY_EXE = core.TGWS_PROXY_EXE

STATUS_TEXT = {
    "ready": "ГОТОВ", "on": "ВКЛ", "busy": "...", "error": "ОШИБКА",
    "no_file": "НЕТ ФАЙЛА", "fail": "СБОЙ",
}


class Api:
    def __init__(self):
        self.window = None
        self.lang = "RU"
        self.theme = core.DEFAULT_THEME
        self.theme_custom = ""
        self.status = "OFF"
        self.status_key = "ready"
        self.status_text = STATUS_TEXT["ready"]
        self.start_time = 0.0
        self.selected_bat = core.DEFAULT_BAT
        self.favorite_bat = None
        self.desired_bypass = True
        self.auto_restart = True
        self.autorun_enabled = True
        self.notifications_enabled = True
        self.minimal_mode = False
        self.snow_enabled = True
        self.start_minimized = False
        self.proxy_enabled = False
        self.proxy_pid = None
        self.hud = {"CPU": "0", "RAM": "0", "PING": "---", "BYPASS": "---"}
        self.test_state = {"running": False, "line": "", "progress": 0, "total": 0}
        self.services = {}
        self.autotest = {"running": False, "index": 0, "total": 0, "strategy": "", "best": None, "best_score": -1.0}
        self.update_info = None
        self.update_channel = core.DEFAULT_UPDATE_CHANNEL
        self._cmd_queue = queue.Queue()
        self._compact = False
        self._pre_compact = None
        self.strategy_scores = {}
        self.quality = "auto"
        self.theme_mode = "dark"
        self.hotkey_toggle = "Ctrl+Shift+Z"
        self.battery_saver = True
        self.battery = {"present": False, "on_battery": False, "percent": None}
        self.idle_hide_min = 0
        self._idle_hidden = False
        self.gaming_mode = False
        self.ui_mode = "advanced"
        self.game_active = False
        self.speedtest_history = []
        self.auto_rotate = False
        self._rotate_fail_streak = 0
        self.discord_rpc = False
        self.intro_enabled = True
        self.discord_client_id = ""
        self.discord = None
        self._discord_ts = 0.0
        self.backend = core.get_backend()
        self.tray = None
        self.zapret_dir = core.locate_zapret_dir()
        self._load_config()
        self._apply_discord_setting()
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        threading.Thread(target=self._watchdog_loop, daemon=True).start()
        threading.Thread(target=self._command_loop, daemon=True).start()
        self.interfaces = core.list_active_interfaces()
        self.network = core.get_current_network()
        key = self.network.get("network_key")
        if key in self.profiles and self.profiles[key] in core.list_strategies(self.zapret_dir):
            self.selected_bat = self.profiles[key]
        if len(self.interfaces) > 1:
            core.log_error(f"Активные сетевые интерфейсы: {', '.join(self.interfaces)}")
        if self.proxy_enabled:
            self._submit("proxy")

    # ---------- config ----------
    def _load_config(self):
        self.profiles = {}
        try:
            if os.path.exists(core.CONFIG_PATH):
                with open(core.CONFIG_PATH, encoding="utf-8") as f:
                    d = json.load(f)
                self.lang = d.get("lang", "RU")
                self.theme = d.get("theme", core.DEFAULT_THEME)
                self.theme_custom = d.get("theme_custom", "")
                self.selected_bat = d.get("bat", core.DEFAULT_BAT)
                self.favorite_bat = d.get("fav")
                self.desired_bypass = d.get("desired_bypass", True)
                self.auto_restart = d.get("auto_restart", True)
                self.autorun_enabled = d.get("autorun", True)
                self.notifications_enabled = d.get("notifications", True)
                self.minimal_mode = d.get("minimal", False)
                self.snow_enabled = d.get("snow", True)
                self.start_minimized = d.get("minimized", False)
                self.proxy_enabled = d.get("proxy_enabled", False)
                self.profiles = d.get("profiles", {})
                self.strategy_scores = d.get("scores", {}) or {}
                self.update_channel = d.get("update_channel", core.DEFAULT_UPDATE_CHANNEL)
                self.quality = d.get("quality", "auto")
                self.theme_mode = d.get("theme_mode", "dark")
                self.hotkey_toggle = d.get("hotkey_toggle", "Ctrl+Shift+Z")
                self.battery_saver = d.get("battery_saver", True)
                self.idle_hide_min = int(d.get("idle_hide_min", 0) or 0)
                self.gaming_mode = d.get("gaming_mode", False)
                self.ui_mode = d.get("ui_mode", "advanced")
                self.speedtest_history = d.get("speedtest_history", []) or []
                self.auto_rotate = d.get("auto_rotate", False)
                self.discord_rpc = bool(d.get("discord_rpc", False))
                self.discord_client_id = str(d.get("discord_client_id", "") or "")
                self.intro_enabled = bool(d.get("intro", True))
        except Exception as e:
            core.log_error(f"webapp load config: {e}")

    def _save_config(self):
        try:
            os.makedirs(core.APP_DATA_DIR, exist_ok=True)
            data = {}
            if os.path.exists(core.CONFIG_PATH):
                try:
                    with open(core.CONFIG_PATH, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data.update({
                "schema_version": core.CONFIG_SCHEMA_VERSION,
                "lang": self.lang,                 "theme": self.theme, "theme_custom": self.theme_custom, "bat": self.selected_bat,
                "fav": self.favorite_bat, "desired_bypass": self.desired_bypass,
                "auto_restart": self.auto_restart, "autorun": self.autorun_enabled,
                "notifications": self.notifications_enabled, "minimal": self.minimal_mode,
                "snow": self.snow_enabled, "minimized": self.start_minimized,
                "proxy_enabled": self.proxy_enabled,
                "profiles": self.profiles,
                "scores": self.strategy_scores,
                "update_channel": self.update_channel,
                "quality": self.quality,
                "theme_mode": self.theme_mode,
                "hotkey_toggle": self.hotkey_toggle,
                "battery_saver": self.battery_saver,
                "idle_hide_min": self.idle_hide_min,
                "gaming_mode": self.gaming_mode,
                "ui_mode": self.ui_mode,
                "speedtest_history": self.speedtest_history,
                "auto_rotate": self.auto_rotate,
                "discord_rpc": self.discord_rpc,
                "discord_client_id": self.discord_client_id,
                "intro": self.intro_enabled,
            })
            tmp = core.CONFIG_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, core.CONFIG_PATH)
        except Exception as e:
            core.log_error(f"webapp save config: {e}")

    # ---------- api: state ----------
    def get_state(self):
        uptime = int(time.time() - self.start_time) if self.status == "ON" and self.start_time else 0
        return {
            "version": core.CURRENT_VERSION,
            "first_run": not os.path.exists(core.CONFIG_PATH),
            "status": self.status,
            "status_key": self.status_key,
            "status_text": self.status_text,
            "strategy": self.selected_bat,
            "favorite": self.favorite_bat,
            "uptime": uptime,
            "hud": self.hud,
            "proxy": "ON" if self.proxy_pid else "OFF",
            "test": self.test_state,
            "services": self.services,
            "autotest": self.autotest,
            "interfaces": self.interfaces,
            "network": self.network,
            "profiles": self.profiles,
            "scores": self.strategy_scores,
            "compact": self._compact,
            "update_channel": self.update_channel,
            "rollback_available": os.path.exists(core.current_exe_path() + ".old"),
            "quality": self.quality,
            "effective_quality": self._effective_quality(),
            "battery": self.battery,
            "idle_hide_min": self.idle_hide_min,
            "gaming_mode": self.gaming_mode,
            "game_active": self.game_active,
            "package": os.path.basename(self.zapret_dir or ""),
            "backend": self.backend.name,
            "strategy_meta": core.load_strategy_meta(self.zapret_dir),
            "auto_rotate": self.auto_rotate,
            "discord": {
                "enabled": bool(self.discord_rpc),
                "active": bool(self.discord is not None and self.discord.available),
                "client_id_set": bool(self._discord_id()),
                "lib_available": bool(discord_rpc.PYPRESENCE_AVAILABLE),
            },
            "update_mode": core.update_mode(),
            "data_dir_mode": core.data_dir_mode(),
            "installer_update": core.installer_update_available(self.update_info or {}),
            "update_available": bool(self.update_info),
            "remote_version": (self.update_info or {}).get("version"),
            "strategies": core.list_strategies(self.zapret_dir),
            "settings": {
                "lang": self.lang, "theme": self.theme, "theme_custom": self.theme_custom,
                "autorun": self.autorun_enabled,
                "notifications": self.notifications_enabled, "auto_restart": self.auto_restart,
                "minimal": self.minimal_mode, "snow": self.snow_enabled,
                "minimized": self.start_minimized,
                "theme_mode": self.theme_mode, "hotkey_toggle": self.hotkey_toggle,
                "battery_saver": self.battery_saver, "gaming_mode": self.gaming_mode,
                "ui_mode": self.ui_mode, "discord_rpc": self.discord_rpc,
                "intro": self.intro_enabled,
            },
            "themes": core.THEMES_DATA,
            "texts": core.TRANSLATIONS_DATA.get(self.lang, core.TRANSLATIONS_DATA["EN"]),
        }

    # ---------- api: actions ----------
    # Единственный писатель статуса — поток _command_loop (single-writer).
    def _transition(self, status, key=None):
        self.status = status
        self.status_key = key or status.lower()
        self.status_text = STATUS_TEXT.get(self.status_key, self.status_text)
        core.log_event("transition", status=status, key=self.status_key, strategy=self.selected_bat)
        self._update_discord(force=True)
        if self.status_key in ("on", "ready") and self.notifications_enabled and self.tray is not None:
            texts = core.TRANSLATIONS_DATA.get(self.lang, core.TRANSLATIONS_DATA["EN"])
            body = texts.get("notify_on" if self.status_key == "on" else "notify_off", "")
            try:
                threading.Thread(target=self.tray.notify, args=(body, "ZapretLauncher"), daemon=True).start()
            except Exception:
                pass
        self._refresh_tray()

    def _submit(self, cmd, data=None, wait=False, timeout=30.0):
        ev = threading.Event()
        box = {}
        self._cmd_queue.put((cmd, data, ev, box))
        if not wait:
            return {"ok": True, "queued": True}
        ev.wait(timeout)
        return box.get("result") or {"ok": False}

    def _command_loop(self):
        while True:
            cmd, data, ev, box = self._cmd_queue.get()
            try:
                box["result"] = self._dispatch_command(cmd, data)
            except Exception as e:
                core.log_error(f"webapp command {cmd}: {e}")
                box["result"] = {"ok": False}
            finally:
                ev.set()

    def _dispatch_command(self, cmd, data):
        if cmd == "start":
            return self._do_start()
        if cmd == "stop":
            return self._do_stop()
        if cmd == "restart":
            self._do_stop()
            return self._do_start()
        if cmd == "fail":
            self._transition("OFF", "fail")
            return {"ok": True}
        if cmd == "proxy":
            return self._do_proxy_toggle()
        return {"ok": False}

    def toggle(self):
        if self.status == "BUSY" or not self._cmd_queue.empty():
            return {"ok": False}
        if self.test_state["running"] or self.autotest.get("running"):
            return {"ok": False}
        self._submit("stop" if self.status == "ON" else "start")
        return {"ok": True}

    def _do_start(self):
        self._transition("BUSY", "busy")
        try:
            bat_path = os.path.join(self.zapret_dir, self.selected_bat)
            if not os.path.exists(bat_path):
                self._transition("OFF", "no_file")
                return {"ok": False}
            ok = self.backend.start(self.zapret_dir, bat_path)
            if ok:
                self.start_time = time.time()
                self.desired_bypass = True
                self._transition("ON", "on")
                self._save_config()
                return {"ok": True}
            self._transition("OFF", "error")
            return {"ok": False}
        except Exception as e:
            core.log_error(f"webapp start: {e}")
            self._transition("OFF", "error")
            return {"ok": False}

    def _do_stop(self):
        try:
            self.backend.stop()
        except Exception as e:
            core.log_error(f"webapp stop: {e}")
        self.desired_bypass = False
        self._transition("OFF", "ready")
        self._save_config()
        return {"ok": True}

    def select_strategy(self, name):
        if name in core.list_strategies(self.zapret_dir):
            self.selected_bat = name
            self._save_config()
            self._update_discord(force=True)
            return {"ok": True}
        return {"ok": False}

    def set_favorite(self):
        self.favorite_bat = None if self.favorite_bat == self.selected_bat else self.selected_bat
        self._save_config()
        return {"ok": True, "favorite": self.favorite_bat}

    def set_setting(self, key, value):
        mapping = {
            "lang": "lang",                 "theme": "theme", "theme_custom": "theme_custom", "autorun": "autorun_enabled",
            "notifications": "notifications_enabled", "auto_restart": "auto_restart",
            "minimal": "minimal_mode", "snow": "snow_enabled", "minimized": "start_minimized",
            "update_channel": "update_channel", "quality": "quality",
            "theme_mode": "theme_mode", "hotkey_toggle": "hotkey_toggle",
            "battery_saver": "battery_saver", "idle_hide_min": "idle_hide_min",
            "gaming_mode": "gaming_mode", "ui_mode": "ui_mode",
            "auto_rotate": "auto_rotate", "discord_rpc": "discord_rpc",
            "intro": "intro_enabled",
        }
        if key not in mapping:
            return {"ok": False}
        if key == "discord_rpc":
            self.discord_rpc = bool(value)
            self._apply_discord_setting()
            self._save_config()
            return {"ok": True}
        if key == "update_channel" and str(value).lower() not in core.UPDATE_CHANNELS:
            return {"ok": False}
        if key == "quality" and str(value) not in ("auto", "low", "medium", "high"):
            return {"ok": False}
        if key == "theme_mode" and str(value) not in ("dark", "light"):
            return {"ok": False}
        if key == "ui_mode" and str(value) not in ("simple", "advanced", "expert"):
            return {"ok": False}
        if key == "hotkey_toggle":
            value = str(value or "").strip()
            if not re.fullmatch(r"[A-Za-zА-Яа-я0-9+ ]{3,40}", value):
                return {"ok": False}
        if key == "idle_hide_min":
            try:
                value = max(0, min(240, int(value)))
            except Exception:
                return {"ok": False}
        setattr(self, mapping[key], value)
        if key == "autorun":
            core.set_autorun(bool(value))
        self._save_config()
        return {"ok": True}

    def _effective_quality(self):
        """D3/D6: эффективный пресет качества с учётом батареи."""
        base = self.quality if self.quality in ("low", "medium", "high") else core.detect_quality_preset()
        if self.battery_saver and self.battery.get("on_battery"):
            return "low"
        return base

    def _discord_id(self):
        return (self.discord_client_id or core.discord_client_id()).strip()

    def set_discord_client_id(self, value):
        """G12: сохранить Client ID приложения Discord и применить настройку."""
        value = str(value or "").strip()
        if value and not re.fullmatch(r"\d{17,20}", value):
            return {"ok": False, "error": "format"}
        self.discord_client_id = value
        self._save_config()
        self._apply_discord_setting()
        return {"ok": True, "client_id_set": bool(self._discord_id())}

    def _apply_discord_setting(self):
        """G12: включить/выключить presence (тихий no-op без client_id/pypresence)."""
        try:
            client_id = self._discord_id()
            if self.discord_rpc and client_id and discord_rpc.PYPRESENCE_AVAILABLE:
                if self.discord is None:
                    self.discord = discord_rpc.DiscordPresence(client_id)
                self._update_discord(force=True)
            elif self.discord is not None:
                self.discord.close()
                self.discord = None
        except Exception as e:
            core.log_error(f"webapp discord: {e}")

    def _update_discord(self, force=False):
        try:
            if self.discord is None:
                return
            payload = core.discord_payload(self.status, self.selected_bat, self.start_time, self.lang)
            self.discord.update(**payload, force=force)
        except Exception:
            pass

    def set_compact(self, enabled):
        enabled = bool(enabled)
        if enabled == self._compact:
            return {"ok": True, "compact": self._compact}
        try:
            w = self.window
            if w is None:
                return {"ok": False}
            native = getattr(w, "native", None)
            size_cls = None
            try:
                from webview.platforms.winforms import Size
                size_cls = Size
            except Exception:
                size_cls = None
            scale = getattr(native, "_scale", 1.0) if native is not None else 1.0
            if enabled:
                self._pre_compact = (w.x, w.y, w.width, w.height)
                if native is not None and size_cls is not None:
                    native.MinimumSize = size_cls(int(250 * scale), int(90 * scale))
                w.on_top = True
                w.resize(300, 140)
            else:
                if native is not None and size_cls is not None:
                    native.MinimumSize = size_cls(int(460 * scale), int(640 * scale))
                w.on_top = False
                if self._pre_compact:
                    x, y, wd, ht = self._pre_compact
                    w.move(x, y)
                    w.resize(wd, ht)
                self._pre_compact = None
            self._compact = enabled
            return {"ok": True, "compact": enabled}
        except Exception as e:
            core.log_error(f"webapp compact: {e}")
            return {"ok": False}

    def open_logs(self):
        try:
            if not os.path.exists(core.LOG_PATH):
                with open(core.LOG_PATH, "w", encoding="utf-8") as f:
                    f.write("[LOG START]\n")
            os.startfile(core.LOG_PATH)
        except Exception as e:
            core.log_error(f"webapp open_logs: {e}")

    def toggle_proxy(self):
        return self._submit("proxy", wait=True, timeout=30.0)

    def _do_proxy_toggle(self):
        try:
            if self.proxy_pid:
                subprocess.call(["taskkill", "/F", "/PID", str(self.proxy_pid)],
                                creationflags=0x08000000)
                self.proxy_pid = None
                self.proxy_enabled = False
                self._save_config()
                return {"ok": True, "proxy": "OFF"}
            exe = os.path.join(self.zapret_dir, PROXY_EXE)
            if not os.path.exists(exe):
                return {"ok": False, "error": "TgWsProxy не найден"}
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.call(["taskkill", "/F", "/IM", PROXY_EXE], startupinfo=si, creationflags=0x08000000)
            proc = subprocess.Popen([exe], cwd=os.path.dirname(exe), startupinfo=si,
                                    creationflags=0x08000000)
            time.sleep(0.4)
            self.proxy_pid = proc.pid if proc.poll() is None else None
            self.proxy_enabled = bool(self.proxy_pid)
            self._save_config()
            return {"ok": True, "proxy": "ON" if self.proxy_pid else "OFF"}
        except Exception as e:
            core.log_error(f"webapp proxy: {e}")
            return {"ok": False}

    def get_proxy_info(self):
        cfg = core.read_proxy_config(self.zapret_dir)
        running = bool(self.proxy_pid)
        return {"ok": True, "running": running, "host": cfg.get("host"),
                "port": cfg.get("port"), "secret": cfg.get("secret"),
                "link": core.proxy_link(cfg),
                "health": core.proxy_health_ok(cfg) if running else False}

    def apply_proxy_config(self, port, secret):
        try:
            port = int(port)
        except Exception:
            return {"ok": False, "error": "port"}
        if not (1 <= port <= 65535):
            return {"ok": False, "error": "port"}
        secret = str(secret or "").strip().lower()
        if secret and not re.fullmatch(r"[0-9a-f]{16,64}", secret):
            return {"ok": False, "error": "secret"}
        if not secret:
            secret = os.urandom(16).hex()
        if not core.write_proxy_config({"port": port, "secret": secret}, self.zapret_dir):
            return {"ok": False, "error": "write"}
        restarted = False
        if self.proxy_pid:
            self._submit("proxy", wait=True, timeout=30.0)
            self._submit("proxy", wait=True, timeout=30.0)
            restarted = True
        cfg = core.read_proxy_config(self.zapret_dir)
        return {"ok": True, "port": cfg.get("port"), "secret": cfg.get("secret"),
                "link": core.proxy_link(cfg), "restarted": restarted}

    # ---------- tests ----------
    def run_tests(self):
        if self.test_state["running"]:
            return {"ok": False}
        self.test_state = {"running": True, "line": "Запуск...", "progress": 0, "total": 0}
        threading.Thread(target=self._tests_worker, daemon=True).start()
        return {"ok": True}

    def _tests_worker(self):
        def on_line(line):
            self.test_state["line"] = line[-60:]
            m = re.search(r"\[(\d+)/(\d+)\]", line)
            if m:
                self.test_state["progress"], self.test_state["total"] = int(m.group(1)), int(m.group(2))

        best = core.run_strategy_tests(self.zapret_dir, on_line=on_line)
        if best:
            self.selected_bat = best
            self.favorite_bat = best
            self.strategy_scores[best] = max(self.strategy_scores.get(best, 0.0), 1.0)
            self._save_config()
        self.test_state = {"running": False, "line": "", "progress": 0, "total": 0,
                           "best": best}

    # ---------- update ----------
    def check_update(self):
        try:
            import ssl
            import urllib.request
            url = core.update_manifest_url(self.update_channel)
            if not core.is_trusted_update_url(url):
                return {"ok": False}
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url,
                                         headers={"User-Agent": f"ZapretLauncherWeb/{core.CURRENT_VERSION}"})
            with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            if not core.manifest_signature_ok(data):
                core.log_event("update_signature_fail", channel=self.update_channel)
                return {"ok": False, "error": "signature"}

            def vt(v):
                try:
                    return tuple(int(x) for x in v.split("."))
                except Exception:
                    return (0,)

            if vt(data.get("version", "")) > vt(core.CURRENT_VERSION):
                self.update_info = data
                return {"ok": True, "available": True, "version": data.get("version")}
            self.update_info = None
            return {"ok": True, "available": False}
        except Exception as e:
            core.log_error(f"webapp check_update: {e}")
            return {"ok": False}

    def perform_update(self):
        info = self.update_info
        if not info:
            return {"ok": False}
        if not core.manifest_signature_ok(info):
            return {"ok": False, "error": "signature"}
        mode = core.update_mode()
        if mode == "installed" and core.installer_update_available(info):
            result = self._perform_installer_update(info)
            if result.get("ok") or result.get("error") != "download":
                return result
            core.log_error("Апдейтер: установщик недоступен, фолбэк на self-update exe")
        return self._perform_exe_update(info)

    def _download_update_file(self, info, key, expected_hash, tmp_path):
        """Скачать файл обновления (SSL + лимит размера + sha256). -> (ok, error)"""
        import ssl
        import urllib.request
        candidates = core.update_download_candidates(info, key=key)
        if not candidates:
            return False, "no_url"
        ctx = ssl.create_default_context()
        downloaded = False
        for url in candidates:
            try:
                req = urllib.request.Request(url,
                                             headers={"User-Agent": f"ZapretLauncherWeb/{core.CURRENT_VERSION}"})
                total = 0
                with urllib.request.urlopen(req, context=ctx, timeout=120) as r, open(tmp_path, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > core.MAX_UPDATE_BYTES:
                            raise ValueError("превышен лимит размера обновления")
                        f.write(chunk)
                downloaded = True
                break
            except Exception as e:
                core.log_error(f"webapp update download ({url}): {e}")
        if not downloaded:
            return False, "download"
        digest = hashlib.sha256()
        with open(tmp_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                digest.update(block)
        if digest.hexdigest().lower() != expected_hash:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return False, "hash"
        return True, ""

    def _perform_installer_update(self, info):
        """A9/I3: обновление через Setup.exe (Program Files + ярлыки), затем перезапуск."""
        expected = (info.get("installer_sha256") or "").lower()
        if not expected:
            return {"ok": False, "error": "no_installer"}
        tmp = os.path.join(os.environ.get("TEMP", "."), "ZapretLauncher-Setup.exe")
        ok, error = self._download_update_file(info, "installer_url", expected, tmp)
        if not ok:
            return {"ok": False, "error": error}
        core.log_event("update_installer_start", version=info.get("version"), channel=self.update_channel)
        if not core.launch_installer_and_restart(tmp, components=core.installed_components()):
            return {"ok": False, "error": "launch"}
        os._exit(0)

    def _perform_exe_update(self, info):
        """Portable/фолбэк: self-update exe (download -> hash -> swap -> restart)."""
        try:
            expected = (info.get("hash") or "").lower()
            if not expected:
                return {"ok": False}
            tmp = os.path.join(os.environ.get("TEMP", "."), "Zapret_Update.exe")
            ok, error = self._download_update_file(info, "download_url", expected, tmp)
            if not ok:
                return {"ok": False, "error": error}
            cur = core.current_exe_path()
            new = cur + ".new"
            shutil.copy2(tmp, new)
            old = cur + ".old"
            try:
                if os.path.exists(old):
                    os.remove(old)
                os.replace(cur, old)
                os.replace(new, cur)
            except Exception as e:
                core.log_error(f"webapp update swap: {e}")
                return {"ok": False}
            core.log_event("update_applied", version=info.get("version"), channel=self.update_channel)
            subprocess.Popen([cur], close_fds=True)
            os._exit(0)
        except Exception as e:
            core.log_error(f"webapp perform_update: {e}")
            return {"ok": False}

    def rollback_update(self):
        """F2: откат на предыдущую версию exe (резервная копия .old от последнего обновления)."""
        cur = core.current_exe_path()
        old = cur + ".old"
        if not os.path.exists(old):
            return {"ok": False, "error": "no_backup"}
        try:
            keep = cur + ".rollback"
            try:
                if os.path.exists(keep):
                    os.remove(keep)
            except OSError:
                pass
            os.replace(cur, keep)
            try:
                os.replace(old, cur)
            except Exception:
                os.replace(keep, cur)
                raise
            core.log_event("update_rollback", exe=cur)
            subprocess.Popen([cur], close_fds=True)
            os._exit(0)
        except Exception as e:
            core.log_error(f"webapp rollback: {e}")
            return {"ok": False, "error": "swap"}

    def get_changelog(self):
        return core.CHANGELOG

    def speedtest(self):
        """G6: доступность/задержки «до/после» — текущий замер против предыдущего другого состояния."""
        try:
            results = core.probe_services(timeout=2.0)
            entry = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "status": self.status,
                     "score": round(core.score_probe_results(results), 3), "results": results}
            history = list(self.speedtest_history)
            history.append(entry)
            self.speedtest_history = history[-10:]
            self._save_config()
            previous = None
            for item in reversed(history[:-1]):
                if item.get("status") != self.status:
                    previous = item
                    break
            return {"ok": True, "current": entry, "previous": previous,
                    "history": self.speedtest_history[-5:]}
        except Exception as e:
            core.log_error(f"webapp speedtest: {e}")
            return {"ok": False}

    def _auto_rotate_now(self, score):
        """B4: деградация — переключиться на избранную стратегию и перезапустить."""
        texts = core.TRANSLATIONS_DATA.get(self.lang, core.TRANSLATIONS_DATA["EN"])
        target = self.favorite_bat if self.favorite_bat and self.favorite_bat != self.selected_bat else self.selected_bat
        if target != self.selected_bat:
            self.selected_bat = target
            self._save_config()
        core.log_event("auto_rotate", strategy=target, score=round(score, 3))
        if self.notifications_enabled and self.tray is not None:
            try:
                body = texts.get("rotate_notify", "Strategy switched: {name}").replace("{name}", target)
                threading.Thread(target=self.tray.notify, args=(body, "ZapretLauncher"), daemon=True).start()
            except Exception:
                pass
        self._submit("restart")

    def _apply_game_priority(self, high):
        try:
            import psutil
            for proc in psutil.process_iter(["name"]):
                if (proc.info.get("name") or "").lower() == "winws.exe":
                    proc.nice(psutil.HIGH_PRIORITY_CLASS if high else psutil.NORMAL_PRIORITY_CLASS)
            core.log_event("game_priority", high=bool(high))
        except Exception as e:
            core.log_error(f"webapp game priority: {e}")

    def report_problem(self):
        try:
            tail = ""
            try:
                if os.path.exists(core.LOG_PATH):
                    with open(core.LOG_PATH, encoding="utf-8", errors="replace") as f:
                        tail = "".join(f.readlines()[-40:])
            except Exception:
                tail = ""
            crash = core.latest_crash_file()
            if crash:
                try:
                    with open(crash, encoding="utf-8", errors="replace") as f:
                        tail += "\n--- crash ---\n" + "".join(f.readlines()[-20:])
                except Exception:
                    pass
            import platform
            url = core.build_issue_url(core.CURRENT_VERSION, strategy=self.selected_bat,
                                       os_info=platform.platform(), log_tail=tail)
            if not url:
                return {"ok": False}
            os.startfile(url)
            return {"ok": True}
        except Exception as e:
            core.log_error(f"webapp report_problem: {e}")
            return {"ok": False}

    def import_bat(self):
        if webview is None or self.window is None:
            return {"ok": False}
        try:
            path = self.window.create_file_dialog(webview.OPEN_DIALOG, file_types=("Bat (*.bat)",))
            if not path:
                return {"ok": False}
            src = path[0] if isinstance(path, (list, tuple)) else path
            name = os.path.basename(src)
            if not name.lower().endswith(".bat"):
                return {"ok": False}
            shutil.copy2(src, os.path.join(self.zapret_dir, name))
            self.selected_bat = name
            self._save_config()
            core.log_event("import_bat", name=name)
            return {"ok": True, "strategy": name,
                    "strategies": core.list_strategies(self.zapret_dir)}
        except Exception as e:
            core.log_error(f"webapp import_bat: {e}")
            return {"ok": False}

    def export_config(self):
        if webview is None or self.window is None:
            return {"ok": False}
        path = self.window.create_file_dialog(webview.SAVE_DIALOG, save_filename="zapret_config.json")
        if path:
            shutil.copy2(core.CONFIG_PATH, path[0] if isinstance(path, (list, tuple)) else path)
            return {"ok": True}
        return {"ok": False}

    def import_config(self):
        if webview is None or self.window is None:
            return {"ok": False}
        path = self.window.create_file_dialog(webview.OPEN_DIALOG, file_types=("JSON (*.json)",))
        if path:
            src = path[0] if isinstance(path, (list, tuple)) else path
            try:
                with open(src, encoding="utf-8") as f:
                    data = json.load(f)
                if any(k in data for k in ("snow", "bat", "theme")):
                    shutil.copy2(src, core.CONFIG_PATH)
                    self._load_config()
                    return {"ok": True}
            except Exception as e:
                core.log_error(f"webapp import: {e}")
        return {"ok": False}

    # ---------- probes & auto-pick (B3, B4, B6) ----------
    def save_network_profile(self):
        key = self.network.get("network_key")
        if not key:
            return {"ok": False}
        self.profiles[key] = self.selected_bat
        self._save_config()
        return {"ok": True, "network": key, "strategy": self.selected_bat}
    def probe_now(self):
        self.services = core.probe_services(timeout=2.0)
        return {"ok": True, "services": self.services}

    def auto_test_strategies(self):
        if self.autotest.get("running") or self.test_state.get("running"):
            return {"ok": False}
        strategies = core.list_strategies(self.zapret_dir)
        if not strategies:
            return {"ok": False}
        self.autotest = {"running": True, "index": 0, "total": len(strategies),
                         "strategy": "", "best": None, "best_score": -1.0}
        threading.Thread(target=self._autotest_worker, args=(strategies,), daemon=True).start()
        return {"ok": True}

    def _autotest_worker(self, strategies):
        try:
            for i, name in enumerate(strategies):
                self.autotest.update({"index": i + 1, "strategy": name})
                self.selected_bat = name
                self._submit("start", wait=True, timeout=120.0)
                if self.status != "ON":
                    self._submit("stop", wait=True, timeout=60.0)
                    continue
                time.sleep(2.0)
                results = core.probe_services(timeout=2.0)
                score = core.score_probe_results(results)
                self.strategy_scores[name] = round(score, 3)
                if score > self.autotest["best_score"]:
                    self.autotest["best_score"] = score
                    self.autotest["best"] = name
                self._submit("stop", wait=True, timeout=60.0)
                if score >= 1.0:
                    break
            best = self.autotest.get("best")
            if best:
                self.selected_bat = best
                self.favorite_bat = best
                self._save_config()
        except Exception as e:
            core.log_error(f"autotest error: {e}")
        finally:
            self._save_config()
            self.autotest["running"] = False

    # ---------- zapret data & lists (B8, B9) ----------
    def check_zapret_update(self):
        rel = core.fetch_zapret_latest_release()
        if not rel:
            return {"ok": False}
        current = os.path.basename(self.zapret_dir or "")
        tag = rel.get("tag", "")
        return {"ok": True, "latest": tag, "current": current,
                "available": bool(tag) and tag not in current}

    def update_zapret(self):
        ok, message = core.update_zapret_data()
        if ok:
            self.zapret_dir = core.locate_zapret_dir()
            strategies = core.list_strategies(self.zapret_dir)
            if self.selected_bat not in strategies and strategies:
                self.selected_bat = strategies[0]
                self._save_config()
        return {"ok": ok, "message": message,
                "strategies": core.list_strategies(self.zapret_dir)}

    def get_lists(self):
        names = ("list-general-user.txt", "list-exclude-user.txt",
                 "ipset-exclude-user.txt", "ipset-all-user.txt")
        out = {}
        for name in names:
            path = os.path.join(self.zapret_dir, "lists", name)
            try:
                if os.path.exists(path):
                    with open(path, encoding="utf-8", errors="replace") as f:
                        out[name] = f.read()
                else:
                    out[name] = ""
            except Exception:
                out[name] = ""
        return out

    def save_list(self, name, content):
        allowed = {"list-general-user.txt", "list-exclude-user.txt",
                   "ipset-exclude-user.txt", "ipset-all-user.txt"}
        if name not in allowed:
            return {"ok": False}
        try:
            path = os.path.join(self.zapret_dir, "lists", name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content or "")
            return {"ok": True}
        except Exception as e:
            core.log_error(f"webapp save_list: {e}")
            return {"ok": False}

    # ---------- tray (C8 + C6) ----------
    def _tray_icon_image(self):
        colors = {"ON": (0, 255, 136), "BUSY": (255, 153, 0), "OFF": (90, 101, 145)}
        color = colors.get(self.status, (90, 101, 145))
        img = core.Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = core.ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=color + (255,), outline=(20, 20, 40, 255), width=3)
        return img

    def _tray_select(self, name):
        def handler(icon, item):
            self.select_strategy(name)
            self._refresh_tray()
        return handler

    def _refresh_tray(self):
        """C8: динамическая иконка по статусу + меню быстрых стратегий."""
        try:
            if self.tray is None:
                return
            self.tray.icon = self._tray_icon_image()
            strategies = core.list_strategies(self.zapret_dir)
            items = [
                core.pystray.MenuItem("Показать", self._tray_show, default=True),
                core.pystray.MenuItem("Вкл / Выкл", lambda icon, item: self.toggle()),
            ]
            if strategies:
                items.append(core.pystray.MenuItem("Стратегия", core.pystray.Menu(*[
                    core.pystray.MenuItem(name, self._tray_select(name), radio=True,
                                          checked=lambda item, n=name: self.selected_bat == n)
                    for name in strategies[:12]
                ])))
            items.append(core.pystray.MenuItem("Выход", self._tray_exit))
            self.tray.menu = core.pystray.Menu(*items)
        except Exception as e:
            core.log_error(f"webapp tray refresh: {e}")

    def _tray_show(self, icon, item):
        try:
            if self.window:
                self.window.show()
                self.window.restore()
        except Exception:
            pass

    def _tray_exit(self, icon, item):
        try:
            icon.stop()
        finally:
            self.quit_app()

    def setup_tray(self):
        try:
            self.tray = core.pystray.Icon("ZapretWeb", self._tray_icon_image(), "ZapretLauncher Web")
            self._refresh_tray()
            threading.Thread(target=self.tray.run, daemon=True).start()
        except Exception as e:
            self.tray = None
            core.log_error(f"webapp tray: {e}")

    def quit_app(self):
        try:
            if self.discord is not None:
                self.discord.close()
        except Exception:
            pass
        try:
            self._submit("stop", wait=True, timeout=15.0)
        except Exception:
            pass
        os._exit(0)

    # ---------- background ----------
    def _monitor_loop(self):
        counter = 0
        while True:
            try:
                import psutil
                self.hud["CPU"] = str(int(psutil.cpu_percent(interval=None)))
                self.hud["RAM"] = str(int(psutil.virtual_memory().percent))
            except Exception:
                pass
            counter += 1
            if counter % 15 == 0:
                self.battery = core.battery_state()
                self._refresh_tray()
            if self.discord is not None and time.time() - self._discord_ts >= 15.0:
                self._discord_ts = time.time()
                self._update_discord()
            ping_every = 30 if (self.battery_saver and self.battery.get("on_battery")) else 10
            if counter % ping_every == 0:
                try:
                    ms = core.tcp_connect_ms("8.8.8.8", 443, timeout=1.0)
                    self.hud["PING"] = f"{ms}ms" if ms >= 0 else "---"
                except Exception:
                    self.hud["PING"] = "---"
            if self.status == "ON" and counter % 15 == 0:
                try:
                    ms = core.tcp_connect_ms("discord.com", 443, timeout=2.0)
                    self.hud["BYPASS"] = "OK" if ms >= 0 else "FAIL"
                except Exception:
                    self.hud["BYPASS"] = "---"
            elif self.status != "ON":
                self.hud["BYPASS"] = "---"
            if self.status == "ON" and counter % 20 == 0 and not self.game_active:
                try:
                    self.services = core.probe_services(timeout=2.0)
                except Exception:
                    self.services = {}
            if counter % 10 == 0:
                active = core.fullscreen_game_active() if self.gaming_mode else False
                if active != self.game_active:
                    self.game_active = active
                    self._apply_game_priority(active)
            if self.auto_rotate and self.status == "ON" and counter % 60 == 0 and not self.game_active:
                try:
                    score = core.score_probe_results(core.probe_services(timeout=2.0))
                    if score < 0.5:
                        self._rotate_fail_streak += 1
                        core.log_event("rotate_degraded", score=round(score, 3),
                                       streak=self._rotate_fail_streak)
                        if self._rotate_fail_streak >= 3:
                            self._rotate_fail_streak = 0
                            self._auto_rotate_now(score)
                    else:
                        self._rotate_fail_streak = 0
                except Exception as e:
                    core.log_error(f"webapp auto-rotate: {e}")
            if self.proxy_pid:
                try:
                    import psutil
                    if not psutil.pid_exists(self.proxy_pid):
                        self.proxy_pid = None
                except Exception:
                    pass
            if self.idle_hide_min:
                try:
                    if core.seconds_since_last_input() > self.idle_hide_min * 60:
                        if not self._idle_hidden and self.window is not None:
                            self._idle_hidden = True
                            self.window.minimize()
                    else:
                        self._idle_hidden = False
                except Exception:
                    pass
            time.sleep(1)

    def _watchdog_loop(self):
        fail_streak = 0
        while True:
            try:
                if self.status == "ON":
                    if self.backend.health_ok():
                        fail_streak = 0
                    else:
                        fail_streak += 1
                        if fail_streak >= 2:
                            core.log_error("Web watchdog: служба упала")
                            fail_streak = 0
                            if not self._cmd_queue.empty():
                                pass
                            elif self.auto_restart:
                                self._submit("restart")
                            else:
                                self._submit("fail")
                else:
                    fail_streak = 0
            except Exception as e:
                core.log_error(f"webapp watchdog: {e}")
            time.sleep(5)


def main():
    if webview is None:
        print("pywebview не установлен. Выполните: pip install pywebview")
        return 1
    core.install_crash_handler("webapp")
    if "--install-service" in sys.argv:
        core.ensure_app_data()
        ok = core.cli_install_service()
        return 0 if ok else 1
    if core.is_dev_mode():
        core.log_error("DEV-режим: MockBackend, без админа и реальной службы")
    elif not core.is_admin():
        script = os.path.abspath(__file__)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}"', None, 1)
        return 0

    core.ensure_app_data()
    core.record_install_mode()
    core.ensure_payload()
    api = Api()
    index = core.resource_path(os.path.join("webui", "index.html"))
    api.window = webview.create_window(
        f"ZapretLauncher v{core.CURRENT_VERSION}", index,
        js_api=api, width=520, height=820, min_size=(460, 640),
        background_color="#0a0b1e", text_select=False)
    api.setup_tray()
    webview.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
