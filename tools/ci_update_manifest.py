"""CI: обновляет update_info.json после сборки релиза.

Что делает:
- `download_url`/`hash` — на собранный exe (self-update portable/desktop-копий);
- если найден установщик (Setup.exe) — `installer_url`/`installer_sha256` на него
  (установленные версии обновляются через тихий Setup, download_url их не касается);
- при наличии MANIFEST_SIGNING_KEY (hex seed) — подписывает манифест Ed25519;
- если в zapret_new_win.py задан UPDATE_PUBKEY_HEX — сверяет, что подпись делается тем же ключом.

Запуск (CI):
    python tools/ci_update_manifest.py --exe dist/Zapret.exe --manifest update_info.json \
        --repo "$GITHUB_REPOSITORY" --tag "$GITHUB_REF_NAME"
"""
import argparse
import glob
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import ed25519  # noqa: E402
import zapret_new_win as core  # noqa: E402


def sha256_upper(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest().upper()


def main(argv=None):
    parser = argparse.ArgumentParser(description="CI: обновление манифеста после сборки")
    parser.add_argument("--exe", default=os.path.join("dist", "Zapret.exe"))
    parser.add_argument("--manifest", default="update_info.json")
    parser.add_argument("--repo", default="", help="owner/repo для ссылки на установщик")
    parser.add_argument("--tag", default="", help="тег релиза (например, v17.4)")
    parser.add_argument("--setup-glob", default=os.path.join("dist", "ZapretLauncher-*-setup.exe"))
    args = parser.parse_args(argv)

    exe_path = os.path.join(ROOT, args.exe) if not os.path.isabs(args.exe) else args.exe
    manifest_path = os.path.join(ROOT, args.manifest) if not os.path.isabs(args.manifest) else args.manifest
    if not os.path.exists(exe_path):
        print(f"Нет exe: {exe_path}")
        return 1

    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    data["hash"] = sha256_upper(exe_path)
    if args.repo and args.tag:
        data["download_url"] = (f"https://github.com/{args.repo}/releases/download/"
                                f"{args.tag}/{os.path.basename(exe_path)}")
    print("self-update exe:", data.get("download_url"), data["hash"][:16], "...")

    setups = sorted(glob.glob(os.path.join(ROOT, args.setup_glob) if not os.path.isabs(args.setup_glob) else args.setup_glob))
    if setups:
        setup = setups[-1]
        setup_sha = sha256_upper(setup)
        data["installer_sha256"] = setup_sha
        if args.repo and args.tag:
            data["installer_url"] = (f"https://github.com/{args.repo}/releases/download/"
                                     f"{args.tag}/{os.path.basename(setup)}")
        print("installer (installed updates):", data.get("installer_url"), setup_sha[:16], "...")
    else:
        print("Установщик не найден — installer_* не обновляется")

    seed = os.environ.get("MANIFEST_SIGNING_KEY", "").strip()
    if seed:
        pub = ed25519.publickey(seed)
        if core.UPDATE_PUBKEY_HEX and core.UPDATE_PUBKEY_HEX != pub:
            print(f"ОШИБКА: MANIFEST_SIGNING_KEY не совпадает с UPDATE_PUBKEY_HEX ({pub[:16]}... != {core.UPDATE_PUBKEY_HEX[:16]}...)")
            return 1
        payload = core.manifest_signing_payload(data)
        data["signature"] = ed25519.sign(seed, payload)
        print(f"Подписано (pub {pub[:16]}...)")
        if not core.UPDATE_PUBKEY_HEX:
            print(f"ВНИМАНИЕ: впишите в zapret_new_win.py UPDATE_PUBKEY_HEX = \"{pub}\"")
    else:
        data.pop("signature", None)
        print("MANIFEST_SIGNING_KEY не задан — манифест без подписи")

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Манифест обновлён:", manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
