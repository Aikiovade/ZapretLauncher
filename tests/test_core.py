"""pytest-набор для чистых функций ядра (H1). Запуск: python -m pytest -q"""
import atexit
import json
import os
import shutil
import sys
import tempfile
import urllib.parse

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# Изоляция: тесты не пишут в реальный каталог данных/лог пользователя
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="zapret_tests_")
os.environ.setdefault("ZAPRET_DATA_DIR", _TEST_DATA_DIR)
atexit.register(lambda: shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True))

import zapret_new_win as app  # noqa: E402


def test_validate_port_range():
    assert app.validate_port_range("12") == "12"
    assert app.validate_port_range("1024-1934,1936-65535") == "1024-1934,1936-65535"
    assert app.validate_port_range("") is None
    assert app.validate_port_range("0-10") is None
    assert app.validate_port_range("1-2-3") is None
    assert app.validate_port_range("70000") is None
    assert app.validate_port_range("100-50") is None


def test_split_windows_args():
    tokens = app.split_windows_args('-a --hostlist="C:\\Program Files\\x.txt" --ipset-exclude="C:\\y.txt"')
    assert tokens == ["-a", "--hostlist=C:\\Program Files\\x.txt", "--ipset-exclude=C:\\y.txt"]


def test_i18n_parity():
    assert set(app.TRANSLATIONS_DATA["RU"]) == set(app.TRANSLATIONS_DATA["EN"])


def test_package_version_key():
    assert app._package_version_key("zapret-discord-youtube-1.10.3") == (1, 10, 3)
    assert app._package_version_key("zapret-discord-youtube-1.9.9") < (1, 10, 3)


def test_trusted_urls():
    assert app.is_trusted_update_url(
        "https://github.com/Aikiovade/ZapretLauncher/releases/download/v17.4/Zapret.exe")
    assert not app.is_trusted_update_url("https://evil.example.com/Aikiovade/ZapretLauncher/x.exe")
    assert not app.is_trusted_update_url("http://github.com/Aikiovade/ZapretLauncher/x.exe")
    assert app.is_trusted_github_url(
        "https://github.com/Flowseal/zapret-discord-youtube/releases/download/1.10.3/x.zip")
    assert not app.is_trusted_github_url("https://evil.example.com/Flowseal/x.zip")


def test_proxy_link():
    cfg = {"host": "127.0.0.1", "port": 1443, "secret": "ab" * 16}
    assert app.proxy_link(cfg) == "tg://proxy?server=127.0.0.1&port=1443&secret=dd" + "ab" * 16
    assert app.proxy_link({"host": "127.0.0.1", "port": 1443, "secret": "cd"}).endswith("secret=ddcd")


def test_score_probe_results():
    assert app.score_probe_results({"a": 1, "b": -1, "c": 3}) == pytest.approx(2 / 3)
    assert app.score_probe_results({}) == 0.0


def _make_pkg(root):
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "winws.exe").write_bytes(b"x")
    (root / app.TGWS_PROXY_EXE).write_bytes(b"x")
    (root / "lists").mkdir()
    (root / "general.bat").write_text("rem", encoding="utf-8")
    return root


def test_payload_complete(tmp_path):
    pkg = _make_pkg(tmp_path / "zapret-discord-youtube-1.0.0")
    assert app.payload_complete(str(pkg))
    os.remove(str(pkg / "general.bat"))
    assert not app.payload_complete(str(pkg))
    assert not app.payload_complete(str(tmp_path / "missing"))
    assert not app.payload_complete("")


def test_rotate_log_file(tmp_path):
    log = tmp_path / "test.log"
    log.write_text("x" * 100, encoding="utf-8")
    assert app._rotate_log_file(str(log), max_bytes=10) is True
    assert (tmp_path / "test.log.1").exists()
    assert not log.exists()
    assert app._rotate_log_file(str(log), max_bytes=10) is False


def test_build_issue_url():
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    tail = f"line1\n{user}\\path\\file" if user else "line1"
    url = app.build_issue_url("17.4", strategy="general.bat", os_info="Windows-test", log_tail=tail)
    assert url.startswith("https://github.com/Aikiovade/ZapretLauncher/issues/new?")
    text = urllib.parse.unquote(url)
    assert "17.4" in text and "general.bat" in text
    if user:
        assert "<user>" in text and user not in text


def test_read_game_filter(tmp_path):
    utils = tmp_path / "utils"
    utils.mkdir()
    (utils / app.GAME_FILTER_FILE).write_text("mode=tcp\ntcp=1024-1934,1936-65535\nudp=1024-65535\n",
                                              encoding="utf-8")
    assert app.read_game_filter(str(tmp_path)) == ("1024-1934,1936-65535", "12", "1024-1934,1936-65535")
    assert app.read_game_filter(str(tmp_path / "nope")) == ("12", "12", "12")


def test_parse_current_package_bats():
    pkg = os.path.join(ROOT, "zapret_data", app.FOLDER_NAME)
    if not os.path.isdir(pkg):
        pytest.skip("пакет не найден")
    bats = app.list_strategies(pkg)
    assert bats, "в пакете нет стратегий"
    for bat in bats:
        args = app.parse_strategy_bat(os.path.join(pkg, bat), pkg)
        assert args, f"не разобран {bat}"
        assert "--wf-tcp" in args and "%" not in args


def test_golden_strategy_args():
    """H8: golden-набор разбора стратегий текущего пакета (tests/golden/<FOLDER_NAME>.json)."""
    golden_path = os.path.join(ROOT, "tests", "golden", f"{app.FOLDER_NAME}.json")
    if not os.path.exists(golden_path):
        pytest.skip("golden-набор отсутствует (python tools/gen_golden.py)")
    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)
    pkg = os.path.join(ROOT, "zapret_data", app.FOLDER_NAME)
    assert golden, "пустой golden-набор"
    for bat, expected in golden.items():
        actual = app.parse_strategy_bat(os.path.join(pkg, bat), pkg)
        assert actual == expected, f"регрессия парсера: {bat}"


def test_ed25519_rfc8032_vectors():
    """E1: проверка Ed25519 по тест-векторам RFC 8032."""
    import ed25519
    seed1 = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
    pub1 = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    sig1 = ("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
            "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    assert ed25519.publickey(seed1) == pub1
    assert ed25519.sign(seed1, b"") == sig1
    assert ed25519.verify(pub1, b"", sig1)
    assert not ed25519.verify(pub1, b"x", sig1)
    seed2 = "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb"
    pub2 = "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c"
    msg2 = bytes([0x72])
    assert ed25519.verify(pub2, msg2, ed25519.sign(seed2, msg2))


def test_manifest_signature():
    import ed25519
    seed = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
    pub = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    data = {"version": "1.0", "hash": "AB"}
    data["signature"] = ed25519.sign(seed, app.manifest_signing_payload(data))
    old = app.UPDATE_PUBKEY_HEX
    try:
        app.UPDATE_PUBKEY_HEX = pub
        assert app.manifest_signature_ok(data)
        data["version"] = "1.1"
        assert not app.manifest_signature_ok(data)
        del data["signature"]
        assert not app.manifest_signature_ok(data)
    finally:
        app.UPDATE_PUBKEY_HEX = old


def test_update_channels_and_mirrors():
    assert app.update_manifest_url("beta").endswith("update_info_beta.json")
    assert app.update_manifest_url("stable") == app.UPDATE_VERSION_URL
    assert app.update_manifest_url("weird") == app.UPDATE_VERSION_URL
    good = "https://github.com/Aikiovade/ZapretLauncher/releases/download/v1/x.exe"
    bad = "https://evil.example.com/x.exe"
    info = {"download_url": good, "mirrors": [bad, good]}
    assert app.update_download_candidates(info) == [good]
    assert app.update_download_candidates({}) == []


def test_detect_quality_and_battery():
    assert app.detect_quality_preset() in ("low", "medium", "high")
    battery = app.battery_state()
    assert set(battery) == {"present", "on_battery", "percent"}
    assert isinstance(app.seconds_since_last_input(), int)


def test_backend_mock_and_dev(monkeypatch):
    backend = app.MockBackend()
    assert backend.start("dir", "bat") and backend.health_ok() and backend.process_running()
    assert backend.stop() and not backend.health_ok()
    monkeypatch.setenv("ZAPRET_DEV", "1")
    assert app.is_dev_mode() and app.get_backend().name == "mock"
    monkeypatch.delenv("ZAPRET_DEV")
    monkeypatch.setattr(sys, "argv", ["pytest"])
    assert not app.is_dev_mode() and app.get_backend().name == "winws"


def test_strategy_meta(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "general (ALT).bat").write_text("rem", encoding="utf-8")
    (pkg / "general (ALT).bat.json").write_text(json.dumps({"tags": ["custom"]}), encoding="utf-8")
    meta = app.load_strategy_meta(str(pkg))
    assert "general (ALT).bat" in meta
    tags = meta["general (ALT).bat"]["tags"]
    assert "custom" in tags and "ALT" in tags and "GENERAL" in tags
    (pkg / "extra.bat").write_text("rem", encoding="utf-8")
    assert "extra.bat" in app.load_strategy_meta(str(pkg))


def test_crash_handler_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "CRASH_DIR", str(tmp_path / "crashes"))
    monkeypatch.setattr(app, "ensure_app_data", lambda: None)
    old_hook = sys.excepthook
    try:
        app.install_crash_handler("test")
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            sys.excepthook(*sys.exc_info())
        files = os.listdir(tmp_path / "crashes")
        assert files
        with open(os.path.join(tmp_path / "crashes", files[0]), encoding="utf-8") as f:
            content = f.read()
        assert "boom" in content and "test" in content
    finally:
        sys.excepthook = old_hook


def test_discord_presence_noop():
    import discord_rpc
    presence = discord_rpc.DiscordPresence("")
    assert presence.available is False
    assert presence.update(details="d", state="s") is False
    presence.close()


def test_discord_payload():
    import time as _time
    payload = app.discord_payload("ON", "general.bat", _time.time() - 65, "RU")
    assert payload["details"].startswith(app.TRANSLATIONS_DATA["RU"]["btn_strategy"])
    assert "00:01:05" in payload["state"]
    off = app.discord_payload("OFF", "general.bat", 0, "EN")
    assert off["state"] == "OFF" and off["start"] is None
    busy = app.discord_payload("BUSY", "general.bat", 0, "EN")
    assert busy["state"] == app.TRANSLATIONS_DATA["EN"]["status_busy"]


def test_installer_helpers():
    good = "https://github.com/Aikiovade/ZapretLauncher/releases/download/v1/ZapretLauncher-1-setup.exe"
    assert app.installer_update_available({"installer_url": good, "installer_sha256": "AB"})
    assert not app.installer_update_available({"installer_url": good, "installer_sha256": ""})
    assert not app.installer_update_available({"installer_url": "https://evil.example.com/x.exe",
                                               "installer_sha256": "AB"})
    assert app.installed_exe_path().endswith(os.path.join("ZapretLauncher", "Zapret.exe"))
    assert app.update_mode() in ("portable", "installed")
    assert app.data_dir_mode() in ("portable", "programdata", "legacy")


def test_ci_update_manifest(tmp_path, monkeypatch):
    import hashlib
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ci_update_manifest", os.path.join(ROOT, "tools", "ci_update_manifest.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    exe = tmp_path / "Zapret.exe"
    exe.write_bytes(b"exe-bytes")
    manifest = tmp_path / "update_info.json"
    manifest.write_text(json.dumps({"version": "1.0"}), encoding="utf-8")
    monkeypatch.delenv("MANIFEST_SIGNING_KEY", raising=False)
    rc = mod.main(["--exe", str(exe), "--manifest", str(manifest), "--repo", "o/r", "--tag", "v1.0",
                   "--setup-glob", str(tmp_path / "none-*.exe")])
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert rc == 0
    assert data["hash"] == hashlib.sha256(b"exe-bytes").hexdigest().upper()
    assert "signature" not in data


def test_install_mode_helpers():
    assert app.installed_components() in ("web", "tk")
    assert isinstance(app.recorded_install_mode(), dict)
    assert app.record_install_mode() == {}  # не frozen -> ничего не пишем
    assert app.installed_exe_path("ZapretWeb.exe").endswith(os.path.join("ZapretLauncher", "ZapretWeb.exe"))
