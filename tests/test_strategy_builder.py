"""pytest-набор конструктора стратегий (17.5). Запуск: python -m pytest -q"""
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import strategy_builder as sb  # noqa: E402

SAMPLE_ARGS = (
    '--wf-tcp=80,443 --wf-udp=443 '
    '--filter-udp=443 --hostlist="C:\\Zapret\\lists\\list-general.txt" '
    '--dpi-desync=fake --dpi-desync-repeats=6 --new '
    '--filter-tcp=80,443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=ts '
    '--dpi-desync-fakedsplit-pattern=0x00'
)


def _make_pkg(tmp_path):
    pkg = tmp_path / "zapret-discord-youtube-1.10.3"
    (pkg / "bin").mkdir(parents=True)
    (pkg / "lists").mkdir()
    (pkg / "service.bat").write_text("rem", encoding="utf-8")
    return pkg


def test_split_args_quotes():
    tokens = sb.split_args('-a --hostlist="C:\\Program Files\\x.txt" --b=2')
    assert tokens == ["-a", "--hostlist=C:\\Program Files\\x.txt", "--b=2"]


def test_parse_segments_and_roundtrip():
    segments = sb.parse_args(SAMPLE_ARGS)
    assert len(segments) == 2
    assert segments[0].options[0].flag == "--wf-tcp"
    assert segments[1].options[0].flag == "--filter-tcp"
    assert sb.parse_args(SAMPLE_ARGS)[0].options[1].value == "443"
    plain = "--wf-tcp=80,443 --dpi-desync=fake --new --filter-tcp=443"
    assert sb.serialize_args(sb.parse_args(plain)) == plain


def test_parse_quoted_value_requoted_on_serialize():
    segments = sb.parse_args('--hostlist="C:\\Program Files\\a.txt"')
    assert segments[0].options[0].value == "C:\\Program Files\\a.txt"
    assert sb.serialize_args(segments) == '--hostlist="C:\\Program Files\\a.txt"'


def test_validate_ports_and_ints():
    assert sb.validate_value("--filter-tcp", "80,443,8443,19294-19344") is None
    assert sb.validate_value("--filter-tcp", "0") == "bad_ports"
    assert sb.validate_value("--filter-tcp", "70000") == "bad_ports"
    assert sb.validate_value("--filter-tcp", "100-50") == "bad_ports"
    assert sb.validate_value("--dpi-desync-repeats", "6") is None
    assert sb.validate_value("--dpi-desync-repeats", "0") == "out_of_range"
    assert sb.validate_value("--dpi-desync-repeats", "abc") == "not_number"
    assert sb.validate_value("--dpi-desync-repeats", None) == "value_required"


def test_validate_enum_and_placeholders():
    assert sb.validate_value("--dpi-desync", "fake,fakedsplit") is None
    assert sb.validate_value("--dpi-desync", "hack") == "bad_choice"
    assert sb.validate_value("--dpi-desync-fooling", "ts,md5sig") is None
    assert sb.validate_value("--hostlist", "%LISTS%list-general.txt") is None
    assert sb.validate_value("--hostlist", "100%bad") == "bad_placeholder"
    assert sb.validate_value("--hostlist", "a&b") == "forbidden_chars"
    assert sb.validate_value("--hostlist", 'ok"x') == "forbidden_chars"
    assert sb.validate_value("--hostlist", "ok'x") == "forbidden_chars"


def test_validate_args_flags_unknown_and_forbidden():
    assert sb.validate_args(SAMPLE_ARGS) == []
    errors = sb.validate_args("--wf-tcp=80 --unknown-flag=ok --dpi-desync=zzz")
    assert [e["flag"] for e in errors] == ["--dpi-desync"]
    errors = sb.validate_args("--custom=bad|value")
    assert errors and errors[0]["error"] == "forbidden_chars"


def test_validate_name():
    assert sb.validate_name("my strategy (2)") is None
    assert sb.validate_name("") == "empty"
    assert sb.validate_name("a" * 41) == "too_long"
    assert sb.validate_name("bad/name") == "bad_chars"
    assert sb.validate_name("custom_x") == "reserved_prefix"


def test_save_load_list_custom(tmp_path):
    pkg = _make_pkg(tmp_path)
    lists = os.path.join(str(pkg), "lists")
    args = (f'--wf-tcp=80,443 --hostlist="{lists}\\list-general.txt" '
            '--dpi-desync=fake --dpi-desync-repeats=6 --new '
            '--filter-tcp=443 --dpi-desync=fake,fakedsplit')
    result = sb.save_custom_strategy(str(pkg), "Моя стратегия", args,
                                     title="Моя стратегия", description="тест")
    assert result["ok"] is True
    bat_path = os.path.join(str(pkg), "custom_Моя стратегия.bat")
    assert os.path.exists(bat_path)
    assert os.path.exists(bat_path + ".json")
    with open(bat_path, encoding="utf-8") as f:
        content = f.read()
    assert "%~dp0bin\\" in content
    assert "%LISTS%list-general.txt" in content
    loaded = sb.load_strategy_args(bat_path, str(pkg))
    assert "--dpi-desync=fake" in loaded
    assert f"{lists}\\list-general.txt" in loaded
    items = sb.list_custom_strategies(str(pkg))
    assert [i["bat"] for i in items] == ["custom_Моя стратегия.bat"]
    assert sb.delete_custom_strategy(str(pkg), "general.bat")["ok"] is False
    assert sb.is_custom_strategy(str(pkg), "custom_Моя стратегия.bat")


def test_save_duplicate_needs_overwrite(tmp_path):
    pkg = _make_pkg(tmp_path)
    assert sb.save_custom_strategy(str(pkg), "dup", SAMPLE_ARGS)["ok"]
    again = sb.save_custom_strategy(str(pkg), "dup", SAMPLE_ARGS)
    assert again["ok"] is False and again["error"] == "exists"
    assert sb.save_custom_strategy(str(pkg), "dup", SAMPLE_ARGS, overwrite=True)["ok"]


def test_generated_bat_parses_back(tmp_path):
    pkg = _make_pkg(tmp_path)
    sb.save_custom_strategy(str(pkg), "roundtrip", SAMPLE_ARGS)
    bat_path = os.path.join(str(pkg), "custom_roundtrip.bat")
    with open(bat_path, encoding="utf-8") as f:
        raw_args = sb.extract_winws_args(f.read())
    assert raw_args.startswith("--wf-tcp=80,443")
    segments = sb.parse_args(sb.resolve_bat_paths(raw_args, str(pkg)))
    flags = {o.flag for seg in segments for o in seg.options}
    assert "--dpi-desync-fakedsplit-pattern" in flags


def test_export_import_roundtrip(tmp_path):
    pkg = _make_pkg(tmp_path)
    other = _make_pkg(tmp_path / "other")
    sb.save_custom_strategy(str(pkg), "share", SAMPLE_ARGS)
    zip_path = str(tmp_path / "share.zip")
    assert sb.export_custom_strategy(str(pkg), "custom_share.bat", zip_path)["ok"]
    imported = sb.import_custom_strategy(str(other), zip_path)
    assert imported["ok"] is True, imported
    assert os.path.exists(os.path.join(str(other), "custom_share.bat"))
    with open(os.path.join(str(other), "custom_share.bat"), encoding="utf-8") as f:
        content = f.read()
    assert "winws.exe" in content and "format" not in content.lower()


def test_import_sanitizes_malicious_bat(tmp_path):
    pkg = _make_pkg(tmp_path)
    evil_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as zf:
        zf.writestr("custom_evil.bat",
                    "@echo off\nstart winws.exe --wf-tcp=80 --ipset=1.1.1.1 & del /f q\nformat C:\n")
    result = sb.import_custom_strategy(str(pkg), str(evil_zip))
    assert result["ok"] is False and result["error"] == "invalid_args"


def test_import_rejects_bad_bundle(tmp_path):
    pkg = _make_pkg(tmp_path)
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("../custom_x.bat", "winws.exe --wf-tcp=80")
    assert sb.import_custom_strategy(str(pkg), str(bad_zip))["error"] == "bad_bundle"
    empty_zip = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty_zip, "w") as zf:
        zf.writestr("readme.txt", "hi")
    assert sb.import_custom_strategy(str(pkg), str(empty_zip))["error"] == "bad_bundle"


def test_import_rejects_oversized_json(tmp_path):
    pkg = _make_pkg(tmp_path)
    bomb = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb, "w") as zf:
        zf.writestr("custom_bomb.bat", "winws.exe --wf-tcp=80")
        zf.writestr("custom_bomb.bat.json", "x" * (sb.MAX_BUNDLE_BYTES + 1))
    assert sb.import_custom_strategy(str(pkg), str(bomb))["error"] == "too_big"
    assert not os.path.exists(os.path.join(str(pkg), "custom_bomb.bat"))


def test_import_auto_renames_on_collision(tmp_path):
    pkg = _make_pkg(tmp_path)
    sb.save_custom_strategy(str(pkg), "same", SAMPLE_ARGS)
    zip_path = str(tmp_path / "same.zip")
    sb.export_custom_strategy(str(pkg), "custom_same.bat", zip_path)
    result = sb.import_custom_strategy(str(pkg), zip_path)
    assert result["ok"] is True
    assert result["bat"] == "custom_same 2.bat"


def test_strategy_meta_reads_json(tmp_path):
    pkg = _make_pkg(tmp_path)
    sb.save_custom_strategy(str(pkg), "meta", SAMPLE_ARGS, title="Title", description="Desc")
    meta = sb.strategy_meta(str(pkg), "custom_meta.bat")
    assert meta["title"] == "Title" and meta["description"] == "Desc"
    with open(os.path.join(str(pkg), "custom_meta.bat.json"), encoding="utf-8") as f:
        assert json.load(f)["tags"] == ["custom"]
