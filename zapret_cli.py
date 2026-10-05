"""zapret-cli — консольное управление ZapretLauncher (общая логика в zapret_new_win.py).

Примеры:
    python zapret_cli.py status
    python zapret_cli.py list
    python zapret_cli.py probe --timeout 2
    python zapret_cli.py interfaces
    python zapret_cli.py start --bat "general (ALT).bat"   (нужен админ)
    python zapret_cli.py stop                              (нужен админ)
    python zapret_cli.py test                              (нужен админ)
"""
import argparse
import json
import os
import sys

import psutil

import zapret_new_win as core


def _current_strategy():
    try:
        with open(core.CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f).get("bat") or core.DEFAULT_BAT
    except Exception:
        return core.DEFAULT_BAT


def cmd_status(_args):
    zapret_dir = core.locate_zapret_dir()
    try:
        proxy_running = any((p.info.get("name") or "").lower() == core.TGWS_PROXY_EXE.lower()
                            for p in psutil.process_iter(["name"]))
    except Exception:
        proxy_running = False
    data = {
        "version": core.CURRENT_VERSION,
        "service": core.service_state("zapret"),
        "winws_process": core.winws_process_running(),
        "healthy": core.winws_health_ok(),
        "package_dir": zapret_dir,
        "package_complete": core.payload_complete(zapret_dir),
        "strategy": _current_strategy(),
        "proxy_running": proxy_running,
    }
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_list(_args):
    for name in core.list_strategies(core.locate_zapret_dir()):
        print(name)
    return 0


def cmd_probe(args):
    results = core.probe_services(timeout=args.timeout)
    for name, ms in results.items():
        print(f"{name}: {ms} ms" if ms >= 0 else f"{name}: FAIL")
    score = core.score_probe_results(results)
    print(f"score: {score:.0%}")
    return 0 if score > 0 else 1


def cmd_interfaces(_args):
    for name in core.list_active_interfaces():
        print(name)
    return 0


def _require_admin():
    if core.is_admin():
        return None
    print("Нужны права администратора (запустите из elevated-консоли).", file=sys.stderr)
    return 2


def cmd_start(args):
    denied = _require_admin()
    if denied is not None:
        return denied
    core.ensure_payload()
    zapret_dir = core.locate_zapret_dir()
    name = args.bat or _current_strategy()
    if name not in core.list_strategies(zapret_dir):
        print(f"Стратегия не найдена: {name}", file=sys.stderr)
        return 1
    bat_path = os.path.join(zapret_dir, name)
    ok = core.install_zapret_service(zapret_dir, bat_path) or core.launch_winws_direct(zapret_dir, bat_path)
    print(f"{'ON' if ok else 'ОШИБКА'}: {name}")
    return 0 if ok else 1


def cmd_stop(_args):
    denied = _require_admin()
    if denied is not None:
        return denied
    core.stop_services_and_processes()
    print("OFF")
    return 0


def cmd_test(_args):
    denied = _require_admin()
    if denied is not None:
        return denied
    best = core.run_strategy_tests(core.locate_zapret_dir(), on_line=print)
    if best:
        print(f"best: {best}")
        return 0
    print("Лучшая стратегия не определена", file=sys.stderr)
    return 1


def build_parser():
    parser = argparse.ArgumentParser(prog="zapret-cli", description="Управление ZapretLauncher из консоли")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="состояние службы и пакета (JSON)").set_defaults(func=cmd_status)
    sub.add_parser("list", help="список стратегий").set_defaults(func=cmd_list)
    probe = sub.add_parser("probe", help="пробы сервисов (YouTube/Discord/Telegram/Google)")
    probe.add_argument("--timeout", type=float, default=2.0)
    probe.set_defaults(func=cmd_probe)
    sub.add_parser("interfaces", help="активные сетевые интерфейсы").set_defaults(func=cmd_interfaces)
    start = sub.add_parser("start", help="включить обход (нужен админ)")
    start.add_argument("--bat", help="имя стратегии .bat")
    start.set_defaults(func=cmd_start)
    sub.add_parser("stop", help="выключить обход (нужен админ)").set_defaults(func=cmd_stop)
    sub.add_parser("test", help="PS-тесты стратегий (нужен админ)").set_defaults(func=cmd_test)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
