"""Smoke-проверки ZapretLauncher (stdlib, без внешних зависимостей).

Запуск: python tools/smoke.py
Возвращает код 0 при успехе, 1 при ошибке.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Изоляция: smoke не должен писать в реальный каталог данных пользователя
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="zapret_smoke_")
os.environ.setdefault("ZAPRET_DATA_DIR", _TEST_DATA_DIR)
MAIN = os.path.join(ROOT, "zapret_new_win.py")
ZIP_PATH = os.path.join(ROOT, "zapret_data.zip")

results: list = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    text = ("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else "")
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(enc)
    except (UnicodeEncodeError, LookupError):
        text = text.encode(enc, "replace").decode(enc, "replace")
    print(text)


def main():
    # 1. py_compile
    try:
        import py_compile
        py_compile.compile(MAIN, doraise=True)
        check("py_compile", True)
    except Exception as e:
        check("py_compile", False, str(e))
        return

    with open(MAIN, encoding="utf-8") as f:
        src = f.read()

    # 2. Удалённый мёртвый код отсутствует
    dead = [
        "make_hidden(", "get_ping_ms(", "MEMORYSTATUSEX", "get_real_ram_usage",
        "set_volume_max", "def play_mp3", "RUSSIAN_ANTHEM_FILE", "AMERICAN_ANTHEM_FILE",
        "_install_files_sync", "check_and_install_files", "copy_exe_to_appdata",
        "def get_exe_path", "_locate_zapret_dir", "update_msg_timer", "update_msg_text",
        "switch_notifications_pos", "switch_repair_pos", "seen_configs",
        "enable_debug_privilege", "on_right_click", "get_autorun_exe_path",
        "import winreg", "import webbrowser",
    ]
    found = [d for d in dead if d in src]
    check("dead code removed", not found, ", ".join(found))

    # 3. Новые функции/константы присутствуют
    required = [
        "def parse_strategy_bat", "def split_windows_args", "def read_game_filter",
        "def ensure_user_lists", "def enable_tcp_timestamps", "def _safe_extractall",
        "def is_trusted_update_url", "def validate_port_range", "def tcp_connect_ms",
        "def current_exe_path", "def sha256_of_file", "def _maybe_save_stats",
        "def ui_call", "def _pump_ui_queue", "def _render_compact",
        "RENDER_FRAME_MS", "UPDATE_ALLOWED_HOSTS",
    ]
    missing = [r for r in required if r not in src]
    check("new helpers present", not missing, ", ".join(missing))

    # 4. shell=True/SeDebug больше нет в коде (кроме changelog-строки)
    code_lines = [ln for ln in src.splitlines() if "shell=True" in ln]
    check("no shell=True in code", not code_lines, "; ".join(code_lines))

    # 5. zip: корень == FOLDER_NAME, целостность, папка <-> zip 1:1
    m = re.search(r'FOLDER_NAME\s*=\s*"([^"]+)"', src)
    folder_name = m.group(1) if m else None
    check("FOLDER_NAME found", bool(folder_name), str(folder_name))
    try:
        zf = zipfile.ZipFile(ZIP_PATH)
        names = zf.namelist()
        check("zip integrity", zf.testzip() is None)
        roots = {n.split("/")[0] for n in names}
        check("zip root", roots == {folder_name}, ", ".join(sorted(roots)))
        zip_files = sorted(n[len(folder_name) + 1:] for n in names if not n.endswith("/"))
        disk_root = os.path.join(ROOT, "zapret_data", folder_name)
        disk_files = []
        for dp, _dn, fn in os.walk(disk_root):
            for f in fn:
                disk_files.append(os.path.relpath(os.path.join(dp, f), disk_root).replace("\\", "/"))
        disk_files.sort()
        check("zip vs folder 1:1", zip_files == disk_files,
              f"zip={len(zip_files)} disk={len(disk_files)}")
        check("zip has winws.exe", any(n.endswith("bin/winws.exe") for n in names))
        check("zip has TgWsProxy", any(n.endswith("TgWsProxy_windows.exe") for n in names))
    except Exception as e:
        check("zip checks", False, str(e))

    # 6. Импорт модуля и функциональные тесты (если среда позволяет)
    sys.path.insert(0, ROOT)
    try:
        import zapret_new_win as app
    except Exception as e:
        check("import zapret_new_win", False, str(e))
        summarize()
        return
    check("import zapret_new_win", True)

    # 6a. parse_strategy_bat на всех стратегиях
    strategies_dir = os.path.join(ROOT, "zapret_data", folder_name)
    bats = sorted(f for f in os.listdir(strategies_dir) if f.endswith(".bat") and "service" not in f.lower()) \
        if os.path.isdir(strategies_dir) else []
    bad = []
    for bat in bats:
        args = app.parse_strategy_bat(os.path.join(strategies_dir, bat), strategies_dir)
        if not args or "--wf-tcp" not in args or "%" in args or "^" in args:
            bad.append(f"{bat}: {'None' if not args else args[:80]}")
    check(f"parse_strategy_bat ({len(bats)} стратегий)", not bad, "; ".join(bad[:3]))

    # 6b. split_windows_args
    tokens = app.split_windows_args('-a --hostlist="C:\\Program Files\\x.txt" --ipset-exclude="C:\\y.txt"')
    expected = ["-a", "--hostlist=C:\\Program Files\\x.txt", "--ipset-exclude=C:\\y.txt"]
    check("split_windows_args", tokens == expected, str(tokens))

    # 6c. validate_port_range
    cases = {
        "12": "12", "1024-1934,1936-65535": "1024-1934,1936-65535",
        "": None, "0-10": None, "1-2-3": None, "70000": None, "100-50": None,
    }
    bad = [k for k, v in cases.items() if app.validate_port_range(k) != v]
    check("validate_port_range", not bad, ", ".join(bad))

    # 6d. read_game_filter
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "utils"))
        with open(os.path.join(tmp, "utils", "game_filter.enabled"), "w", encoding="utf-8") as f:
            f.write("mode=tcp\ntcp=1024-1934,1936-65535\nudp=1024-65535\n")
        gf = app.read_game_filter(tmp)
        check("read_game_filter tcp-mode", gf == ("1024-1934,1936-65535", "12", "1024-1934,1936-65535"), str(gf))
        empty = app.read_game_filter(os.path.join(tmp, "nope"))
        check("read_game_filter default", empty == ("12", "12", "12"), str(empty))

    # 6e. is_trusted_update_url
    trusted = app.is_trusted_update_url(
        "https://github.com/Aikiovade/ZapretLauncher/releases/download/v17.4/Zapret.exe")
    untrusted = app.is_trusted_update_url("https://evil.example.com/Aikiovade/ZapretLauncher/x.exe")
    http_url = app.is_trusted_update_url("http://github.com/Aikiovade/ZapretLauncher/x.exe")
    check("is_trusted_update_url", trusted and not untrusted and not http_url)

    # 6f. _safe_extractall (zip-slip)
    with tempfile.TemporaryDirectory() as tmp:
        bad_zip = os.path.join(tmp, "bad.zip")
        with zipfile.ZipFile(bad_zip, "w") as z:
            z.writestr("ok.txt", "ok")
            z.writestr("../evil.txt", "evil")
        dest = os.path.join(tmp, "dest")
        os.makedirs(dest)
        with zipfile.ZipFile(bad_zip) as z:
            app._safe_extractall(z, dest)
        escaped = os.path.exists(os.path.join(tmp, "evil.txt"))
        check("_safe_extractall blocks traversal", os.path.exists(os.path.join(dest, "ok.txt")) and not escaped)

    # 6g. i18n: одинаковый набор ключей RU/EN
    ru = set(app.TRANSLATIONS_DATA["RU"])
    en = set(app.TRANSLATIONS_DATA["EN"])
    check("i18n keys parity", ru == en, str(ru ^ en))

    # 6h. ensure_user_lists
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "lists"))
        app.ensure_user_lists(tmp)
        files = sorted(os.listdir(os.path.join(tmp, "lists")))
        check("ensure_user_lists", files == ["ipset-exclude-user.txt", "list-exclude-user.txt",
                                             "list-general-user.txt"], str(files))

    # 6i. звуки запуска/выключения
    ok_sounds = True
    detail = []
    for rel in ("sounds/start.wav", "sounds/stop.wav"):
        path = os.path.join(ROOT, rel.replace("/", os.sep))
        good = False
        if os.path.exists(path):
            with open(path, "rb") as f:
                good = f.read(4) == b"RIFF"
        ok_sounds = ok_sounds and good
        detail.append(f"{rel}={os.path.getsize(path) if os.path.exists(path) else 'missing'}")
    check("sound files (RIFF WAV)", ok_sounds, ", ".join(detail))

    # 6j. новые функции волны 1
    required_wave1 = ["service_state", "winws_health_ok", "winws_process_running",
                      "detect_foreign_dpi_tools", "migrate_from_legacy_dir", "_pick_data_dir"]
    missing_w1 = [r for r in required_wave1 if not hasattr(app, r)]
    check("wave1 helpers", not missing_w1, ", ".join(missing_w1))

    # 6k. каталог данных и схема конфига
    env_dir = os.environ.get("ZAPRET_DATA_DIR")
    check("data dir (isolated in tests)", bool(env_dir)
          and os.path.realpath(app.APP_DATA_DIR) == os.path.realpath(env_dir), app.APP_DATA_DIR)
    check("config schema v2", app.CONFIG_SCHEMA_VERSION == 2, str(getattr(app, "CONFIG_SCHEMA_VERSION", None)))

    # 6l. модульные функции службы (A3/A7) и webapp Api (A7)
    core_funcs = ["install_zapret_service", "launch_winws_direct", "stop_services_and_processes",
                  "list_strategies", "fetch_zapret_latest_release", "update_zapret_data",
                  "is_trusted_github_url", "_package_version_key", "_find_installed_package_roots",
                  "run_strategy_tests"]
    missing_core = [f for f in core_funcs if not hasattr(app, f)]
    check("module service funcs", not missing_core, ", ".join(missing_core))
    check("webui/index.html exists", os.path.exists(os.path.join(ROOT, "webui", "index.html")))
    check("package version key", app._package_version_key("zapret-discord-youtube-1.10.3") == (1, 10, 3)
          and app._package_version_key("zapret-discord-youtube-1.9.9") < (1, 10, 3))
    check("probe funcs", hasattr(app, "probe_services") and hasattr(app, "score_probe_results")
          and app.score_probe_results({"a": 1, "b": -1, "c": 3}) == 2 / 3
          and app.score_probe_results({}) == 0.0)
    check("proxy config helpers", all(hasattr(app, f) for f in
          ("read_proxy_config", "write_proxy_config", "proxy_link", "proxy_health_ok"))
          and app.proxy_link({"host": "127.0.0.1", "port": 1443, "secret": "ab" * 16})
          == "tg://proxy?server=127.0.0.1&port=1443&secret=dd" + "ab" * 16
          and app.proxy_link({"host": "0.0.0.0", "port": 1443, "secret": "cd"}).endswith("secret=ddcd")
          and app.proxy_health_ok({"host": "127.0.0.1", "port": 1}) is False)
    check("payload completeness", hasattr(app, "payload_complete")
          and app.payload_complete(os.path.join(ROOT, "zapret_data", folder_name))
          and not app.payload_complete(os.path.join(ROOT, "docs"))
          and not app.payload_complete(""))
    check("ensure_payload self-heal", hasattr(app, "ensure_payload")
          and app.payload_complete(app.ensure_payload()))
    winws = os.path.join(ROOT, "zapret_data", folder_name, "bin", "winws.exe")
    check("winws hash pinned", os.path.exists(winws) and app.sha256_of_file(winws) in app.KNOWN_WINWS_SHA256)
    check("interfaces func", isinstance(app.list_active_interfaces(), list))
    net = app.get_current_network()
    check("current network", isinstance(net, dict) and net.get("network_key"))
    check("github url trust", app.is_trusted_github_url(
        "https://github.com/Flowseal/zapret-discord-youtube/releases/download/1.10.3/zapret-discord-youtube-1.10.3.zip")
        and not app.is_trusted_github_url("https://evil.example.com/Flowseal/x.zip"))
    try:
        import webapp
        api = webapp.Api()
        st = api.get_state()
        check("webapp Api state", isinstance(st, dict) and "status" in st
              and "strategies" in st and "settings" in st)
        check("webapp strategies", len(st.get("strategies", [])) > 0, str(len(st.get("strategies", []))))
        check("webapp set_setting", api.set_setting("theme", st["settings"]["theme"]) == {"ok": True})
        lists = api.get_lists()
        check("webapp lists", isinstance(lists, dict) and len(lists) == 4)
        check("webapp list guard", api.save_list("..\\evil.txt", "x") == {"ok": False})
        check("webapp autotest api", hasattr(api, "auto_test_strategies") and hasattr(api, "probe_now"))
        check("webapp interfaces", isinstance(st.get("interfaces"), list))
        check("webapp network", isinstance(st.get("network"), dict) and isinstance(st.get("profiles"), dict)
              and hasattr(api, "save_network_profile"))
        # 6m. C9/A2: single-writer state и локализация web-UI
        check("webapp single-writer", all(hasattr(webapp.Api, m) for m in
              ("_transition", "_submit", "_command_loop", "_dispatch_command"))
              and isinstance(st.get("status_key"), str) and bool(st.get("status_key")))
        check("webapp texts", isinstance(st.get("texts"), dict) and len(st["texts"]) >= 60
              and isinstance(st["texts"].get("status_on"), str))
        check("webapp compact api", hasattr(api, "set_compact") and "compact" in st)
        check("webapp strategy scores", isinstance(st.get("scores"), dict) and hasattr(api, "strategy_scores"))
        pi = api.get_proxy_info()
        check("webapp proxy api", hasattr(api, "apply_proxy_config") and isinstance(pi, dict)
              and pi.get("ok") and str(pi.get("link", "")).startswith("tg://proxy?server=")
              and isinstance(pi.get("port"), int))
        check("webapp report/import api", hasattr(api, "report_problem") and hasattr(api, "import_bat"))
        check("webapp update channel/rollback", hasattr(api, "rollback_update")
              and st.get("update_channel") in app.UPDATE_CHANNELS
              and isinstance(st.get("rollback_available"), bool)
              and "channel" not in st.get("update_channel", "x"))
        check("webapp quality/battery/gaming/idle", st.get("effective_quality") in ("low", "medium", "high")
              and isinstance(st.get("battery"), dict) and isinstance(st.get("idle_hide_min"), int)
              and isinstance(st.get("gaming_mode"), bool) and isinstance(st.get("game_active"), bool))
        check("webapp speedtest api", hasattr(api, "speedtest"))
        check("webapp intro setting", isinstance(st.get("settings", {}).get("intro"), bool))
        check("webapp discord client id api", hasattr(api, "set_discord_client_id"))
        check("webapp discord state", isinstance(st.get("discord"), dict)
              and st["discord"].get("enabled") is False  # дефолт выключен (изолированный конфиг)
              and isinstance(st["discord"].get("lib_available"), bool))
        check("webapp update/installer state", st.get("update_mode") in ("portable", "installed")
              and st.get("data_dir_mode") in ("portable", "programdata", "legacy")
              and isinstance(st.get("installer_update"), bool))
        check("webapp backend/meta/rotate", st.get("backend") in ("winws", "mock")
              and isinstance(st.get("strategy_meta"), dict) and len(st.get("strategy_meta", {})) > 0
              and isinstance(st.get("auto_rotate"), bool) and isinstance(st.get("package"), str))
    except Exception as e:
        check("webapp Api", False, str(e))

    # 6n. C9: все i18n-ключи web-UI присутствуют в словаре ядра
    try:
        with open(os.path.join(ROOT, "webui", "index.html"), encoding="utf-8") as f:
            html = f.read()
    except Exception:
        html = ""
    check("webui i18n engine", "function applyI18n" in html and "function T(" in html
          and "data-i18n=" in html and "data-i18n-title=" in html)
    static_keys = set(re.findall(r'data-i18n(?:-title)?="([^"]+)"', html))
    missing_static = sorted(k for k in static_keys if k not in app.TRANSLATIONS_DATA["RU"])
    check(f"webui static i18n keys ({len(static_keys)})", not missing_static and bool(static_keys),
          ", ".join(missing_static))
    dyn_keys = set(re.findall(r"\bT\('([a-z0-9_]+)'(?!\s*\+)", html))
    missing_dyn = sorted(k for k in dyn_keys if k not in app.TRANSLATIONS_DATA["RU"])
    check(f"webui T() keys ({len(dyn_keys)})", not missing_dyn and bool(dyn_keys), ", ".join(missing_dyn))
    with open(os.path.join(ROOT, "webapp.py"), encoding="utf-8") as f:
        webapp_src = f.read()
    check("webapp ensures payload", "core.ensure_payload()" in webapp_src)
    check("webui discord id modal", 'id="discordmodal"' in html and 'id="discordhint"' in html)
    check("startup animation assets", 'id="splash"' in html and 'id="bg"' in html
          and "function hideSplash" in html and "def _render_intro" in src
          and "intro_lbl" in app.TRANSLATIONS_DATA["RU"] and "intro_lbl" in app.TRANSLATIONS_DATA["EN"])
    check("dev tooling files", os.path.exists(os.path.join(ROOT, "ruff.toml"))
          and os.path.exists(os.path.join(ROOT, "tools", "uninstall.ps1"))
          and os.path.exists(os.path.join(ROOT, ".github", "workflows", "ci.yml")))
    check("installer/portable/golden files", os.path.exists(os.path.join(ROOT, "installer", "zapret_launcher.iss"))
          and os.path.exists(os.path.join(ROOT, "tools", "make_portable.py"))
          and os.path.exists(os.path.join(ROOT, "tools", "gen_golden.py"))
          and os.path.exists(os.path.join(ROOT, "tools", "sign_manifest.py"))
          and os.path.exists(os.path.join(ROOT, "tests", "golden", f"{folder_name}.json")))
    check("core extras", all(hasattr(app, f) for f in
          ("detect_quality_preset", "battery_state", "seconds_since_last_input",
           "fullscreen_game_active", "update_manifest_url", "update_download_candidates",
           "manifest_signature_ok", "manifest_signing_payload")))
    check("backend abstraction", all(hasattr(app, f) for f in
          ("BypassBackend", "WinwsBackend", "MockBackend", "get_backend", "is_dev_mode"))
          and issubclass(app.WinwsBackend, app.BypassBackend)
          and issubclass(app.MockBackend, app.BypassBackend))
    check("strategy meta + crash handler", hasattr(app, "load_strategy_meta")
          and hasattr(app, "install_crash_handler") and hasattr(app, "latest_crash_file")
          and "general (ALT).bat" in app.load_strategy_meta(os.path.join(ROOT, "zapret_data", folder_name)))
    try:
        import tomllib
        with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
            pyproject = tomllib.load(f)
        check("pyproject version sync", pyproject["project"]["version"] == app.CURRENT_VERSION
              and pyproject["project"]["scripts"]["zapret-cli"] == "zapret_cli:main")
    except Exception as e:
        check("pyproject version sync", False, str(e))
    with open(os.path.join(ROOT, "ZapretLite.spec"), encoding="utf-8") as f:
        lite_spec = f.read()
    check("lite spec without zip", "('zapret_data.zip', '.')" not in lite_spec and "ZapretLite" in lite_spec)
    check("pre-commit config", os.path.exists(os.path.join(ROOT, ".pre-commit-config.yaml"))
          and os.path.exists(os.path.join(ROOT, "tools", "ci_service_integration.py")))

    # G12: Discord Rich Presence (опционально, off by default)
    try:
        import discord_rpc as drpc
        noop = drpc.DiscordPresence("")
        embedded = app.discord_client_id()
        check("discord rpc off by default", noop.available is False
              and noop.update(details="x", state="y") is False
              and (not embedded or bool(re.fullmatch(r"\d{17,20}", embedded))))
    except Exception as e:
        check("discord rpc module", False, str(e))
    with open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8") as f:
        reqs = f.read()
    with open(os.path.join(ROOT, "Zapret.spec"), encoding="utf-8") as f:
        spec_tk = f.read()
    with open(os.path.join(ROOT, "ZapretWeb.spec"), encoding="utf-8") as f:
        spec_web = f.read()
    check("discord rpc packaged", "pypresence" in reqs and "'pypresence'" in spec_tk and "'pypresence'" in spec_web)
    check("discord embed tool", os.path.exists(os.path.join(ROOT, "tools", "set_discord_id.py"))
          and hasattr(app, "discord_client_id") and isinstance(app.discord_client_id(), str))
    check("discord payload helper", hasattr(app, "discord_payload")
          and app.discord_payload("ON", "general.bat", time.time() - 65, "RU")["details"].startswith(
              app.TRANSLATIONS_DATA["RU"]["btn_strategy"]))

    # A9/I3/F2: установщик и режимы обновления
    manifests_ok = True
    for man_name in ("update_info.json", "update_info_beta.json"):
        try:
            with open(os.path.join(ROOT, man_name), encoding="utf-8") as f:
                man = json.load(f)
            manifests_ok = manifests_ok and isinstance(man.get("installer_url"), str) and "installer_sha256" in man
        except Exception as e:
            manifests_ok = False
            print("manifest check:", man_name, e)
    check("manifest installer fields", manifests_ok)
    transition_ok = True
    for man_name in ("update_info.json", "update_info_beta.json"):
        try:
            with open(os.path.join(ROOT, man_name), encoding="utf-8") as f:
                man = json.load(f)
            transition_ok = (transition_ok and str(man.get("download_url", "")).endswith("-setup.exe")
                             and man.get("hash") == man.get("installer_sha256"))
        except Exception:
            transition_ok = False
    check("manifest 17.3->installer transition", transition_ok)
    check("installer update helpers", all(hasattr(app, f) for f in
          ("update_mode", "installer_update_available", "installed_exe_path",
           "launch_installer_and_restart", "cli_install_service", "ensure_data_dir_acl",
           "data_dir_mode", "discord_payload"))
          and app.update_mode() in ("portable", "installed")
          and app.data_dir_mode() in ("portable", "programdata", "legacy")
          and app.installed_exe_path().endswith("Zapret.exe"))
    with open(os.path.join(ROOT, "installer", "zapret_launcher.iss"), encoding="utf-8") as f:
        iss = f.read()
    check("installer .iss content", "DefaultDirName={autopf}" in iss and "runascurrentuser" in iss
          and "uninstall.ps1" in iss and "--install-service" in iss
          and "admins-full users-readexec" in iss and "WizardImageFile=wizard_image.bmp" in iss
          and 'Source: "..\\dist\\Zapret.exe"' in iss
          and 'Source: "..\\dist\\ZapretWeb.exe"' not in iss and "Components:" not in iss)
    check("installer art files", os.path.exists(os.path.join(ROOT, "installer", "wizard_image.bmp"))
          and os.path.exists(os.path.join(ROOT, "installer", "wizard_small.bmp")))
    check("installer dark style", "WizardStyle=modern dark includetitlebar" in iss
          and "WizardSizePercent=" in iss and "WizardBackImageFile=wizard_back.bmp" in iss)
    check("installer custom UI", "CreateCustomPage" in iss and "TWizardPage" in iss
          and "SetTimer" in iss and "CurInstallProgressChanged" in iss
          and "ShouldSkipPage" in iss and "banner.bmp" in iss)
    check("installer wow assets", os.path.exists(os.path.join(ROOT, "installer", "wizard_back.bmp"))
          and os.path.exists(os.path.join(ROOT, "installer", "banner.bmp"))
          and os.path.exists(os.path.join(ROOT, "installer", "progress_track.bmp"))
          and os.path.exists(os.path.join(ROOT, "installer", "progress_fill.bmp"))
          and os.path.exists(os.path.join(ROOT, "installer", "finish_banner.bmp"))
          and not os.path.isdir(os.path.join(ROOT, "installer", "frames"))
          and not os.path.exists(os.path.join(ROOT, "installer", "sound_intro.wav")))
    check("installer wow code", "WizardBackImageFile=wizard_back.bmp" in iss
          and "CLOSE_SECONDS" in iss and "CloseTick" in iss and "BM_CLICK" in iss
          and "VersionInfoProductVersion" in iss)
    check("installer sandbox tool", os.path.exists(os.path.join(ROOT, "tools", "installer_sandbox_test.py")))
    check("install-mode helpers", all(hasattr(app, f) for f in
          ("record_install_mode", "recorded_install_mode", "installed_components"))
          and app.installed_components() in ("web", "tk")
          and isinstance(app.recorded_install_mode(), dict))
    check("ci manifest tool", os.path.exists(os.path.join(ROOT, "tools", "ci_update_manifest.py")))
    check("portable helpers", hasattr(app, "is_portable_mode") and hasattr(app, "_portable_requested")
          and app.is_portable_mode() in (True, False))
    check("log helpers", hasattr(app, "log_event") and hasattr(app, "_rotate_log_file")
          and hasattr(app, "build_issue_url")
          and app.build_issue_url("1.0").startswith("https://github.com/Aikiovade/ZapretLauncher/issues/new?"))
    check("service recovery policy", '"sc", "failure"' in src)

    # 6p. 17.5: конструктор стратегий, иммунитет, Windows-интеграция панели задач
    import strategy_builder as sb
    import win_taskbar as wtb
    check("strategy builder module", all(hasattr(sb, f) for f in
          ("parse_args", "serialize_args", "validate_args", "validate_name", "build_bat_content",
           "extract_winws_args", "save_custom_strategy", "export_custom_strategy",
           "import_custom_strategy", "list_custom_strategies")))
    roundtrip = sb.serialize_args(sb.parse_args("--wf-tcp=80 --dpi-desync=fake --new --filter-tcp=443"))
    check("strategy builder roundtrip", roundtrip == "--wf-tcp=80 --dpi-desync=fake --new --filter-tcp=443")
    check("strategy builder validation", sb.validate_args("--wf-tcp=80,443 --dpi-desync=fake") == []
          and [e["error"] for e in sb.validate_args("--dpi-desync=hack")] == ["bad_choice"]
          and sb.validate_args("--custom=bad|value") != []
          and sb.validate_name("my strategy") is None and sb.validate_name("bad/name") == "bad_chars")
    check("recovery helpers", all(hasattr(app, f) for f in
          ("pick_rotation_target", "next_recovery_step", "log_incident", "read_incidents"))
          and app.next_recovery_step("degraded", [], [], 1000.0) == "rotate"
          and app.pick_rotation_target("a.bat", None, ["a.bat", "b.bat"], {}) == "b.bat")
    taskbar = wtb.TaskbarIntegration(None)
    check("taskbar no-op safety", taskbar.enabled is False and taskbar.set_overlay("ON") is False
          and taskbar.set_progress(1, 2) is False and taskbar.flash_error() is False)
    taskbar.close()
    check("17.5 tk integration", all(name in src for name in
          ("def _init_taskbar", "def _sync_taskbar", "def _attempt_recovery", "def _run_recovery_action",
           "def _degrade_check", "def show_osd", "def open_more_settings", "def open_incidents_window",
           "def open_builder_window", "def _builder_load", "def _builder_save", "def _builder_test",
           "def run_custom_strategy_probe", "def repack_payload")))
    check("17.5 config keys", all(f'"{key}"' in src for key in
          ("taskbar_ui", "osd", "self_heal", "auto_rotate")))
    new_keys = ("more_settings", "taskbar_lbl", "osd_lbl", "self_heal_lbl", "inc_title", "inc_copy",
                "builder_open", "sb_base", "sb_test", "sb_save", "osd_on", "osd_off", "heal_fixed",
                "tb_toggle", "tb_tests", "tb_strategies")
    check("17.5 i18n keys", all(key in app.TRANSLATIONS_DATA["RU"] and key in app.TRANSLATIONS_DATA["EN"]
                                for key in new_keys))
    check("custom probe no-op", app.run_custom_strategy_probe("", "")["ok"] is False)

    # 6o. A3/F6/H1: CLI, единый changelog, pytest-набор
    cli = os.path.join(ROOT, "zapret_cli.py")
    check("cli + tests files", os.path.exists(cli) and os.path.exists(os.path.join(ROOT, "tests", "test_core.py")))
    child_env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        out = subprocess.run([sys.executable, cli, "list"], cwd=ROOT, capture_output=True, text=True,
                             timeout=120, encoding="utf-8", errors="replace", env=child_env)
        check("cli list", out.returncode == 0 and ".bat" in (out.stdout or ""), (out.stderr or "")[-140:])
        out = subprocess.run([sys.executable, cli, "status"], cwd=ROOT, capture_output=True, text=True,
                             timeout=120, encoding="utf-8", errors="replace", env=child_env)
        status = json.loads(out.stdout or "{}")
        check("cli status", out.returncode == 0 and status.get("package_complete") is True, str(status)[-140:])
    except Exception as e:
        check("cli run", False, str(e))
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "sync_changelog.py"), "--check"],
                         cwd=ROOT, capture_output=True, text=True, timeout=120,
                         encoding="utf-8", errors="replace", env=child_env)
    check("changelog single source", out.returncode == 0, ((out.stdout or "") + (out.stderr or "")).strip()[-140:])

    summarize()


def summarize():
    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results)} checks, {len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
