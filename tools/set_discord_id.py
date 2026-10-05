"""G12: вшить Discord Application ID в zapret_new_win.py одной командой.

Автор проекта регистрирует приложение один раз и вшивает его ID — после этого
все пользователи получают статус в Discord без каких-либо настроек.

Как получить ID (один раз, ~1 минута):
  1) https://discord.com/developers/applications?new_application=true
  2) введите имя приложения (например, ZapretLauncher) → Create
  3) на странице General Information нажмите Copy рядом с APPLICATION ID

Использование:
  python tools/set_discord_id.py 123456789012345678   # вшить ID
  python tools/set_discord_id.py                      # показать текущий
  python tools/set_discord_id.py --clear              # убрать ID
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "zapret_new_win.py")
PATTERN = re.compile(r'^DISCORD_CLIENT_ID = "(\d*)"', re.MULTILINE)


def current_id():
    with open(MAIN, encoding="utf-8") as f:
        match = PATTERN.search(f.read())
    return match.group(1) if match else ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Вшить Discord Application ID")
    parser.add_argument("client_id", nargs="?", default=None, help="Application ID (17-20 цифр)")
    parser.add_argument("--clear", action="store_true", help="убрать ID")
    args = parser.parse_args(argv)

    if args.client_id is None and not args.clear:
        print("Текущий DISCORD_CLIENT_ID:", current_id() or "(не задан)")
        return 0

    new_id = "" if args.clear else str(args.client_id).strip()
    if new_id and not re.fullmatch(r"\d{17,20}", new_id):
        print("Ошибка: Application ID — это 17-20 цифр (скопируйте из Developer Portal)")
        return 1

    with open(MAIN, encoding="utf-8") as f:
        text = f.read()
    if not PATTERN.search(text):
        print("Не нашёл строку DISCORD_CLIENT_ID в zapret_new_win.py")
        return 1
    text = PATTERN.sub(f'DISCORD_CLIENT_ID = "{new_id}"', text, count=1)
    with open(MAIN, "w", encoding="utf-8") as f:
        f.write(text)
    print("DISCORD_CLIENT_ID обновлён:", new_id or "(очищен)")
    print("Дальше: пересобрать exe (Zapret.spec / ZapretWeb.spec) и закоммитить.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
