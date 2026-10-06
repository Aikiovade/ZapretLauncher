"""Визуальный тест установщика: песочная сборка + скриншоты страниц.

Безопасно: [Run]/[UninstallRun]/[Dirs]/[Icons]/[Tasks] вырезаются, установка
в %TEMP%\\ZapretVisualSandbox, права lowest, без службы/ярлыков/реестра.
Песочный [Run] добавляет только безвредный чекбокс "Запустить" (cmd /c exit),
чтобы проверить раскладку страницы финала.

Запуск: python tools/installer_visual_test.py
Результат: %TEMP%\\zapret_visual\\*.png (1_intro, 2_installing, 2b_installing, 3_finished)
"""
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import ImageGrab

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISS_SRC = os.path.join(ROOT, "installer", "zapret_launcher.iss")
SANDBOX_DIR = os.path.join(tempfile.gettempdir(), "ZapretVisualSandbox")
WORK = os.path.join(tempfile.gettempdir(), "zapret_visual_build")
SHOTS = os.path.join(tempfile.gettempdir(), "zapret_visual")
STRIP_SECTIONS = ("[Run]", "[UninstallRun]", "[Dirs]", "[Icons]", "[Tasks]")

user32 = ctypes.windll.user32


def cleanup_leftovers():
    for image in ("visual-setup.exe", "visual-setup.tmp"):
        subprocess.run(["taskkill", "/F", "/IM", image], capture_output=True, timeout=30)
    for entry in os.listdir(tempfile.gettempdir()):
        if entry.startswith("is-") and entry.endswith(".tmp"):
            shutil.rmtree(os.path.join(tempfile.gettempdir(), entry), ignore_errors=True)


def strip_sections(text):
    out, skip = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            skip = stripped in STRIP_SECTIONS
        if not skip:
            out.append(line)
    return "\n".join(out)


def make_dummy(path, mb=150):
    if os.path.exists(path) and os.path.getsize(path) >= mb * 1024 * 1024:
        return
    with open(path, "wb") as f:
        chunk = os.urandom(1024 * 1024)
        for _ in range(mb):
            f.write(chunk)


def build_sandbox():
    shutil.rmtree(WORK, ignore_errors=True)
    shutil.rmtree(SANDBOX_DIR, ignore_errors=True)
    shutil.rmtree(SHOTS, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(SHOTS, exist_ok=True)
    dummy = os.path.join(WORK, "dummy.bin")
    make_dummy(dummy)
    with open(ISS_SRC, encoding="utf-8") as f:
        text = f.read()
    text = strip_sections(text)
    text = text.replace("AppId={{A1B6A0F4-8C2E-4E9B-9B3B-1F5C7D2A9E10}",
                        "AppId={{BBBB1111-1111-1111-1111-111111111111}")
    text = text.replace("DefaultDirName={autopf}\\{#AppName}",
                        "DefaultDirName=" + SANDBOX_DIR.replace("\\", "\\\\"))
    text = text.replace("PrivilegesRequired=admin", "PrivilegesRequired=lowest")
    text = text.replace("OutputDir=..\\dist", "OutputDir=" + WORK.replace("\\", "\\\\"))
    text = text.replace("OutputBaseFilename=ZapretLauncher-{#AppVersion}-setup",
                        "OutputBaseFilename=visual-setup")
    text = text.replace("UninstallDisplayIcon={uninstallexe}\n", "")
    text = text.replace("CloseApplications=yes\n", "")
    text = text.replace("DisableProgramGroupPage=yes",
                        "DisableProgramGroupPage=yes\nUninstallable=no\nDisableDirPage=yes")
    text = text.replace('Source: "..\\dist\\',
                        'Source: "' + os.path.join(ROOT, "dist").replace("\\", "\\\\") + "\\\\")
    text = text.replace('Source: "..\\tools\\',
                        'Source: "' + os.path.join(ROOT, "tools").replace("\\", "\\\\") + "\\\\")
    text += ("\n[Files]\n"
             'Source: "' + dummy.replace("\\", "\\\\") + '"; DestDir: "{app}"; Flags: ignoreversion\n'
             "\n[Run]\n"
             'Filename: "{sys}\\cmd.exe"; Parameters: "/c exit"; '
             'Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent\n')
    iss_path = os.path.join(ROOT, "installer", "_visual_test.iss")
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        res = subprocess.run(["iscc", iss_path], capture_output=True, text=True, timeout=600)
        if res.returncode != 0:
            print("COMPILE FAIL:", (res.stdout or "")[-400:], (res.stderr or "")[-600:])
            return None
    finally:
        try:
            os.remove(iss_path)
        except OSError:
            pass
    setup = os.path.join(WORK, "visual-setup.exe")
    return setup if os.path.exists(setup) else None


def find_setup_window():
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if "ZapretLauncher" in buf.value and "Chrome" not in buf.value:
            found.append(hwnd)
        return True

    user32.EnumWindows(enum_proc, 0)
    return found[0] if found else None


def window_rect(hwnd):
    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def press_enter():
    user32.keybd_event(0x0D, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(0x0D, 0, 2, 0)


def finished_page(hwnd):
    caps = set()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_child(h, _lparam):
        length = user32.GetWindowTextLengthW(h)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(h, buf, length + 1)
            caps.add(buf.value.strip().upper())
        return True

    user32.EnumChildWindows(hwnd, enum_child, 0)
    return any(c.startswith("ЗАКРЫТЬ") or c.startswith("CLOSE") for c in caps)


def shot(hwnd, name):
    left, top, right, bottom = window_rect(hwnd)
    pad = 8
    img = ImageGrab.grab(bbox=(left - pad, top - pad, right + pad, bottom + pad))
    os.makedirs(SHOTS, exist_ok=True)
    path = os.path.join(SHOTS, name + ".png")
    img.save(path)
    print("SHOT:", path, img.size)
    return path


def main():
    cleanup_leftovers()
    setup = build_sandbox()
    if not setup:
        return 1
    print("SETUP:", setup)
    proc = subprocess.Popen([setup, "/LANG=russian"])
    hwnd = None
    deadline = time.time() + 60
    while time.time() < deadline:
        hwnd = find_setup_window()
        if hwnd:
            break
        time.sleep(0.5)
    if not hwnd:
        print("FAIL: окно не найдено")
        proc.terminate()
        return 1
    user32.SetForegroundWindow(hwnd)
    time.sleep(2.2)
    shot(hwnd, "1_intro")
    press_enter()
    time.sleep(1.2)
    shot(hwnd, "2_installing")
    time.sleep(2.0)
    shot(hwnd, "2b_installing")
    deadline = time.time() + 120
    while time.time() < deadline:
        if proc.poll() is not None or finished_page(hwnd):
            break
        time.sleep(1.0)
    time.sleep(0.8)
    shot(hwnd, "3_finished")
    press_enter()
    time.sleep(0.6)
    if proc.poll() is None:
        proc.terminate()
    cleanup_leftovers()
    shutil.rmtree(SANDBOX_DIR, ignore_errors=True)
    print("DONE. Screenshots in", SHOTS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
