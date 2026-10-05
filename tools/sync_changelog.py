"""Синхронизация CHANGELOG.md -> CHANGELOG в zapret_new_win.py и changelog в update_info.json.

Запуск:
    python tools/sync_changelog.py            # обновить файлы
    python tools/sync_changelog.py --check    # проверить синхронность (0 — ок, 1 — расхождение)

Формат CHANGELOG.md:
    ## v17.4
    + добавлено
    * исправлено
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "zapret_new_win.py")
MANIFEST = os.path.join(ROOT, "update_info.json")
CHANGELOG_MD = os.path.join(ROOT, "CHANGELOG.md")

BEGIN_LINE = "# CHANGELOG:BEGIN (генерируется tools/sync_changelog.py из CHANGELOG.md — не править вручную)"
END_LINE = "# CHANGELOG:END"


def parse_md(text):
    versions = []
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        match = re.fullmatch(r"##\s+(v[\d.]+)", stripped)
        if match:
            current = (match.group(1), [])
            versions.append(current)
            continue
        if current is not None and re.match(r"^[+*-]\s+\S", stripped):
            current[1].append(stripped)
    return versions


def render_block(versions):
    lines = [BEGIN_LINE, "CHANGELOG = ["]
    for version, items in versions:
        lines.append(f'    ("{version}", [')
        for item in items:
            lines.append("        " + json.dumps(item, ensure_ascii=False) + ",")
        lines.append("    ]),")
    lines.append("]")
    lines.append(END_LINE)
    return "\n".join(lines)


def replace_block(source, block):
    pattern = re.compile(r"# CHANGELOG:BEGIN.*?# CHANGELOG:END", re.DOTALL)
    if not pattern.search(source):
        raise SystemExit("Маркеры CHANGELOG:BEGIN/END не найдены в zapret_new_win.py")
    return pattern.sub(lambda _match: block, source, count=1)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Синхронизация CHANGELOG.md")
    parser.add_argument("--check", action="store_true", help="только проверить, ничего не писать")
    args = parser.parse_args(argv)

    versions = parse_md(read_text(CHANGELOG_MD))
    if not versions:
        print("CHANGELOG.md не содержит ни одной секции '## vX.Y'")
        return 1

    block = render_block(versions)
    source = read_text(MAIN)
    new_source = replace_block(source, block)
    source_ok = new_source == source

    manifest_text = read_text(MANIFEST)
    manifest = json.loads(manifest_text)
    manifest_ok = manifest.get("changelog") == versions[0][1]
    new_manifest = dict(manifest)
    new_manifest["changelog"] = versions[0][1]
    new_manifest_text = json.dumps(new_manifest, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        if source_ok and manifest_ok:
            print("CHANGELOG.md, zapret_new_win.py и update_info.json синхронны")
            return 0
        if not source_ok:
            print("Расхождение: блок CHANGELOG в zapret_new_win.py не совпадает с CHANGELOG.md")
        if not manifest_ok:
            print("Расхождение: changelog в update_info.json не совпадает с последней версией CHANGELOG.md")
        print("Запустите: python tools/sync_changelog.py")
        return 1

    changed = []
    if not source_ok:
        with open(MAIN, "w", encoding="utf-8") as f:
            f.write(new_source)
        changed.append("zapret_new_win.py")
    if not manifest_ok or new_manifest_text != manifest_text:
        with open(MANIFEST, "w", encoding="utf-8") as f:
            f.write(new_manifest_text)
        changed.append("update_info.json")
    print("Обновлено: " + ", ".join(changed) if changed else "Ничего менять не нужно — всё синхронно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
