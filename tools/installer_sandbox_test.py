"""A9/I3: безопасная проверка установщика в песочнице.

Собирает обезвреженную копию installer/zapret_launcher.iss:
  - без [Run]/[UninstallRun]/[Dirs]/[Icons]/[Tasks] (никакой службы, ProgramData, ярлыков, реестра);
  - установка в %TEMP%\\ZapretSandbox, Uninstallable=no, PrivilegesRequired=lowest.
Затем ставит её SILENT дважды (/COMPONENTS=tk и web) и проверяет файлы.

Запуск: python tools/installer_sandbox_test.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISS_SRC = os.path.join(ROOT, "installer", "zapret_launcher.iss")
SANDBOX_DIR = os.path.join(tempfile.gettempdir(), "ZapretSandbox")
STRIP_SECTIONS = ("[Run]", "[UninstallRun]", "[Dirs]", "[Icons]", "[Tasks]")


def strip_sections(text):
    out = []
    skip = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            skip = stripped in STRIP_SECTIONS
        if not skip:
            out.append(line)
    return "\n".join(out)


def main():
    if not shutil.which("iscc"):
        print("SKIP: iscc (Inno Setup) не найден в PATH")
        return 0
    work = os.path.join(tempfile.gettempdir(), "zapret_sandbox_build")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    shutil.rmtree(SANDBOX_DIR, ignore_errors=True)

    with open(ISS_SRC, encoding="utf-8") as f:
        text = f.read()
    text = strip_sections(text)
    text = text.replace("AppId={{A1B6A0F4-8C2E-4E9B-9B3B-1F5C7D2A9E10}", "AppId={{BBBB0000-0000-0000-0000-00000000SANDBOX}")
    text = text.replace("DefaultDirName={autopf}\\{#AppName}", "DefaultDirName=" + SANDBOX_DIR.replace("\\", "\\\\"))
    text = text.replace("PrivilegesRequired=admin", "PrivilegesRequired=lowest")
    text = text.replace("OutputDir=..\\dist", "OutputDir=" + work.replace("\\", "\\\\"))
    text = text.replace("OutputBaseFilename=ZapretLauncher-{#AppVersion}-setup", "OutputBaseFilename=sandbox-setup")
    text = text.replace("UninstallDisplayIcon={uninstallexe}\n", "")
    text = text.replace("CloseApplications=yes\n", "")
    text = text.replace("DisableProgramGroupPage=yes", "DisableProgramGroupPage=yes\nUninstallable=no\nDisableDirPage=yes")
    text = text.replace('Source: "..\\dist\\', 'Source: "' + os.path.join(ROOT, "dist").replace("\\", "\\\\") + "\\\\")
    text = text.replace('Source: "..\\tools\\', 'Source: "' + os.path.join(ROOT, "tools").replace("\\", "\\\\") + "\\\\")

    # .iss пишем рядом с оригиналом, иначе относительные пути (арт/звуки) не найдутся
    iss_path = os.path.join(ROOT, "installer", "_sandbox_test.iss")
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("[1/4] Компиляция песочного установщика...")
    res = subprocess.run(["iscc", iss_path], capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        print("FAIL: компиляция:", (res.stdout or "")[-400:], (res.stderr or "")[-200:])
        return 1

    setup = os.path.join(work, "sandbox-setup.exe")
    if not os.path.exists(setup):
        print("FAIL: setup не найден:", setup)
        return 1

    ok = True
    print("[2/4] Silent-установка (только Tk-версия) ...")
    res = subprocess.run([setup, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                         capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        print("FAIL: код", res.returncode, (res.stdout or "")[-200:])
        ok = False
    else:
        target = os.path.join(SANDBOX_DIR, "Zapret.exe")
        if not os.path.exists(target):
            print("FAIL: нет", target)
            ok = False
        elif os.path.exists(os.path.join(SANDBOX_DIR, "ZapretWeb.exe")):
            print("FAIL: в установщике не должно быть ZapretWeb.exe")
            ok = False
        else:
            print("      ok: Zapret.exe (без ZapretWeb.exe)")

    print("[3/4] Очистка...")
    shutil.rmtree(SANDBOX_DIR, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    try:
        os.remove(iss_path)
    except OSError:
        pass
    print("[4/4]", "PASS: песочный тест установщика" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
