import hashlib
import os

# Имя твоего скомпилированного файла
filename = "Zapret.exe"

def get_file_hash(path):
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        # Читаем файл кусками, чтобы не забивать память
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

if os.path.exists(filename):
    print(f"--- ХЕШ ДЛЯ ФАЙЛА {filename} ---")
    print(get_file_hash(filename))
    print("-----------------------------------")
    print("Скопируй этот код в свой version.json на GitHub")
    input("\nНажми Enter, чтобы выйти...")
else:
    print(f"Файл {filename} не найден! Положи этот скрипт рядом с exe.")