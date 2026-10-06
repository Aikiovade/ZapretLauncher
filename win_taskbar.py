"""Windows-интеграция 2.0 (17.5): панель задач через ITaskbarList3.

Оверлей-иконка статуса, кнопки на эскизе, прогресс на иконке и вспышка окна.
Модуль опционален: при любой ошибке/недоступности COM тихо отключается,
все вызовы становятся no-op и возвращают False.
"""
from __future__ import annotations

import ctypes
import os
import sys
import tempfile
from ctypes import wintypes

IS_WINDOWS = sys.platform == "win32"
_HRESULT = ctypes.c_long

STATUS_COLORS = {
    "ON": "#22c55e",
    "OFF": "#7c8291",
    "BUSY": "#eab308",
    "TESTING": "#eab308",
    "ERROR": "#ef4444",
}

WM_COMMAND = 0x0111
THBN_CLICKED = 0x1800
GA_ROOT = 2

THB_ICON = 0x00000002
THBF_ENABLED = 0x00000000
THBF_DISMISSONCLICK = 0x00000002

TBPF_NOPROGRESS = 0x0
TBPF_INDETERMINATE = 0x1
TBPF_NORMAL = 0x2
TBPF_ERROR = 0x4
TBPF_PAUSED = 0x8

FLASHW_ALL = 0x00000003
FLASHW_TIMERNOFG = 0x0000000C


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]


class THUMBBUTTON(ctypes.Structure):
    _fields_ = [
        ("dwMask", wintypes.DWORD),
        ("iId", wintypes.UINT),
        ("iBitmap", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("pszTip", ctypes.c_wchar * 260),
        ("dwFlags", wintypes.DWORD),
    ]


class FLASHWINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("hwnd", wintypes.HWND),
        ("dwFlags", wintypes.DWORD),
        ("uCount", wintypes.UINT),
        ("dwTimeout", wintypes.DWORD),
    ]


SUBCLASSPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                                  wintypes.WPARAM, wintypes.LPARAM,
                                  ctypes.c_ulonglong, ctypes.c_ulonglong)

CLSID_TASKBAR_LIST = "{56FDF344-FD6D-11D0-958A-006097C9A090}"
IID_TASKBAR_LIST3 = "{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}"

_VTBL_HR_INIT = 3
_VTBL_SET_PROGRESS_VALUE = 9
_VTBL_SET_PROGRESS_STATE = 10
_VTBL_THUMB_BAR_ADD_BUTTONS = 15
_VTBL_THUMB_BAR_UPDATE_BUTTONS = 16
_VTBL_SET_OVERLAY_ICON = 18


def available():
    """Доступна ли интеграция (Windows + COM без ошибок)."""
    return IS_WINDOWS


def _guid_from_string(text):
    if not IS_WINDOWS:
        return None
    guid = GUID()
    ole32 = ctypes.windll.ole32
    ole32.CLSIDFromString.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(GUID)]
    ole32.CLSIDFromString.restype = _HRESULT
    if ole32.CLSIDFromString(text, ctypes.byref(guid)) < 0:
        return None
    return guid


def make_icon_ico(path, kind="dot", color="#22c55e", size=32):
    """Сгенерировать .ico (Pillow) с простым глифом; возвращает путь или None."""
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    try:
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        edge = max(2, size // 12)
        if kind == "dot":
            draw.ellipse((edge, edge, size - edge, size - edge), fill=color,
                         outline="#0a0b1e", width=max(1, size // 16))
        elif kind == "power":
            draw.ellipse((edge, edge, size - edge, size - edge), outline=color, width=edge)
            draw.rectangle((size // 2 - size // 12, edge, size // 2 + size // 12, size // 2), fill=color)
        elif kind == "test":
            draw.line((size * 0.2, size * 0.55, size * 0.42, size * 0.78,
                       size * 0.8, size * 0.28), fill=color, width=edge, joint="curve")
        elif kind == "list":
            for i in range(3):
                y = size * (0.25 + 0.25 * i)
                draw.rectangle((size * 0.2, y, size * 0.8, y + edge), fill=color)
        else:
            draw.ellipse((edge, edge, size - edge, size - edge), fill=color)
        image.save(path, format="ICO", sizes=[(16, 16), (32, 32)])
        return path
    except Exception:
        return None


class TaskbarIntegration:
    """Обёртка ITaskbarList3; при hwnd=None или ошибке — безопасный no-op."""

    def __init__(self, hwnd, icon_dir=None, logger=None):
        self.enabled = False
        self._ptr = None
        self._hwnd = int(hwnd) if hwnd else 0
        self._icon_dir = icon_dir or os.path.join(tempfile.gettempdir(), "zapret_taskbar_icons")
        self._icons = {}
        self._button_cb = {}
        self._buttons_added = False
        self._subclass_proc = None
        self._subclass_id = 0x5A50
        self._default_proc = None
        self._log = logger or (lambda *_a, **_k: None)
        self._com_inited = False
        if not IS_WINDOWS or not self._hwnd:
            return
        try:
            root = ctypes.windll.user32.GetAncestor(self._hwnd, GA_ROOT)
            if root:
                self._hwnd = int(root)
            self._init_com()
            self.enabled = self._init_hr() == 0
        except Exception as exc:
            self._log(f"taskbar init error: {exc}")
            self.enabled = False

    def _init_com(self):
        ole32 = ctypes.windll.ole32
        ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        ole32.CoInitializeEx.restype = _HRESULT
        ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.c_ulong,
                                           ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        ole32.CoCreateInstance.restype = _HRESULT
        if ole32.CoInitializeEx(None, 0x2) == 0:
            self._com_inited = True
        clsid = _guid_from_string(CLSID_TASKBAR_LIST)
        iid = _guid_from_string(IID_TASKBAR_LIST3)
        if clsid is None or iid is None:
            return
        ptr = ctypes.c_void_p()
        ole32.CoCreateInstance(ctypes.byref(clsid), None, 0x1, ctypes.byref(iid), ctypes.byref(ptr))
        self._ptr = ptr

    def _vtable_entry(self, index):
        vtable = ctypes.cast(self._ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return vtable[index]

    def _init_hr(self):
        if not self._ptr:
            return -1
        try:
            func = ctypes.WINFUNCTYPE(_HRESULT, ctypes.c_void_p)(self._vtable_entry(_VTBL_HR_INIT))
            return int(func(self._ptr))
        except Exception:
            return -1

    def _load_icon(self, key, kind, color):
        if key in self._icons:
            return self._icons[key]
        try:
            os.makedirs(self._icon_dir, exist_ok=True)
            path = os.path.join(self._icon_dir, f"{key}.ico")
            if not os.path.exists(path) and not make_icon_ico(path, kind, color):
                return None
            user32 = ctypes.windll.user32
            user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                                          ctypes.c_int, ctypes.c_int, wintypes.UINT]
            user32.LoadImageW.restype = wintypes.HANDLE
            icon = user32.LoadImageW(None, path, 1, 16, 16, 0x10)
            self._icons[key] = icon
            return icon
        except Exception:
            return None

    def set_overlay(self, status):
        """Оверлей-точка статуса на иконке в панели задач."""
        if not self.enabled:
            return False
        try:
            color = STATUS_COLORS.get(status, STATUS_COLORS["OFF"])
            icon = self._load_icon(f"dot_{status}", "dot", color)
            func = ctypes.WINFUNCTYPE(_HRESULT, ctypes.c_void_p, wintypes.HWND, wintypes.HICON,
                                      wintypes.LPCWSTR)(self._vtable_entry(_VTBL_SET_OVERLAY_ICON))
            return int(func(self._ptr, self._hwnd, icon, f"Zapret: {status}")) == 0
        except Exception:
            return False

    def clear_overlay(self):
        if not self.enabled:
            return False
        try:
            func = ctypes.WINFUNCTYPE(_HRESULT, ctypes.c_void_p, wintypes.HWND, wintypes.HICON,
                                      wintypes.LPCWSTR)(self._vtable_entry(_VTBL_SET_OVERLAY_ICON))
            return int(func(self._ptr, self._hwnd, None, None)) == 0
        except Exception:
            return False

    def set_progress(self, value=None, total=100, state=None):
        """Прогресс на иконке: value=None очищает, state переопределяет (error/paused)."""
        if not self.enabled:
            return False
        try:
            state_func = ctypes.WINFUNCTYPE(_HRESULT, ctypes.c_void_p, wintypes.HWND,
                                            ctypes.c_int)(self._vtable_entry(_VTBL_SET_PROGRESS_STATE))
            value_func = ctypes.WINFUNCTYPE(_HRESULT, ctypes.c_void_p, wintypes.HWND,
                                            ctypes.c_ulonglong,
                                            ctypes.c_ulonglong)(self._vtable_entry(_VTBL_SET_PROGRESS_VALUE))
            if value is None:
                return int(state_func(self._ptr, self._hwnd, TBPF_NOPROGRESS)) == 0
            flag = {"error": TBPF_ERROR, "paused": TBPF_PAUSED}.get(state or "", TBPF_NORMAL)
            state_func(self._ptr, self._hwnd, flag)
            return int(value_func(self._ptr, self._hwnd, int(value), max(1, int(total)))) == 0
        except Exception:
            return False

    @property
    def buttons_added(self):
        return self._buttons_added

    def register_button(self, button_id, callback):
        self._button_cb[int(button_id)] = callback

    def add_buttons(self, buttons):
        """buttons: [(id, tooltip, glyph)] — кнопки на эскизе панели задач."""
        if not self.enabled or self._buttons_added:
            return False
        try:
            structs = (THUMBBUTTON * len(buttons))()
            for index, (button_id, tooltip, glyph) in enumerate(buttons):
                item = structs[index]
                item.dwMask = THB_ICON
                item.iId = int(button_id)
                item.hIcon = self._load_icon(f"glyph_{glyph}", glyph, "#e5e7eb")
                item.pszTip = str(tooltip)[:259]
                item.dwFlags = THBF_ENABLED | THBF_DISMISSONCLICK
            func = ctypes.WINFUNCTYPE(_HRESULT, ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                      ctypes.POINTER(THUMBBUTTON))(
                self._vtable_entry(_VTBL_THUMB_BAR_ADD_BUTTONS))
            result = int(func(self._ptr, self._hwnd, len(buttons), structs))
            self._buttons_added = result == 0
            if self._buttons_added:
                self._install_subclass()
            return self._buttons_added
        except Exception as exc:
            self._log(f"taskbar buttons error: {exc}")
            return False

    def update_buttons(self, buttons):
        if not self.enabled or not self._buttons_added:
            return False
        try:
            structs = (THUMBBUTTON * len(buttons))()
            for index, (button_id, tooltip, glyph) in enumerate(buttons):
                item = structs[index]
                item.dwMask = THB_ICON
                item.iId = int(button_id)
                item.hIcon = self._load_icon(f"glyph_{glyph}", glyph, "#e5e7eb")
                item.pszTip = str(tooltip)[:259]
                item.dwFlags = THBF_ENABLED | THBF_DISMISSONCLICK
            func = ctypes.WINFUNCTYPE(_HRESULT, ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                      ctypes.POINTER(THUMBBUTTON))(
                self._vtable_entry(_VTBL_THUMB_BAR_UPDATE_BUTTONS))
            return int(func(self._ptr, self._hwnd, len(buttons), structs)) == 0
        except Exception:
            return False

    def _install_subclass(self):
        try:
            comctl32 = ctypes.windll.comctl32
            comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, SUBCLASSPROC,
                                                   ctypes.c_ulonglong, ctypes.c_ulonglong]
            comctl32.SetWindowSubclass.restype = wintypes.BOOL
            comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT,
                                                 wintypes.WPARAM, wintypes.LPARAM]
            comctl32.DefSubclassProc.restype = ctypes.c_ssize_t
        except Exception:
            return False

        def _proc(hwnd, msg, wparam, lparam, _uid, _ref):
            if msg == WM_COMMAND:
                code = (int(wparam) >> 16) & 0xFFFF
                if code == THBN_CLICKED:
                    callback = self._button_cb.get(int(wparam) & 0xFFFF)
                    if callback:
                        try:
                            callback()
                        except Exception as exc:
                            self._log(f"taskbar button callback error: {exc}")
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

        self._subclass_proc = SUBCLASSPROC(_proc)
        try:
            ok = bool(comctl32.SetWindowSubclass(self._hwnd, self._subclass_proc,
                                                 self._subclass_id, 0))
            if not ok:
                self._subclass_proc = None
            return ok
        except Exception:
            self._subclass_proc = None
            return False

    def flash_error(self, count=3):
        """Вспышка окна в панели задач при сбое."""
        if not IS_WINDOWS or not self._hwnd:
            return False
        try:
            info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), self._hwnd,
                              FLASHW_ALL | FLASHW_TIMERNOFG, count, 0)
            return bool(ctypes.windll.user32.FlashWindowEx(ctypes.byref(info)))
        except Exception:
            return False

    def close(self):
        try:
            if self._subclass_proc is not None:
                try:
                    ctypes.windll.comctl32.RemoveWindowSubclass(self._hwnd, self._subclass_proc,
                                                                self._subclass_id)
                except Exception:
                    pass
                self._subclass_proc = None
            self.clear_overlay()
        except Exception:
            pass
        for icon in list(self._icons.values()):
            try:
                if icon:
                    ctypes.windll.user32.DestroyIcon(icon)
            except Exception:
                pass
        self._icons.clear()
        if self._ptr:
            try:
                release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(self._vtable_entry(2))
                release(self._ptr)
            except Exception:
                pass
            self._ptr = None
        if self._com_inited:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass
            self._com_inited = False
        self.enabled = False
        self._buttons_added = False
