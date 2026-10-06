"""pytest-набор Windows-интеграции панели задач (17.5)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import win_taskbar as tb  # noqa: E402


def test_no_hwnd_is_safe_noop():
    taskbar = tb.TaskbarIntegration(None)
    assert taskbar.enabled is False
    assert taskbar.set_overlay("ON") is False
    assert taskbar.clear_overlay() is False
    assert taskbar.set_progress(5, 10) is False
    assert taskbar.set_progress(None) is False
    assert taskbar.add_buttons([(1, "x", "power")]) is False
    assert taskbar.update_buttons([(1, "x", "power")]) is False
    assert taskbar.flash_error() is False
    taskbar.register_button(1, lambda: None)
    taskbar.close()
    assert taskbar.enabled is False


def test_available_is_bool():
    assert isinstance(tb.available(), bool)


def test_status_colors_cover_all_states():
    for state in ("ON", "OFF", "BUSY", "ERROR"):
        assert state in tb.STATUS_COLORS
        assert tb.STATUS_COLORS[state].startswith("#")


def test_make_icon_ico(tmp_path):
    try:
        import PIL  # noqa: F401
    except Exception:
        return
    for kind in ("dot", "power", "test", "list", "unknown-kind"):
        path = str(tmp_path / f"{kind}.ico")
        result = tb.make_icon_ico(path, kind, "#22c55e")
        assert result == path
        with open(path, "rb") as f:
            header = f.read(4)
        assert header[:4] == b"\x00\x00\x01\x00"
    assert tb.make_icon_ico(str(tmp_path / "x.ico"), "dot") is not None
