"""Пересобирает zapret_data.zip из папки zapret_data/<FOLDER_NAME>.

Запуск: python tools/rebuild_zip.py
Корень архива — имя папки (как ожидает лаунчер), файлы кладутся 1:1.
"""
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "zapret_new_win.py")
OUT = os.path.join(ROOT, "zapret_data.zip")


def main():
    with open(MAIN, encoding="utf-8") as f:
        src = f.read()
    match = re.search(r'FOLDER_NAME\s*=\s*"([^"]+)"', src)
    if not match:
        print("FOLDER_NAME не найден в zapret_new_win.py")
        return 1
    folder_name = match.group(1)
    folder = os.path.join(ROOT, "zapret_data", folder_name)
    if not os.path.isdir(folder):
        print(f"Папка не найдена: {folder}")
        return 1
    if not os.path.exists(os.path.join(folder, "bin", "winws.exe")):
        print("В папке нет bin/winws.exe — отказ от сборки")
        return 1

    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _dirnames, filenames in os.walk(folder):
            for name in filenames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, folder).replace("\\", "/")
                z.write(full, f"{folder_name}/{rel}")
                count += 1

    with zipfile.ZipFile(OUT) as z:
        bad = z.testzip()
    size_mb = round(os.path.getsize(OUT) / 1048576, 2)
    print(f"OK: {count} файлов, {size_mb} МБ, integrity={'ok' if bad is None else bad}")
    return 0 if bad is None else 1


if __name__ == "__main__":
    sys.exit(main())
