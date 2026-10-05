"""H8: генерирует golden-набор разбора стратегий текущего пакета.

Запуск: python tools/gen_golden.py
Результат: tests/golden/<FOLDER_NAME>.json  (bat -> разобранные аргументы)

При обновлении пакета Flowseal: сгенерировать новый файл и закоммитить
(старые наборы остаются как регрессия парсера по версиям).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import zapret_new_win as core  # noqa: E402

GOLDEN_DIR = os.path.join(ROOT, "tests", "golden")


def main():
    pkg = os.path.join(ROOT, "zapret_data", core.FOLDER_NAME)
    if not os.path.isdir(pkg):
        print(f"Пакет не найден: {pkg}")
        return 1
    golden = {}
    for bat in core.list_strategies(pkg):
        args = core.parse_strategy_bat(os.path.join(pkg, bat), pkg)
        if not args:
            print(f"Не разобрана стратегия: {bat}")
            return 1
        golden[bat] = args
    os.makedirs(GOLDEN_DIR, exist_ok=True)
    out = os.path.join(GOLDEN_DIR, f"{core.FOLDER_NAME}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(golden, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"OK: {len(golden)} стратегий -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
