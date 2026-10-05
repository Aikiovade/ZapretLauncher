"""E1: подпись и проверка update_info.json (Ed25519, без зависимостей).

Генерация ключей:   python tools/sign_manifest.py --gen-keys keys.json
Подпись манифеста:  python tools/sign_manifest.py update_info.json --key keys.json
Проверка подписи:   python tools/sign_manifest.py update_info.json --pub <hex>
                    (или --key keys.json — возьмёт публичный ключ оттуда)

Публичный ключ из keys.json нужно вписать в zapret_new_win.py -> UPDATE_PUBKEY_HEX.
Файл keys.json — СЕКРЕТ: не коммитьте его (добавьте в .gitignore).
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import ed25519  # noqa: E402
import zapret_new_win as core  # noqa: E402


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def cmd_gen_keys(path):
    seed = os.urandom(32).hex()
    public = ed25519.publickey(seed)
    save_json(path, {"seed": seed, "public": public})
    print(f"Ключи сохранены: {path}")
    print(f"UPDATE_PUBKEY_HEX = \"{public}\"")
    return 0


def cmd_sign(path, key_path):
    keys = load_json(key_path)
    data = load_json(path)
    payload = core.manifest_signing_payload(data)
    data["signature"] = ed25519.sign(keys["seed"], payload)
    save_json(path, data)
    print(f"Подписано: {path} (ключ {keys['public'][:16]}...)")
    return 0


def cmd_verify(path, public_hex):
    data = load_json(path)
    signature = (data.get("signature") or "").strip()
    if not signature:
        print("В манифесте нет поля signature")
        return 1
    payload = core.manifest_signing_payload(data)
    ok = ed25519.verify(public_hex, payload, signature)
    print("Подпись верна" if ok else "ПОДПИСЬ НЕВЕРНА")
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Подпись/проверка update_info.json (Ed25519)")
    parser.add_argument("manifest", nargs="?", default=os.path.join(ROOT, "update_info.json"))
    parser.add_argument("--gen-keys", metavar="PATH", help="сгенерировать ключи в JSON")
    parser.add_argument("--key", metavar="PATH", help="JSON с ключами для подписи/проверки")
    parser.add_argument("--pub", metavar="HEX", help="публичный ключ (hex) для проверки")
    args = parser.parse_args(argv)

    if args.gen_keys:
        return cmd_gen_keys(args.gen_keys)
    if args.key and not args.pub:
        keys = load_json(args.key)
        args.pub = keys.get("public", "")
        if not args.pub:
            print("В файле ключей нет публичного ключа")
            return 1
        if "seed" in keys:
            return cmd_sign(args.manifest, args.key)
    if args.pub:
        return cmd_verify(args.manifest, args.pub)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
