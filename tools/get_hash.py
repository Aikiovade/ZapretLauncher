import hashlib
import os
import sys


def get_file_hash(path):
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("dist", "Zapret.exe")
    if os.path.exists(path):
        print(get_file_hash(path))
    else:
        print(f"Файл {path} не найден")
        sys.exit(1)
