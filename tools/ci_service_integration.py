"""H3: интеграционный тест службы (только вручную/CI, требует прав администратора).

Проверяет: установку службы zapret с general-стратегией, живой процесс winws,
корректное удаление службы и процессов. НЕ запускайте на рабочей машине — тест
реально ставит и снимает службу. В CI — только job workflow_dispatch.

Запуск: python tools/ci_service_integration.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import zapret_new_win as core  # noqa: E402


def main():
    if not core.is_admin():
        print("SKIP: нужны права администратора (CI windows-runner или elevated-консоль)")
        return 0
    zapret_dir = core.ensure_payload()
    bats = core.list_strategies(zapret_dir)
    if not bats:
        print("FAIL: пакет без стратегий (ensure_payload)")
        return 1
    bat = next((b for b in bats if b.lower().startswith("general")), bats[0])
    print(f"[1/4] Установка службы: {bat}")
    ok = core.install_zapret_service(zapret_dir, os.path.join(zapret_dir, bat))
    if not ok:
        print("FAIL: служба не установилась")
        core.stop_services_and_processes()
        return 1

    time.sleep(1)
    state = core.service_state("zapret")
    alive = state in ("RUNNING", "START_PENDING") or core.winws_process_running()
    print(f"[2/4] Состояние: {state} | winws: {core.winws_process_running()}")

    print("[3/4] Остановка и удаление")
    core.stop_services_and_processes()
    time.sleep(1.5)
    gone = core.service_state("zapret") == "NO_SERVICE" and not core.winws_process_running()
    print(f"[4/4] Удалено: {gone}")

    if alive and gone:
        print("PASS: интеграционный тест службы")
        return 0
    print("FAIL: служба или процесс остались в неожиданном состоянии")
    return 1


if __name__ == "__main__":
    sys.exit(main())
