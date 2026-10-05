"""A9/I3: portable-сборка — zip с exe и флагом portable.txt (данные рядом с exe).

Запуск: python tools/make_portable.py [Zapret.exe|ZapretWeb.exe]
Результат: dist/<имя exe>-<версия>-portable.zip
Содержимое: <ExeName>, portable.txt, README-PORTABLE.txt
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import zapret_new_win as core  # noqa: E402

PORTABLE_README = """ZapretLauncher (portable)
=========================
1. Распакуйте архив в любую папку.
2. При первом запуске рядом с exe появится каталог ZapretLauncher_data —
   в нём конфиг, логи и данные пакета (ничего не пишется в C:\\ZapretLauncher).
3. Для удаления достаточно закрыть приложение и удалить папку.
   Службу zapret/WinDivert можно удалить скриптом tools\\uninstall.ps1 из репозитория.
"""


def main(argv=None):
    argv = argv or sys.argv[1:]
    exe_name = argv[0] if argv else "Zapret.exe"
    exe_path = os.path.join(ROOT, "dist", exe_name)
    if not os.path.exists(exe_path):
        print(f"Не найден {exe_path} — сначала соберите exe (PyInstaller)")
        return 1
    out = os.path.join(ROOT, "dist", f"{os.path.splitext(exe_name)[0]}-{core.CURRENT_VERSION}-portable.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe_path, exe_name)
        z.writestr(core.PORTABLE_FLAG_FILE, "portable mode\n")
        z.writestr("README-PORTABLE.txt", PORTABLE_README)
    size_mb = round(os.path.getsize(out) / 1048576, 2)
    print(f"OK: {out} ({size_mb} МБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
