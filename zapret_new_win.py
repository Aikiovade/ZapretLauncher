# Сборка: python -m PyInstaller --noconfirm --onefile --windowed --uac-admin --name "Zapret" --icon "icon.ico" --add-data "zapret_data.zip;." --add-data "icon.ico;." zapret.py

import ctypes
import hashlib
import json
import math
import os
import queue
import random
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
import urllib.parse
import urllib.request
import winsound
import zipfile
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk
import keyboard
import psutil
import pystray
from PIL import Image, ImageDraw

import discord_rpc
import ed25519
import strategy_builder
import win_taskbar

# ======================================================================
# 1. КОНФИГУРАЦИЯ И ПУТИ
# ======================================================================
CURRENT_VERSION = "17.5"
UPDATE_VERSION_URL = "https://raw.githubusercontent.com/Aikiovade/ZapretLauncher/main/update_info.json"

# --- GLOBAL UI SETTINGS (Critical for fast start) ---
try:
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
except Exception: pass
# ----------------------------------------------------

DATA_ARCHIVE_NAME = "zapret_data.zip"
FOLDER_NAME = "zapret-discord-youtube-1.10.3"
DEFAULT_BAT = "general (ALT).bat"
CONFIG_FILE_NAME = "launcher_config.json"
LOG_FILE_NAME = "launcher_debug.txt"

TGWS_PROXY_EXE = "TgWsProxy_windows.exe"  # TgWsProxy — запускается из папки zapret
GAME_FILTER_FILE = "game_filter.enabled"
USER_LIST_FILES = (
    "list-general-user.txt",
    "list-exclude-user.txt",
    "ipset-exclude-user.txt",
    "ipset-all-user.txt",
)
UPDATE_ALLOWED_HOSTS = ("github.com", "objects.githubusercontent.com", "raw.githubusercontent.com")
UPDATE_REPO_PATH = "/Aikiovade/ZapretLauncher/"
DISCORD_CLIENT_ID = "1553946245704192142"  # G12: Client ID приложения Discord (пусто = presence выключен; см. HANDOFF)
DISCORD_REPO_URL = "https://github.com/Aikiovade/ZapretLauncher"
INSTALL_DIR_NAME = "ZapretLauncher"          # Program Files\ZapretLauncher (совпадает с .iss)
INSTALLED_EXE_NAME = "Zapret.exe"            # имя exe в установленной версии (для апдейтера-установщика)
RENDER_FRAME_MS = 33
RENDER_HIDDEN_MS = 250
RENDER_COMPACT_MS = 100
MAX_UPDATE_BYTES = 200 * 1024 * 1024
CONFIG_SCHEMA_VERSION = 2
SOUND_START_FILE = os.path.join("sounds", "start.wav")
SOUND_STOP_FILE = os.path.join("sounds", "stop.wav")

# CHANGELOG:BEGIN (генерируется tools/sync_changelog.py из CHANGELOG.md — не править вручную)
CHANGELOG = [
    ("v17.5", [
        "+ Windows-интеграция: оверлей статуса на иконке панели задач, кнопки на эскизе (Вкл/Выкл, Тесты, Стратегии), прогресс тестов и загрузки на иконке, вспышка при сбое",
        "+ Самовосстановление («Иммунитет»): лестница restart → пересоздание службы → перепаковка пакета → уведомление, журнал инцидентов, авто-ротация при деградации",
        "+ Конструктор стратегий: визуальная правка winws-параметров, проверка на пробах сервисов, сохранение/экспорт/импорт своих стратегий",
        "+ OSD-уведомление при включении/выключении обхода",
        "+ Новый звук действий (alert-03)",
        "+ Установщик: статичный баннер без анимации и звука, переработанная вёрстка, авто-закрытие финала через 5 секунд",
        "* Исправлено: перепаковка пакета выполняется после остановки службы (не падает на занятом winws.exe)",
        "* Исправлено: лимит размера проверяется для всех файлов при импорте стратегии (zip-бомба)",
        "* Исправлено: гонка самовосстановления (параллельный запуск лечения из watchdog и монитора)",
        "* Исправлено: статус после проверки конструктора восстанавливается по факту работы службы",
        "* Исправлено: кастомные стратегии со словом «service» в имени больше не скрываются из списка",
        "* Исправлено: флаги проверки/лечения не залипают при ошибках; тест блокируется при активных операциях",
        "* Валидация: запрещены кавычки в значениях параметров стратегий",
        "+ Инструмент визуальной проверки установщика (tools/installer_visual_test.py); тесты: 52 pytest, 103 smoke",
    ]),
    ("v17.4", [
        "+ Запрет обновлён до 1.10.3 (стратегия ALT13, обновлённые списки и утилиты)",
        "+ TgWsProxy обновлён до v1.10.4",
        "+ Новый web-интерфейс (WebView2): локализация RU/EN, мини-оверлей, сортировка стратегий по тестам",
        "+ Менеджер TgProxy: порт, секрет и ссылка для Telegram",
        "+ Поддержка кастомных портов GameFilter из utils/game_filter.enabled",
        "+ User-списки и TCP timestamps настраиваются как в оригинальном service.bat",
        "+ Авто-обновление пакета стратегий Flowseal из настроек",
        "+ Динамический выбор установленной версии пакета",
        "+ Редактор пользовательских списков (web UI)",
        "+ Пробы сервисов (YouTube/Discord/Telegram/Google) и индикатор SRV",
        "+ Авто-подбор лучшей стратегии по доступности сервисов",
        "+ Проверка хэша winws.exe (предупреждение о подмене)",
        "+ Профили сети: стратегия автоматически подбирается по SSID",
        "+ Диагностика сетевых интерфейсов",
        "+ Рабочий каталог перенесён в C:\\ZapretLauncher (старые данные мигрируют автоматически)",
        "+ Новые звуки включения/выключения",
        "+ Watchdog: SCM-проверка, повторные попытки, понятные уведомления",
        "+ CLI (zapret-cli) для управления из консоли",
        "+ Единый CHANGELOG.md как источник «Что нового»",
        "+ Portable-режим: флаг portable.txt рядом с exe — данные пишутся рядом, а не в C:\\ZapretLauncher",
        "+ Каналы обновлений stable/beta и кнопка «Откатиться» (резервная копия предыдущего exe)",
        "+ Авто-качество по железу (low/medium/high) и режим экономии батареи",
        "+ Светлая тема и настраиваемый хоткей включения/выключения",
        "+ Гейминг-режим: приоритет winws и пауза проб при полноэкранной игре",
        "+ Speedtest: замер доступности «до/после» с историей",
        "+ Авто-скрытие окна при простое",
        "+ Динамическая иконка трея, меню быстрых стратегий и Windows-уведомления",
        "+ Подпись манифеста обновлений (Ed25519) и зеркала загрузки",
        "+ Установщик (Inno Setup) и portable-zip сборка",
        "+ График пинга в спарклайне (CPU/RAM/PING)",
        "+ Режимы интерфейса Simple/Advanced/Expert (web)",
        "+ Dev-режим (--dev) с MockBackend — интерфейс без службы и прав администратора",
        "+ Теги и метаданные стратегий (<bat>.json), поиск по тегам",
        "+ Авто-ротация стратегии при деградации доступности",
        "+ Lite-сборка ZapretLite.exe без встроенного пакета (докачивается при первом старте)",
        "+ Локальные крашрепорты и их хвост в «Сообщить о проблеме»",
        "+ Мастер первого запуска и подсказки-тултипы",
        "+ pre-commit (ruff + smoke + синхронизация CHANGELOG)",
        "+ Discord Rich Presence: стратегия, состояние, аптайм и кнопка установки (по умолчанию выключено)",
        "+ Обновление установленной версии через Setup.exe (SSL + sha256 + Ed25519-подпись); portable — self-update",
        "+ Данные перенесены в %ProgramData%\\ZapretLauncher (DACL Administrators/Users, автомиграция)",
        "+ Анимация запуска приложения (кольца + логотип; пропуск кликом; отключается в настройках)",
        "+ Живой фон web-UI: частицы по настройке «Эффекты» (плотность зависит от качества)",
        "+ Пульсация главного круга при включённом обходе",
        "+ Установщик: тёмный стиль, брендинг мастера, страница «Что внутри», выбор WebView2/Tk",
        "+ Discord: Client ID вшивается в сборку (tools/set_discord_id.py) — пользователю вводить ничего не нужно; статус подключения под тумблером",
        "+ Анимация запуска прокачана: вращающиеся дуги, частицы, glow (2.4 с, пропуск кликом)",
        "+ Установщик «вау»: фоновая графика мастера, звуковое сопровождение, брендинг приветствия и финала",
        "* Апдейтер: обязательные SSL и проверка хэша, без bat и TEMP-подмены",
        "* Безопасность: убраны shell-запуски и SeDebugPrivilege, файлы больше не скрываются",
        "* Производительность: пауза рендера в трее, 30 FPS, кэш цветов",
        "* Автозапуск сохраняется в настройках и отключается по-настоящему",
        "* Единое ядро тестов стратегий; конфиг не теряет настройки между Tk и web",
        "* Запоминается последнее состояние обхода (ON/OFF)",
        "* Исправлено: восстановление повреждённого рабочего пакета (стратегии и TgProxy больше не пропадают)",
        "* Исправлены: кнопка «Экспорт», счётчик аптайма, гонка распаковки архива",
    ]),
    ("v17.3", [
        "+ Кнопка отключения уведомлений (только на главном экране)",
        "+ Исправлен автозапуск — теперь через ярлык (работает при переносе .exe)",
        "+ Версия 17.3",
    ]),
    ("v17.2", [
        "* Фикс: Устранена проблема с падением программы каждые 3-5 секунд",
        "* Фикс: Watchdog теперь запускает службу в отдельном потоке",
        "* Фикс: Оптимизирован счётчик аптайма",
    ]),
    ("v17.1", [
        "* Фикс: все профили теперь корректно отображаются в списке",
        "* Фикс: TgWsProxy теперь корректно запускается (поиск в bin/)",
        "* Фикс taskkill — убирает прокси без лишних кавычек",
    ]),
    ("v17.0", [
        "+ TgWsProxy — кнопка запуска/остановки прокси для Telegram",
        "+ Watchdog с авто-рестартом — служба упала и сама поднялась",
        "+ Пинг в HUD (CPU / RAM / PING обновляются в реальном времени)",
        "+ Детектор обхода — проверяет discord.com и показывает ✓/✗",
        "+ Быстрая смена стратегии без стоп/старт — hot-switch на лету",
        "+ Статистика: суммарный аптайм и кол-во запусков",
        "+ Экспорт и импорт конфига одной кнопкой",
        "+ Мини-оверлей (compact mode) — окно 220×50 поверх всех",
        "+ Стратегия и аптайм в tooltip системного трея",
        "+ Имя активной стратегии под кнопкой START / таймером",
        "+ Обновление запрета до версии 1.10.0",
        "- Убраны музыкальные кнопки (Русский / Американец)",
        "* Фикс кодировки .bat файлов (utf-8 + cp1251 fallback)",
        "* Фикс SSL: нормальная проверка → fallback без проверки",
    ]),
    ("v16.7", [
        "+ Новые стратегии: FAKE TLS AUTO, SIMPLE FAKE и др.",
        "+ Поддержка тем оформления",
        "+ Мультиязычность (RU / EN)",
        "+ Автозапуск через реестр",
        "+ Системное тестирование стратегий",
        "+ Иконка в трее",
    ]),
    ("v16.0", [
        "+ Первая публичная версия ZapretLauncher",
        "+ Запуск обхода через Windows Service",
        "+ Пользовательский интерфейс на tkinter Canvas",
        "+ Анимация и HUD",
    ]),
]
# CHANGELOG:END

TARGET_PROCESSES = ["winws.exe"]      
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 800

# --- ОПРЕДЕЛЕНИЕ ПУТЕЙ ---
if getattr(sys, 'frozen', False):
    EXE_DIR = os.path.dirname(sys.executable)
else:
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))

PORTABLE_FLAG_FILE = "portable.txt"
PORTABLE_DATA_DIR = "ZapretLauncher_data"


def _portable_requested():
    """Portable-режим: файл portable.txt рядом с exe или аргумент --portable."""
    try:
        if "--portable" in sys.argv:
            return True
        return os.path.exists(os.path.join(EXE_DIR, PORTABLE_FLAG_FILE))
    except Exception:
        return False


def _portable_dir():
    return os.path.join(EXE_DIR, PORTABLE_DATA_DIR)


def _programdata_dir():
    """E2: общий каталог данных для установленной версии (%ProgramData%\\ZapretLauncher)."""
    base = os.environ.get('ProgramData') or os.path.join(os.environ.get('SystemDrive', 'C:') + os.sep, 'ProgramData')
    return os.path.join(base, INSTALL_DIR_NAME)


def _dir_writable(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, '.write_probe')
        with open(probe, 'w') as f:
            f.write('ok')
        os.remove(probe)
        return True
    except Exception:
        return False


def _pick_data_dir():
    r"""Рабочий каталог: ZAPRET_DATA_DIR (тесты) → portable → %ProgramData% → C:\ZapretLauncher → %LOCALAPPDATA%."""
    legacy = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ZapretLauncher')
    env_dir = (os.environ.get('ZAPRET_DATA_DIR') or '').strip()
    if env_dir and _dir_writable(env_dir):
        return env_dir, legacy
    if _portable_requested():
        portable = _portable_dir()
        if _dir_writable(portable):
            return portable, legacy
    programdata = _programdata_dir()
    if _dir_writable(programdata):
        return programdata, legacy
    system_drive = os.environ.get('SystemDrive', 'C:')
    preferred = os.path.join(system_drive + os.sep, 'ZapretLauncher')
    if _dir_writable(preferred):
        return preferred, legacy
    return legacy, preferred


def _legacy_data_roots():
    """E2: старые каталоги данных (кроме активного) — для миграции и очистки."""
    system_drive = os.environ.get('SystemDrive', 'C:')
    roots = [
        os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ZapretLauncher'),
        os.path.join(system_drive + os.sep, 'ZapretLauncher'),
    ]
    result = []
    for root in roots:
        try:
            if os.path.realpath(root) != os.path.realpath(APP_DATA_DIR):
                result.append(root)
        except Exception:
            continue
    return result


def is_portable_mode():
    """Активен ли portable-режим (данные лежат рядом с exe)."""
    try:
        return os.path.realpath(APP_DATA_DIR).startswith(os.path.realpath(EXE_DIR) + os.sep)
    except Exception:
        return False


def data_dir_mode():
    """Где лежат данные: 'portable' | 'programdata' | 'legacy'."""
    try:
        if is_portable_mode():
            return "portable"
        if os.path.realpath(APP_DATA_DIR) == os.path.realpath(_programdata_dir()):
            return "programdata"
    except Exception:
        pass
    return "legacy"


APP_DATA_DIR, LEGACY_DATA_DIR = _pick_data_dir()


def payload_complete(zapret_dir):
    """Полный ли пакет: движок winws + стратегии .bat + TgWsProxy + папка lists."""
    try:
        if not zapret_dir or not os.path.isdir(zapret_dir):
            return False
        if not os.path.exists(os.path.join(zapret_dir, "bin", "winws.exe")):
            return False
        if not os.path.exists(os.path.join(zapret_dir, TGWS_PROXY_EXE)):
            return False
        if not os.path.isdir(os.path.join(zapret_dir, "lists")):
            return False
        return any(f.endswith(".bat") and "service" not in f.lower()
                   for f in os.listdir(zapret_dir))
    except Exception:
        return False


def _find_installed_package_roots():
    """Все папки zapret-discord-youtube* с winws.exe (новый и старый каталоги)."""
    roots = []
    bases = [APP_DATA_DIR, LEGACY_DATA_DIR]
    for legacy in _legacy_data_roots():
        if legacy not in bases:
            bases.append(legacy)
    for base in bases:
        for sub in ("", "zapret_data"):
            folder = os.path.join(base, sub)
            try:
                for item in os.listdir(folder):
                    if item.startswith("zapret-discord-youtube"):
                        full = os.path.join(folder, item)
                        if os.path.exists(os.path.join(full, "bin", "winws.exe")):
                            roots.append(full)
            except Exception:
                continue
    return roots


def _package_version_key(path):
    match = re.search(r'(\d+(?:\.\d+)*)', os.path.basename(path))
    return tuple(int(x) for x in match.group(1).split('.')) if match else (0,)


def locate_zapret_dir():
    candidates = [
        os.path.join(APP_DATA_DIR, "zapret_data", FOLDER_NAME),
        os.path.join(APP_DATA_DIR, FOLDER_NAME),
        os.path.join(EXE_DIR, "zapret_data", FOLDER_NAME),
        os.path.join(EXE_DIR, FOLDER_NAME),
    ]
    for c in candidates:
        if payload_complete(c):
            return c

    installed = _find_installed_package_roots()
    if installed:
        complete = [p for p in installed if payload_complete(p)]
        return max(complete or installed, key=_package_version_key)

    for c in (os.path.join(APP_DATA_DIR, "zapret_data"), APP_DATA_DIR):
        if payload_complete(c):
            return c
    return candidates[0]


_payload_lock = threading.Lock()


def ensure_payload():
    """Гарантирует полный пакет в рабочем каталоге: при неполном/старом — распаковка bundled zip."""
    with _payload_lock:
        current = locate_zapret_dir()
        if payload_complete(current) and _package_version_key(current) >= _package_version_key(FOLDER_NAME):
            return current
        try:
            zip_path = resource_path(DATA_ARCHIVE_NAME)
            if not os.path.exists(zip_path):
                log_error(f"Архив не найден: {zip_path}; пробую скачать пакет Flowseal (lite-сборка)")
                ok, message = update_zapret_data()
                if ok:
                    log_error(f"Пакет загружен: {message}")
                    return locate_zapret_dir()
                log_error(f"update_zapret_data: {message}")
                return current
            ensure_app_data()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                _safe_extractall(zip_ref, APP_DATA_DIR)
            target = os.path.join(APP_DATA_DIR, FOLDER_NAME)
            if os.path.isdir(current) and os.path.realpath(current) != os.path.realpath(target):
                moved = _migrate_user_data(current, target)
                if moved:
                    log_error(f"Перенесено пользовательских файлов: {moved}")
            return locate_zapret_dir()
        except Exception as e:
            log_error(f"ensure_payload error: {e}")
            return current


def repack_payload():
    """17.5: принудительная перераспаковка дата-архива (шаг «repack» самовосстановления)."""
    with _payload_lock:
        try:
            zip_path = resource_path(DATA_ARCHIVE_NAME)
            if not os.path.exists(zip_path):
                ok, message = update_zapret_data()
                return bool(ok), message
            ensure_app_data()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                _safe_extractall(zip_ref, APP_DATA_DIR)
            complete = payload_complete(os.path.join(APP_DATA_DIR, FOLDER_NAME))
            log_event("repack_payload", complete=complete)
            return complete, "repacked"
        except Exception as e:
            log_error(f"repack_payload error: {e}")
            return False, str(e)


ZAPRET_DIR = locate_zapret_dir()

CONFIG_PATH = os.path.join(APP_DATA_DIR, CONFIG_FILE_NAME)
LOG_PATH = os.path.join(APP_DATA_DIR, LOG_FILE_NAME)


def current_exe_path():
    """Путь к запущенному .exe (или скрипту в dev-режиме)."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def cleanup_stale_update_files():
    """Хвост апдейтера рядом с exe: .new от прерванной загрузки — убираем при старте."""
    try:
        for suffix in (".new",):
            path = current_exe_path() + suffix
            if os.path.exists(path):
                try:
                    os.remove(path)
                    log_event("update_leftover_removed", file=os.path.basename(path))
                except Exception:
                    pass
    except Exception:
        pass

# ----------------------------------

# Цветовые темы
THEMES_DATA = {
    "Cyber Green": "#00ff88",
    "Neon Blue": "#00f2ff",
    "Plasma Red": "#ff2a2a",
    "Solar Orange": "#ff9900",
    "Void Purple": "#aa00ff",
    "White": "#ffffff"
}
DEFAULT_THEME = "Cyber Green"

STRATEGY_LIST = ["general (ALT).bat", "general.bat"]  # Используется только как fallback до загрузки папки

# Словари переводов (БЕЗ ЧАТА И ИИ)
TRANSLATIONS_DATA = {
    "RU": {
        "main_title": "ОБХОД",
        "lang_name": "Я РУССКИЙ",
        "settings_title": "НАСТРОЙКИ",
        "active_strategy": "АКТИВНАЯ СТРАТЕГИЯ",
        "snow_fx": "Снег",
        "minimal_mode": "Минимализм",
        "auto_run": "Автозапуск",
        "logs": "Логи",
        "start_min": "Тихий старт",
        "theme": "Тема",
        "status_ready": "ГОТОВ",
        "status_on": "ВКЛ",
        "status_busy": "ЖДИТЕ...",
        "status_error": "ОШИБКА",
        "status_no_file": "НЕТ ФАЙЛА",
        "status_installing": "УСТАНОВКА...",
        "btn_start": "НАЧАТЬ",
        "btn_active": "АКТИВЕН",
        "update_check": "ПРОВЕРКА...",
        "update_found": "ЕСТЬ ОБНОВЛЕНИЕ",
        "update_downloading": "ЗАГРУЗКА...",
        "update_failed": "ОШИБКА ОБНОВЛЕНИЯ",
        "update_hash_fail": "ОШИБКА ХЕША",
        "update_latest": "ПОСЛЕДНЯЯ ВЕРСИЯ",
        "btn_tests": "ЗАПУСК ТЕСТОВ",
        "lang_label": "Язык",
        "notifications": "Уведомления",
        "auto_restart_lbl": "Авто-рестарт",
        "custom_color": "Свой цвет:",
        "app_sub": "DPI bypass launcher",
        "gear_title": "Настройки",
        "spark_title": "CPU (зелёный) и RAM (синий) за последнюю минуту",
        "btn_strategy": "Стратегия",
        "btn_stop_action": "СТОП",
        "btn_update_install": "Установить обновление",
        "btn_lists": "Списки",
        "btn_autotest": "Авто-подбор",
        "btn_probe": "Проверить",
        "net_profile": "Профиль сети",
        "btn_changelog": "Что нового",
        "btn_quit": "Выход",
        "btn_export": "Экспорт",
        "btn_import": "Импорт",
        "btn_update_check": "Обновление",
        "btn_pkg": "Пакет Flowseal",
        "btn_save": "Сохранить",
        "btn_close": "Закрыть",
        "lists_title": "Пользовательские списки",
        "search_ph": "Поиск по {n} стратегиям...",
        "changelog_hint": "что нового?",
        "status_fail": "СБОЙ",
        "first_run_toast": "Первый запуск: выбери стратегию или нажми «Авто-подбор» в настройках",
        "confirm_autotest": "Перебрать все стратегии и выбрать лучшую по доступности сервисов? Обход будет временно перезапускаться.",
        "autotest_fail": "Не удалось запустить авто-подбор",
        "autotest_line": "Авто-подбор {i}/{t} — {s}",
        "testing_line": "Тестирование {p}/{t} — {line}",
        "ms_suffix": " мс",
        "pkg_latest": "Установлена последняя версия пакета стратегий",
        "pkg_check_fail": "Не удалось проверить релизы Flowseal",
        "pkg_install_q": "Установить пакет стратегий {tag}?",
        "pkg_installed": "Установлено: {msg}",
        "pkg_error": "Ошибка: {msg}",
        "net_remember_q": "Запомнить стратегию «{s}» для сети «{n}»?",
        "net_saved": "Сохранено для сети: {n}",
        "net_fail": "Не удалось сохранить",
        "saved_ok": "Сохранено",
        "save_fail": "Ошибка сохранения",
        "update_apply_fail": "Не удалось выполнить обновление",
        "btn_compact": "Мини-оверлей",
        "sort_az": "A-Z",
        "sort_score": "По тестам",
        "proxy_status": "Статус",
        "proxy_port": "Порт",
        "proxy_secret": "Секрет",
        "proxy_link_lbl": "Ссылка для Telegram",
        "btn_copy": "Копировать",
        "btn_start_stop": "Старт/Стоп",
        "proxy_bad_port": "Неверный порт",
        "proxy_bad_secret": "Неверный секрет (hex 16-64)",
        "proxy_restarted": "перезапущен",
        "copied": "Скопировано",
        "btn_report": "Сообщить о проблеме",
        "btn_import_bat": "Импорт .bat",
        "imported_ok": "Импортировано: {name}",
        "import_fail": "Не удалось импортировать",
        "update_channel_lbl": "Канал обновлений",
        "btn_rollback": "Откатиться",
        "confirm_rollback": "Вернуться к предыдущей версии? Приложение перезапустится.",
        "rollback_fail": "Не удалось откатиться",
        "notify_on": "Обход включён",
        "notify_off": "Обход выключен",
        "quality_lbl": "Качество",
        "quality_auto": "Авто",
        "quality_low": "Низкое",
        "quality_medium": "Среднее",
        "quality_high": "Высокое",
        "battery_lbl": "Режим батареи",
        "idle_lbl": "Скрывать при простое (мин)",
        "light_lbl": "Светлая тема",
        "hotkey_lbl": "Хоткей вкл/выкл",
        "gaming_lbl": "Гейминг-режим",
        "btn_speedtest": "Speedtest",
        "speedtest_title": "Доступность и задержки",
        "speedtest_none": "Нет данных",
        "mode_lbl": "Режим интерфейса",
        "mode_simple": "Простой",
        "mode_advanced": "Обычный",
        "mode_expert": "Эксперт",
        "auto_rotate_lbl": "Авто-ротация при деградации",
        "rotate_notify": "Стратегия переключена: {name}",
        "tip_toggle": "Включить/выключить обход (хоткей)",
        "tip_update": "Проверить обновления",
        "tip_strategy": "Выбрать стратегию",
        "wiz_title": "Первый запуск",
        "wiz_s1": "Добро пожаловать! Этот лаунчер включает обход блокировок (YouTube, Discord) и ускоряет Telegram.",
        "wiz_s2": "Выберите стратегию: можно запустить авто-подбор (перебор всех стратегий) или выбрать вручную.",
        "wiz_s3": "Готово! Нажмите большую кнопку на главном экране, чтобы включить обход.",
        "wiz_next": "Далее",
        "wiz_open_strategies": "Выбрать вручную",
        "discord_rpc_lbl": "Discord статус",
        "intro_lbl": "Анимация запуска",
        "discord_id_needed": "Укажите Client ID (нажмите)",
        "discord_wait": "Ожидание Discord…",
        "discord_ok": "Подключено к Discord",
        "discord_lib_missing": "pypresence не установлен",
        "discord_client_id_title": "Discord Client ID",
        "discord_client_id_hint": "Создайте приложение на discord.com/developers/applications и вставьте Application ID (17-20 цифр)",
        "more_settings": "Ещё…",
        "more_title": "Дополнительно",
        "taskbar_lbl": "Панель задач",
        "osd_lbl": "OSD при переключении",
        "self_heal_lbl": "Самовосстановление",
        "inc_title": "Журнал инцидентов",
        "inc_open": "Журнал инцидентов",
        "inc_copy": "Копировать",
        "inc_refresh": "Обновить",
        "inc_empty": "Инцидентов пока не было",
        "builder_open": "Конструктор стратегий",
        "sb_base": "База:",
        "sb_load": "Загрузить",
        "sb_global": "Общие фильтры",
        "sb_profile": "Профиль",
        "sb_add": "Добавить",
        "sb_save": "Сохранить стратегию",
        "sb_name": "Имя:",
        "sb_test": "Проверить",
        "sb_testing": "Проверка… (обход временно выключен)",
        "sb_score": "Результат: {score}",
        "sb_export": "Экспорт",
        "sb_import": "Импорт",
        "sb_test_warn": "Обход будет временно выключен на время проверки. Продолжить?",
        "sb_saved": "Сохранено: {name}",
        "sb_error": "Ошибка: {error}",
        "sb_restored": "обход восстановлен",
        "sb_overwrite": "Стратегия «{name}» уже есть. Перезаписать?",
        "sb_no_custom": "нет своих стратегий",
        "sb_exported": "Экспортировано: {name}",
        "sb_busy": "Сейчас занято — дождитесь завершения операции",
        "osd_on": "Обход включён",
        "osd_off": "Обход выключен",
        "heal_fixed": "Проблема устранена автоматически",
        "heal_help": "Не удалось восстановить обход — нужна помощь",
        "tb_toggle": "Вкл/Выкл",
        "tb_tests": "Тесты",
        "tb_strategies": "Стратегии"
    },
    "EN": {
        "main_title": "ZAPRET",
        "lang_name": "inasranets",
        "settings_title": "SETTINGS",
        "active_strategy": "ACTIVE STRATEGY",
        "snow_fx": "Snow FX",
        "minimal_mode": "Minimal",
        "auto_run": "Auto-Run",
        "logs": "Logs",
        "start_min": "Start Min",
        "theme": "Theme",
        "status_ready": "READY",
        "status_on": "ON",
        "status_busy": "WAIT...",
        "status_error": "ERROR",
        "status_no_file": "NO FILE",
        "status_installing": "INSTALLING...",
        "btn_start": "START",
        "btn_active": "ACTIVE",
        "update_check": "CHECKING...",
        "update_found": "UPDATE AVAILABLE",
        "update_downloading": "DOWNLOADING...",
        "update_failed": "UPDATE FAILED",
        "update_hash_fail": "HASH MISMATCH",
        "update_latest": "LATEST VERSION",
        "btn_tests": "RUN TESTS",
        "lang_label": "Language",
        "notifications": "Notifications",
        "auto_restart_lbl": "Auto-Restart",
        "custom_color": "Custom color:",
        "app_sub": "DPI bypass launcher",
        "gear_title": "Settings",
        "spark_title": "CPU (green) and RAM (blue) over the last minute",
        "btn_strategy": "Strategy",
        "btn_stop_action": "STOP",
        "btn_update_install": "Install update",
        "btn_lists": "Lists",
        "btn_autotest": "Auto-pick",
        "btn_probe": "Check",
        "net_profile": "Network profile",
        "btn_changelog": "What's new",
        "btn_quit": "Exit",
        "btn_export": "Export",
        "btn_import": "Import",
        "btn_update_check": "Update",
        "btn_pkg": "Flowseal package",
        "btn_save": "Save",
        "btn_close": "Close",
        "lists_title": "User lists",
        "search_ph": "Search {n} strategies...",
        "changelog_hint": "what's new?",
        "status_fail": "FAILED",
        "first_run_toast": "First run: pick a strategy or use Auto-pick in settings",
        "confirm_autotest": "Test all strategies and pick the best by service availability? Bypass will restart temporarily.",
        "autotest_fail": "Failed to start auto-pick",
        "autotest_line": "Auto-pick {i}/{t} — {s}",
        "testing_line": "Testing {p}/{t} — {line}",
        "ms_suffix": " ms",
        "pkg_latest": "The strategy package is up to date",
        "pkg_check_fail": "Failed to check Flowseal releases",
        "pkg_install_q": "Install strategy package {tag}?",
        "pkg_installed": "Installed: {msg}",
        "pkg_error": "Error: {msg}",
        "net_remember_q": "Remember strategy \"{s}\" for network \"{n}\"?",
        "net_saved": "Saved for network: {n}",
        "net_fail": "Failed to save",
        "saved_ok": "Saved",
        "save_fail": "Save failed",
        "update_apply_fail": "Update failed",
        "btn_compact": "Mini overlay",
        "sort_az": "A-Z",
        "sort_score": "By score",
        "proxy_status": "Status",
        "proxy_port": "Port",
        "proxy_secret": "Secret",
        "proxy_link_lbl": "Telegram link",
        "btn_copy": "Copy",
        "btn_start_stop": "Start/Stop",
        "proxy_bad_port": "Invalid port",
        "proxy_bad_secret": "Invalid secret (hex 16-64)",
        "proxy_restarted": "restarted",
        "copied": "Copied",
        "btn_report": "Report a problem",
        "btn_import_bat": "Import .bat",
        "imported_ok": "Imported: {name}",
        "import_fail": "Import failed",
        "update_channel_lbl": "Update channel",
        "btn_rollback": "Roll back",
        "confirm_rollback": "Roll back to the previous version? The app will restart.",
        "rollback_fail": "Rollback failed",
        "notify_on": "Bypass is ON",
        "notify_off": "Bypass is OFF",
        "quality_lbl": "Quality",
        "quality_auto": "Auto",
        "quality_low": "Low",
        "quality_medium": "Medium",
        "quality_high": "High",
        "battery_lbl": "Battery saver",
        "idle_lbl": "Hide when idle (min)",
        "light_lbl": "Light theme",
        "hotkey_lbl": "Toggle hotkey",
        "gaming_lbl": "Gaming mode",
        "btn_speedtest": "Speedtest",
        "speedtest_title": "Availability and latency",
        "speedtest_none": "No data",
        "mode_lbl": "UI mode",
        "mode_simple": "Simple",
        "mode_advanced": "Advanced",
        "mode_expert": "Expert",
        "auto_rotate_lbl": "Auto-rotate on degradation",
        "rotate_notify": "Strategy switched: {name}",
        "tip_toggle": "Toggle bypass (hotkey)",
        "tip_update": "Check for updates",
        "tip_strategy": "Choose a strategy",
        "wiz_title": "First launch",
        "wiz_s1": "Welcome! This launcher enables DPI bypass (YouTube, Discord) and speeds up Telegram.",
        "wiz_s2": "Pick a strategy: run Auto-pick (tests every strategy) or choose manually.",
        "wiz_s3": "Done! Press the big button on the main screen to enable bypass.",
        "wiz_next": "Next",
        "wiz_open_strategies": "Choose manually",
        "discord_rpc_lbl": "Discord status",
        "intro_lbl": "Startup animation",
        "discord_id_needed": "Set Client ID (click)",
        "discord_wait": "Waiting for Discord…",
        "discord_ok": "Connected to Discord",
        "discord_lib_missing": "pypresence is not installed",
        "discord_client_id_title": "Discord Client ID",
        "discord_client_id_hint": "Create an app at discord.com/developers/applications and paste its Application ID (17-20 digits)",
        "more_settings": "More…",
        "more_title": "Advanced",
        "taskbar_lbl": "Taskbar",
        "osd_lbl": "Toggle OSD",
        "self_heal_lbl": "Self-healing",
        "inc_title": "Incident log",
        "inc_open": "Incident log",
        "inc_copy": "Copy",
        "inc_refresh": "Refresh",
        "inc_empty": "No incidents yet",
        "builder_open": "Strategy builder",
        "sb_base": "Base:",
        "sb_load": "Load",
        "sb_global": "Global filters",
        "sb_profile": "Profile",
        "sb_add": "Add",
        "sb_save": "Save strategy",
        "sb_name": "Name:",
        "sb_test": "Test",
        "sb_testing": "Testing… (bypass temporarily off)",
        "sb_score": "Score: {score}",
        "sb_export": "Export",
        "sb_import": "Import",
        "sb_test_warn": "Bypass will be temporarily disabled during the test. Continue?",
        "sb_saved": "Saved: {name}",
        "sb_error": "Error: {error}",
        "sb_restored": "bypass restored",
        "sb_overwrite": "Strategy “{name}” already exists. Overwrite?",
        "sb_no_custom": "no custom strategies",
        "sb_exported": "Exported: {name}",
        "sb_busy": "Busy — wait for the current operation to finish",
        "osd_on": "Bypass ON",
        "osd_off": "Bypass OFF",
        "heal_fixed": "Issue fixed automatically",
        "heal_help": "Could not restore bypass — help needed",
        "tb_toggle": "Toggle",
        "tb_tests": "Tests",
        "tb_strategies": "Strategies"
    }
}

# ======================================================================
# 2. СИСТЕМНЫЕ ФУНКЦИИ
# ======================================================================

def _legacy_zapret_dirs():
    """Папки старых версий пакета zapret во всех каталогах данных (активный + legacy)."""
    roots = [APP_DATA_DIR, os.path.join(APP_DATA_DIR, "zapret_data")]
    for legacy in _legacy_data_roots():
        roots.extend([legacy, os.path.join(legacy, "zapret_data")])
    for root in roots:
        try:
            for item in os.listdir(root):
                path = os.path.join(root, item)
                if os.path.isdir(path) and item.startswith("zapret-discord-youtube") and item != FOLDER_NAME:
                    yield path
        except Exception:
            continue


def _migrate_user_data(old_dir, new_dir):
    """Переносит пользовательские файлы из старой папки версии в текущую."""
    ok = 0
    try:
        candidates = [os.path.join("lists", name) for name in USER_LIST_FILES]
        candidates.append(os.path.join("utils", GAME_FILTER_FILE))
        for rel in candidates:
            src_path = os.path.join(old_dir, rel)
            dst_path = os.path.join(new_dir, rel)
            if not os.path.exists(src_path) or os.path.exists(dst_path):
                continue
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)
            ok += 1
        try:
            src_ipset = os.path.join(old_dir, "lists", "ipset-all.txt")
            dst_ipset = os.path.join(new_dir, "lists", "ipset-all.txt")
            if os.path.exists(src_ipset) and os.path.getsize(src_ipset) > os.path.getsize(dst_ipset) + 200:
                shutil.copy2(src_ipset, dst_ipset)
                ok += 1
        except Exception:
            pass
    except Exception as e:
        log_error(f"User data migration error: {e}")
    return ok


def cleanup_old_zapret_folders():
    try:
        ensure_app_data()
        keep_dir = os.path.realpath(locate_zapret_dir()).lower()
        if not payload_complete(keep_dir):
            log_error("Пропущена очистка старых папок: активный пакет неполный")
            return
        running_exe = os.path.realpath(current_exe_path()).lower()
        for item_path in list(_legacy_zapret_dirs()):
            try:
                folder_real = os.path.realpath(item_path).lower()
                if folder_real == keep_dir:
                    continue
                if running_exe.startswith(folder_real + os.sep):
                    log_error(f"Пропущена очистка {os.path.basename(item_path)}: из неё запущен текущий exe")
                    continue
                ctypes.windll.kernel32.SetFileAttributesW(item_path, 128)
                if os.path.isdir(keep_dir):
                    moved = _migrate_user_data(item_path, keep_dir)
                    if moved:
                        log_error(f"Перенесено пользовательских файлов: {moved} из {os.path.basename(item_path)}")
                shutil.rmtree(item_path, ignore_errors=True)
                log_error(f"Удалена старая папка версии: {os.path.basename(item_path)}")
            except Exception as e:
                log_error(f"Не удалось удалить старую папку {item_path}: {e}")
    except Exception as e:
        log_error(f"Ошибка при очистке старых папок: {e}")



def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception: return False

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def ensure_app_data():
    try:
        if not os.path.exists(APP_DATA_DIR):
            os.makedirs(APP_DATA_DIR)
    except Exception: pass


def ensure_data_dir_acl(path=None):
    """E2: DACL на каталог данных — Administrators: Full, Users: Read (icacls, best-effort)."""
    try:
        target = path or APP_DATA_DIR
        if not os.path.isdir(target):
            os.makedirs(target, exist_ok=True)
        if not is_admin():
            return False
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        res = subprocess.call(
            ["icacls", target,
             "/grant", "*S-1-5-32-544:(OI)(CI)F",   # Administrators: Full
             "/grant", "*S-1-5-32-545:(OI)(CI)R",   # Users: Read
             "/T", "/C", "/Q"],
            startupinfo=si, creationflags=0x08000000)
        return res == 0
    except Exception as e:
        log_error(f"ensure_data_dir_acl error: {e}")
        return False

LOG_MAX_BYTES = 2 * 1024 * 1024
EVENTS_PATH = os.path.join(APP_DATA_DIR, "events.jsonl")


def _rotate_log_file(path, max_bytes=LOG_MAX_BYTES, keep=1):
    """Ротация по размеру: path -> path.1 (при переполнении). Возвращает True, если ротировали."""
    try:
        if not os.path.exists(path) or os.path.getsize(path) < max_bytes:
            return False
        for idx in range(keep, 0, -1):
            src = path if idx == 1 else f"{path}.{idx - 1}"
            dst = f"{path}.{idx}"
            if os.path.exists(dst):
                os.remove(dst)
            if os.path.exists(src):
                os.replace(src, dst)
        return True
    except Exception:
        return False


def log_error(msg):
    try:
        ensure_app_data()
        _rotate_log_file(LOG_PATH)
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception: pass


def log_event(name, **fields):
    """Структурированное событие (JSON Lines) для диагностики: events.jsonl с ротацией."""
    try:
        ensure_app_data()
        _rotate_log_file(EVENTS_PATH)
        record = {"ts": time.strftime('%Y-%m-%d %H:%M:%S'), "event": name}
        record.update(fields)
        with open(EVENTS_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception: pass


# ---------------------------------------------------------------
# 17.5 «Иммунитет»: лестница самовосстановления и журнал инцидентов
# ---------------------------------------------------------------

INCIDENTS_PATH = os.path.join(APP_DATA_DIR, "incidents.jsonl")

REPAIR_LADDER = {
    "service_down": ("restart", "recreate", "repack", "notify"),
    "degraded": ("rotate", "restart", "recreate", "repack", "notify"),
}

REPAIR_COOLDOWN_SEC = {
    "rotate": 300.0,
    "restart": 120.0,
    "recreate": 600.0,
    "repack": 1800.0,
    "notify": 0.0,
}


def pick_rotation_target(current, favorite, strategies, scores=None):
    """B4/17.5: стратегия для ротации — лучшая по тестам, затем избранная, затем следующая."""
    strategies = [s for s in (strategies or []) if s]
    if not strategies:
        return current
    scores = scores or {}
    try:
        ordered = sorted(range(len(strategies)),
                         key=lambda i: (-float(scores.get(strategies[i], 0.0) or 0.0), i))
    except Exception:
        ordered = list(range(len(strategies)))
    for index in ordered:
        candidate = strategies[index]
        if candidate != current and float(scores.get(candidate, 0.0) or 0.0) > 0.0:
            return candidate
    if favorite and favorite in strategies and favorite != current:
        return favorite
    if current in strategies and len(strategies) > 1:
        return strategies[(strategies.index(current) + 1) % len(strategies)]
    return current if current in strategies else strategies[0]


def next_recovery_step(reason, attempts, history, now, max_repairs=6, window=1800.0):
    """Следующий шаг самовосстановления по лестнице reason.

    reason: "service_down" (служба упала) | "degraded" (пробы деградировали).
    attempts: действия текущего инцидента (до сброса при здоровье).
    history: журнал [{action, ts}] для кулдаунов и лимита попыток.
    Возвращает имя действия или None (лестница исчерпана/лимит).
    """
    ladder = REPAIR_LADDER.get(reason)
    if not ladder:
        return None
    attempted = set(attempts or [])
    recent = [h for h in (history or [])
              if h.get("action") != "notify" and now - float(h.get("ts", 0) or 0.0) <= window]
    if len(recent) >= max_repairs:
        return "notify" if "notify" not in attempted else None
    for action in ladder:
        if action in attempted:
            continue
        cooldown = REPAIR_COOLDOWN_SEC.get(action, 0.0)
        if cooldown and any(h.get("action") == action
                            and now - float(h.get("ts", 0) or 0.0) < cooldown
                            for h in (history or [])):
            continue
        return action
    return None


def log_incident(action, result, level="warn", details=None):
    """Запись инцидента самовосстановления: incidents.jsonl + events.jsonl."""
    try:
        ensure_app_data()
        _rotate_log_file(INCIDENTS_PATH)
        record = {
            "ts": time.time(),
            "time": time.strftime('%Y-%m-%d %H:%M:%S'),
            "level": level,
            "action": action,
            "result": result,
        }
        if details:
            record["details"] = str(details)[:500]
        with open(INCIDENTS_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception: pass
    log_event("incident", action=action, result=result, level=level)


def read_incidents(limit=50):
    """Последние записи журнала инцидентов (для окна «Журнал»)."""
    items = []
    try:
        if os.path.exists(INCIDENTS_PATH):
            with open(INCIDENTS_PATH, encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            for line in lines[-max(1, int(limit)):]:
                try:
                    record = json.loads(line)
                    if isinstance(record, dict):
                        items.append(record)
                except Exception:
                    continue
    except Exception: pass
    return items


def build_issue_url(version, strategy=None, os_info=None, log_tail=None):
    """G10: ссылка на новый issue с предзаполненным телом (без имени пользователя)."""
    try:
        user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        tail = (log_tail or "").strip()
        if user:
            tail = tail.replace(user, "<user>")

        def _clean(text):
            return (text or "").replace("```", "'''")[:6000]

        body = [
            "### Описание проблемы",
            "",
            "<!-- что произошло -->",
            "",
            "### Окружение",
            f"- ZapretLauncher: v{version}",
            f"- ОС: {os_info or ''}",
            f"- Стратегия: {strategy or '—'}",
            "",
            "### Последние строки лога",
            "```",
            _clean(tail),
            "```",
        ]
        params = urllib.parse.urlencode({
            "title": f"[bug] v{version}: ",
            "body": "\n".join(body),
            "labels": "bug",
        })
        return f"https://github.com/{UPDATE_REPO_PATH.strip('/')}/issues/new?{params}"
    except Exception as e:
        log_error(f"build_issue_url error: {e}")
        return ""

def cleanup_old_logs():
    try:
        if not os.path.exists(LOG_PATH): return
        
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        valid_lines = []
        current_time = time.time()
        three_days_sec = 3 * 24 * 60 * 60 # 3 дня в секундах
        
        keep_current_block = False # Флаг: сохраняем ли мы текущий блок текста
        
        for line in lines:
            # Ищем паттерн даты в начале строки
            match = re.search(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            
            if match:
                try:
                    # Превращаем дату в секунды
                    log_time = time.mktime(time.strptime(match.group(1), '%Y-%m-%d %H:%M:%S'))
                    # Включаем флаг сохранения, если лог свежее 3 дней
                    keep_current_block = (current_time - log_time <= three_days_sec)
                except Exception:
                    keep_current_block = False # Если дата кривая — не сохраняем
                    
            # Если флаг включен, мы сохраняем и строку с датой, и все многострочные детали ошибки под ней
            if keep_current_block:
                valid_lines.append(line)

        with open(LOG_PATH, 'w', encoding='utf-8') as f:
            f.writelines(valid_lines)
    except Exception: pass

def migrate_old_files():
    try:
        old_folder = os.path.join(EXE_DIR, FOLDER_NAME)
        old_config = os.path.join(EXE_DIR, CONFIG_FILE_NAME)
        old_log = os.path.join(EXE_DIR, LOG_FILE_NAME)
        if os.path.exists(old_folder):
            try:
                ctypes.windll.kernel32.SetFileAttributesW(old_folder, 128) 
                shutil.rmtree(old_folder, ignore_errors=True)
            except Exception: pass
        if os.path.exists(old_config):
            try: os.remove(old_config)
            except Exception: pass
        if os.path.exists(old_log):
            try: os.remove(old_log)
            except Exception: pass
    except Exception: pass


def create_shortcut(target_path, shortcut_path, work_dir=None):
    """Создаёт .lnk ярлык Windows через WScript.Shell (без pywin32)."""
    try:
        if work_dir is None:
            work_dir = os.path.dirname(target_path)

        def _ps_quote(value):
            return "'" + str(value).replace("'", "''") + "'"

        script = (
            "$ws = New-Object -ComObject WScript.Shell; "
            f"$lnk = $ws.CreateShortcut({_ps_quote(shortcut_path)}); "
            f"$lnk.TargetPath = {_ps_quote(target_path)}; "
            f"$lnk.WorkingDirectory = {_ps_quote(work_dir)}; "
            "$lnk.Description = 'Zapret Launcher'; "
            "$lnk.Save()"
        )
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        result = subprocess.call(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            startupinfo=si, creationflags=0x08000000
        )
        ok = result == 0 and os.path.exists(shortcut_path)
        if not ok:
            log_error(f"Shortcut creation failed (exit={result})")
        return ok
    except Exception as e:
        log_error(f"Shortcut creation error: {e}")
        return False

def set_autorun(enable):
    try:
        autostart_folder = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        shortcut_path = os.path.join(autostart_folder, 'Zapret.lnk')

        if enable:
            exe_path = current_exe_path()
            if not create_shortcut(exe_path, shortcut_path):
                return False
        else:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)

        return True
    except Exception as e:
        log_error(f"Autorun error: {e}")
        return False

def check_autorun():
    try:
        autostart_folder = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        shortcut_path = os.path.join(autostart_folder, 'Zapret.lnk')
        return os.path.exists(shortcut_path)
    except Exception: return False

def service_state(service_name):
    """Состояние службы Windows (RUNNING/STOPPED/...) или UNKNOWN."""
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        result = subprocess.run(["sc", "query", service_name], capture_output=True, text=True,
                                startupinfo=si, creationflags=0x08000000)
        text = (result.stdout or "").upper()
        for state in ("RUNNING", "START_PENDING", "STOP_PENDING", "PAUSED", "STOPPED"):
            if state in text:
                return state
        return "NO_SERVICE"
    except Exception:
        return "UNKNOWN"


def winws_process_running():
    try:
        return any((p.info.get('name') or '').lower() == "winws.exe" for p in psutil.process_iter(['name']))
    except Exception:
        return False


def winws_health_ok():
    """Служба zapret в состоянии RUNNING/START_PENDING или есть живой процесс winws.exe."""
    if service_state("zapret") in ("RUNNING", "START_PENDING"):
        return True
    return winws_process_running()


def detect_foreign_dpi_tools():
    """Ищет сторонние DPI-утилиты, которые могут конфликтовать с zapret."""
    found = []
    try:
        for svc_name in ("GoodbyeDPI", "GoodbyeDPI-Turbo"):
            if service_state(svc_name) in ("RUNNING", "START_PENDING"):
                found.append(f"служба {svc_name}")
        for proc in psutil.process_iter(['name']):
            name = (proc.info.get('name') or '').lower()
            if name in ("goodbyedpi.exe", "goodbyedpi64.exe"):
                found.append(f"процесс {proc.info.get('name')}")
    except Exception as e:
        log_error(f"detect_foreign_dpi_tools error: {e}")
    return found


def migrate_from_legacy_dir():
    r"""E2: переносит данные из старых каталогов (C:\ZapretLauncher, %LOCALAPPDATA%) в активный."""
    for legacy in _legacy_data_roots():
        try:
            if not os.path.isdir(legacy):
                continue
            os.makedirs(APP_DATA_DIR, exist_ok=True)
            moved = 0
            for item in os.listdir(legacy):
                src_path = os.path.join(legacy, item)
                dst_path = os.path.join(APP_DATA_DIR, item)
                if os.path.exists(dst_path):
                    continue
                try:
                    if os.path.isdir(src_path):
                        ctypes.windll.kernel32.SetFileAttributesW(src_path, 128)
                    shutil.move(src_path, dst_path)
                    moved += 1
                except Exception as e:
                    log_error(f"Migration error ({item}): {e}")
            if moved:
                log_error(f"Перенесено объектов из {legacy}: {moved}")
        except Exception as e:
            log_error(f"migrate_from_legacy_dir error ({legacy}): {e}")


def tcp_connect_ms(host, port=443, timeout=1.5):
    """TCP-connect до host:port — проверка по тому же пути, что и DPI-фильтрация."""
    try:
        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return int((time.perf_counter() - start) * 1000)
    except Exception:
        return -1


def detect_quality_preset():
    """D3: пресет качества по железу: low / medium / high."""
    try:
        cores = psutil.cpu_count(logical=False) or psutil.cpu_count() or 2
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        if cores <= 2 or ram_gb < 4:
            return "low"
        if cores >= 8 and ram_gb >= 16:
            return "high"
        return "medium"
    except Exception:
        return "medium"


def battery_state():
    """D6: состояние батареи: present/on_battery/percent."""
    try:
        bat = psutil.sensors_battery()
        if bat is None:
            return {"present": False, "on_battery": False, "percent": None}
        return {"present": True, "on_battery": not bat.power_plugged, "percent": int(bat.percent)}
    except Exception:
        return {"present": False, "on_battery": False, "percent": None}


def foreground_process_name():
    """Имя exe активного окна (для G4)."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return psutil.Process(pid.value).name()
    except Exception:
        return ""


def fullscreen_game_active():
    """G4: активное окно занимает весь экран и это не системный/наш процесс."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False

        class _Rect(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        rect = _Rect()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        if width < screen_w or height < screen_h:
            return False
        name = foreground_process_name().lower()
        return name not in ("", "explorer.exe", "zapret.exe", "zapretweb.exe", "python.exe", "powershell.exe")
    except Exception:
        return False


def seconds_since_last_input():
    """G14: секунды с последнего ввода пользователя (GetLastInputInfo); 0 при ошибке."""
    try:
        class _LastInputInfo(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = _LastInputInfo()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0
        millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
        return max(0, int(millis // 1000))
    except Exception:
        return 0


TGWS_APP_NAME = "TgWsProxy"
TGWS_PORTABLE_DIR = "TgWsProxy_data"
TGWS_DEFAULT_PORT = 1443
TGWS_DEFAULT_HOST = "127.0.0.1"


def tgws_config_path(zapret_dir=None):
    """config.json TgWsProxy: portable рядом с пакетом, иначе %APPDATA%\\TgWsProxy."""
    try:
        base = zapret_dir or locate_zapret_dir()
        portable = os.path.join(base, TGWS_PORTABLE_DIR, "config.json")
        if os.path.exists(portable):
            return portable
    except Exception:
        pass
    return os.path.join(os.environ.get("APPDATA", ""), TGWS_APP_NAME, "config.json")


def read_proxy_config(zapret_dir=None):
    """Текущий конфиг TgWsProxy (host/port/secret) с безопасными умолчаниями."""
    cfg = {"host": TGWS_DEFAULT_HOST, "port": TGWS_DEFAULT_PORT, "secret": ""}
    try:
        path = tgws_config_path(zapret_dir)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for key in ("host", "port", "secret"):
                if key in data:
                    cfg[key] = data[key]
    except Exception as e:
        log_error(f"read_proxy_config error: {e}")
    return cfg


def write_proxy_config(patch, zapret_dir=None):
    """Атомарно дописывает поля в config.json TgWsProxy."""
    try:
        path = tgws_config_path(zapret_dir)
        data = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        data.update(patch)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception as e:
        log_error(f"write_proxy_config error: {e}")
        return False


def proxy_link(cfg):
    """tg://-ссылка для подключения Telegram к прокси (формат Flowseal: secret=dd<hex>)."""
    host = (cfg or {}).get("host") or TGWS_DEFAULT_HOST
    port = (cfg or {}).get("port") or TGWS_DEFAULT_PORT
    secret = (cfg or {}).get("secret") or ""
    link_host = host
    if host == "0.0.0.0":
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                link_host = s.getsockname()[0]
        except OSError:
            link_host = "127.0.0.1"
    return f"tg://proxy?server={link_host}&port={port}&secret=dd{secret}"


def proxy_health_ok(cfg, timeout=1.0):
    """TCP-проверка, что прокси слушает свой порт."""
    host = (cfg or {}).get("host") or TGWS_DEFAULT_HOST
    if host in ("0.0.0.0", ""):
        host = "127.0.0.1"
    try:
        port = int((cfg or {}).get("port") or TGWS_DEFAULT_PORT)
    except Exception:
        return False
    return tcp_connect_ms(host, port, timeout=timeout) >= 0


def split_windows_args(cmdline):
    """Разбор строки аргументов по правилам Windows (CommandLineToArgvW)."""
    try:
        argv_func = ctypes.windll.shell32.CommandLineToArgvW
        argv_func.restype = ctypes.POINTER(ctypes.c_wchar_p)
        argv_func.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
        argc = ctypes.c_int(0)
        argv = argv_func("x " + cmdline, ctypes.byref(argc))
        if not argv:
            return []
        try:
            return [argv[i] for i in range(1, argc.value)]
        finally:
            ctypes.windll.kernel32.LocalFree(argv)
    except Exception as e:
        log_error(f"split_windows_args error: {e}")
        return []


class BypassBackend:
    """A5: интерфейс движка обхода (абстракция от winws/Windows)."""
    name = "base"

    def start(self, zapret_dir, bat_path):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def health_ok(self):
        raise NotImplementedError

    def process_running(self):
        raise NotImplementedError


class WinwsBackend(BypassBackend):
    """Боевой backend: служба zapret / прямой winws.exe."""
    name = "winws"

    def start(self, zapret_dir, bat_path):
        ok = install_zapret_service(zapret_dir, bat_path)
        if not ok:
            ok = launch_winws_direct(zapret_dir, bat_path)
        return bool(ok)

    def stop(self):
        stop_services_and_processes()
        return True

    def health_ok(self):
        return winws_health_ok()

    def process_running(self):
        return winws_process_running()


class MockBackend(BypassBackend):
    """H5: dev-режим — интерфейс без служб, процессов и сети."""
    name = "mock"

    def __init__(self):
        self._on = False

    def start(self, zapret_dir, bat_path):
        self._on = True
        return True

    def stop(self):
        self._on = False
        return True

    def health_ok(self):
        return self._on

    def process_running(self):
        return self._on


def is_dev_mode():
    """H5: dev-режим (--dev или ZAPRET_DEV=1) — без админа и без реальной службы."""
    return "--dev" in sys.argv or os.environ.get("ZAPRET_DEV") == "1"


def get_backend():
    return MockBackend() if is_dev_mode() else WinwsBackend()


def load_strategy_meta(zapret_dir):
    """A4/C5: метаданные стратегий: <bat>.json (title/tags/description) + эвристики по имени."""
    meta = {}
    try:
        for name in list_strategies(zapret_dir):
            info = {"title": name.replace(".bat", ""), "tags": [], "description": ""}
            path = os.path.join(zapret_dir, name + ".json")
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    for key in ("title", "tags", "description"):
                        if key in data:
                            info[key] = data[key]
                except Exception as e:
                    log_error(f"strategy meta {name}: {e}")
            low = name.lower()
            derived = []
            match = re.search(r"alt(\d*)", low)
            if match:
                derived.append("ALT" + match.group(1))
            if "fake" in low:
                derived.append("FAKE")
            if "simple" in low:
                derived.append("SIMPLE")
            if "exp" in low:
                derived.append("EXP")
            if "general" in low:
                derived.append("GENERAL")
            if isinstance(info.get("tags"), list):
                info["tags"] = sorted(set(str(t) for t in info["tags"] + derived))
            else:
                info["tags"] = sorted(set(derived))
            meta[name] = info
    except Exception as e:
        log_error(f"load_strategy_meta error: {e}")
    return meta


CRASH_DIR = os.path.join(APP_DATA_DIR, "crashes")


def install_crash_handler(app_name="launcher"):
    """E6: локальные крашрепорты без сети: APP_DATA_DIR/crashes/<ts>_<app>.txt."""
    def _hook(exc_type, exc_value, exc_tb):
        try:
            ensure_app_data()
            os.makedirs(CRASH_DIR, exist_ok=True)
            path = os.path.join(CRASH_DIR, time.strftime("%Y%m%d_%H%M%S") + f"_{app_name}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"ZapretLauncher {CURRENT_VERSION} ({app_name})\n")
                f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
            log_error(f"Crash report saved: {path}")
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def latest_crash_file():
    """Последний локальный крашрепорт (или "")."""
    try:
        if not os.path.isdir(CRASH_DIR):
            return ""
        files = sorted(os.path.join(CRASH_DIR, f) for f in os.listdir(CRASH_DIR))
        return files[-1] if files else ""
    except Exception:
        return ""


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def is_trusted_update_url(url):
    try:
        parsed = urllib.parse.urlparse(url or "")
        if parsed.scheme != "https":
            return False
        if parsed.hostname not in UPDATE_ALLOWED_HOSTS:
            return False
        return parsed.path.startswith(UPDATE_REPO_PATH)
    except Exception:
        return False


def is_trusted_github_url(url):
    try:
        parsed = urllib.parse.urlparse(url or "")
        if parsed.scheme != "https" or parsed.hostname not in UPDATE_ALLOWED_HOSTS:
            return False
        return parsed.path.startswith("/Flowseal/") or parsed.path.startswith("/Aikiovade/")
    except Exception:
        return False


# --- F2/F5/E1: каналы обновлений, зеркала, подпись манифеста ---
UPDATE_CHANNELS = {
    "stable": UPDATE_VERSION_URL,
    "beta": "https://raw.githubusercontent.com/Aikiovade/ZapretLauncher/main/update_info_beta.json",
}
UPDATE_PUBKEY_HEX = ""  # E1: публичный Ed25519-ключ (hex) для проверки подписи манифеста
DEFAULT_UPDATE_CHANNEL = "stable"


def update_manifest_url(channel):
    """URL манифеста для канала (stable/beta)."""
    return UPDATE_CHANNELS.get((channel or DEFAULT_UPDATE_CHANNEL).lower(), UPDATE_VERSION_URL)


def update_download_candidates(info, key="download_url"):
    """F5: доверенные URL для скачивания (основной + зеркала из манифеста), по порядку."""
    urls = []
    primary = (info or {}).get(key)
    if primary:
        urls.append(primary)
    for url in (info or {}).get("mirrors") or []:
        if isinstance(url, str):
            urls.append(url)
    result = []
    for url in urls:
        if is_trusted_update_url(url) and url not in result:
            result.append(url)
        elif url:
            log_error(f"Недоверенное зеркало обновления пропущено: {url}")
    return result


# --- A9/I3/F2: обновление через установщик vs portable self-update ---

def update_mode():
    """Способ обновления: 'portable' (exe рядом с данными) | 'installed' (Program Files)."""
    try:
        if is_portable_mode():
            return "portable"
    except Exception:
        pass
    return "installed"


INSTALL_MODE_FILE = "install_mode.json"


def install_mode_path():
    return os.path.join(APP_DATA_DIR, INSTALL_MODE_FILE)


def record_install_mode():
    """A9/I3: зафиксировать способ установки (exe/компонент) для апдейтера (только frozen)."""
    try:
        if not getattr(sys, 'frozen', False):
            return {}
        if is_portable_mode():
            return {}
        exe_name = os.path.basename(current_exe_path())
        data = {
            "mode": update_mode(),
            "exe": exe_name,
            "dir": EXE_DIR,
            "components": "web" if exe_name.lower() == "zapretweb.exe" else "tk",
        }
        ensure_app_data()
        tmp = install_mode_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, install_mode_path())
        return data
    except Exception as e:
        log_error(f"record_install_mode error: {e}")
        return {}


def recorded_install_mode():
    """Записанный режим установки (install_mode.json) или {}."""
    try:
        with open(install_mode_path(), encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def installed_components():
    """Компонент для silent-апдейта: 'web' | 'tk' (install_mode.json или имя exe)."""
    recorded = recorded_install_mode().get("components")
    if recorded in ("web", "tk"):
        return recorded
    return "web" if os.path.basename(current_exe_path()).lower() == "zapretweb.exe" else "tk"


def installed_exe_path(exe_name=None):
    """Путь установленного exe (совпадает с DefaultDirName={autopf}\\ZapretLauncher в .iss)."""
    name = exe_name or recorded_install_mode().get("exe") or INSTALLED_EXE_NAME
    base = os.environ.get('ProgramFiles') or os.path.join(os.environ.get('SystemDrive', 'C:') + os.sep, 'Program Files')
    return os.path.join(base, INSTALL_DIR_NAME, name)


def installer_update_available(info):
    """Есть ли в манифесте данные установщика (installer_url + installer_sha256)."""
    url = str((info or {}).get("installer_url") or "")
    sha = str((info or {}).get("installer_sha256") or "")
    return bool(url and sha) and is_trusted_update_url(url)


def launch_installer_and_restart(setup_path, components=None):
    """Запускает Setup.exe /SILENT и после установки — установленный exe (detached cmd).

    components: 'web' | 'tk' — сохранить выбор интерфейса при silent-обновлении.
    Вызывающий код после успешного запуска должен немедленно завершиться (os._exit).
    """
    try:
        exe = installed_exe_path()
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        cmd = f'start "" /wait "{setup_path}" /SILENT /NORESTART /CLOSEAPPLICATIONS'
        if components in ("web", "tk"):
            cmd += f' /COMPONENTS="{components}" /UI={components}'
        cmd += f' && start "" "{exe}"'
        subprocess.Popen(["cmd", "/c", cmd], startupinfo=si, creationflags=0x08000000, close_fds=True)
        return True
    except Exception as e:
        log_error(f"launch_installer_and_restart error: {e}")
        return False


def cli_install_service():
    """Установщик вызывает: поставить службу один раз (если ещё нет). Требует админа."""
    try:
        if service_state("zapret") in ("RUNNING", "START_PENDING", "STOPPED", "PAUSED"):
            log_error("Служба zapret уже установлена — пропускаю --install-service")
            return True
        zapret_dir = ensure_payload()
        name = DEFAULT_BAT
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                name = json.load(f).get("bat") or DEFAULT_BAT
        except Exception:
            pass
        if name not in list_strategies(zapret_dir):
            strategies = list_strategies(zapret_dir)
            name = strategies[0] if strategies else ""
        if not name:
            log_error("--install-service: нет доступных стратегий")
            return False
        ok = install_zapret_service(zapret_dir, os.path.join(zapret_dir, name))
        log_error(f"--install-service: {'OK' if ok else 'FAIL'} ({name})")
        return ok
    except Exception as e:
        log_error(f"cli_install_service error: {e}")
        return False


def discord_client_id():
    """G12: Client ID приложения Discord (env override → вшитая константа)."""
    return (os.environ.get("ZAPRET_DISCORD_CLIENT_ID") or DISCORD_CLIENT_ID or "").strip()


def discord_payload(status, strategy, start_time, lang):
    """G12: payload presence (details/state/start) для текущего состояния."""
    texts = TRANSLATIONS_DATA.get(lang, TRANSLATIONS_DATA["EN"])
    if status == "ON":
        uptime = int(time.time() - start_time) if start_time else 0
        state = (f"{texts.get('status_on', 'ON')} • "
                 f"{uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}")
        start = int(start_time) if start_time else None
    elif status in ("BUSY", "TESTING"):
        state = texts.get("status_busy", "...")
        start = None
    else:
        state = "OFF"
        start = None
    details = f"{texts.get('btn_strategy', 'Strategy')}: {strategy or '—'}"
    return {"details": details, "state": state, "start": start}


def manifest_signing_payload(data):
    """Канонический payload манифеста для подписи (без поля signature)."""
    clean = {key: value for key, value in (data or {}).items() if key != "signature"}
    return json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_signature_ok(data):
    """E1: проверка подписи манифеста. Пока публичный ключ не задан — проверка пропускается."""
    signature = ((data or {}).get("signature") or "").strip()
    if not UPDATE_PUBKEY_HEX:
        if signature:
            log_error("Манифест подписан, но публичный ключ не задан — проверка подписи пропущена")
        return True
    if not signature:
        log_error("У манифеста нет подписи, а публичный ключ задан")
        return False
    try:
        return ed25519.verify(UPDATE_PUBKEY_HEX, manifest_signing_payload(data), signature)
    except Exception as e:
        log_error(f"manifest_signature_ok error: {e}")
        return False


ZAPRET_RELEASES_API = "https://api.github.com/repos/Flowseal/zapret-discord-youtube/releases/latest"


def fetch_zapret_latest_release():
    """Последний релиз Flowseal zapret-discord-youtube: tag, zip-URL, sha256."""
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(ZAPRET_RELEASES_API,
                                     headers={"User-Agent": f"ZapretLauncher/{CURRENT_VERSION}"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
        asset = None
        for item in data.get("assets", []):
            if item.get("name", "").endswith(".zip"):
                asset = item
                break
        if not asset:
            return None
        digest = asset.get("digest") or ""
        sha = digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else ""
        return {"tag": data.get("tag_name", ""), "url": asset["browser_download_url"],
                "name": asset["name"], "sha256": sha}
    except Exception as e:
        log_error(f"fetch_zapret_latest_release error: {e}")
        return None


def update_zapret_data():
    """Скачивает и распаковывает последний пакет стратегий Flowseal. -> (ok, message)."""
    rel = fetch_zapret_latest_release()
    if not rel:
        return False, "Не удалось получить список релизов Flowseal"
    if not is_trusted_github_url(rel["url"]):
        return False, "Недоверенный URL релиза"

    folder_name = rel["name"][:-4] if rel["name"].lower().endswith(".zip") else rel["name"]
    dest_dir = os.path.join(APP_DATA_DIR, folder_name)
    if payload_complete(dest_dir):
        return True, f"Уже установлено: {folder_name}"

    tmp_zip = os.path.join(os.environ.get("TEMP", "."), rel["name"])
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(rel["url"],
                                     headers={"User-Agent": f"ZapretLauncher/{CURRENT_VERSION}"})
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp, open(tmp_zip, 'wb') as out:
            shutil.copyfileobj(resp, out)

        if rel["sha256"]:
            actual = sha256_of_file(tmp_zip)
            if actual.lower() != rel["sha256"]:
                os.remove(tmp_zip)
                return False, "Хэш пакета не совпал"

        old_dir = locate_zapret_dir()
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with zipfile.ZipFile(tmp_zip, 'r') as zip_ref:
            _safe_extractall(zip_ref, APP_DATA_DIR)

        if not payload_complete(dest_dir):
            return False, "В архиве нет bin/winws.exe"

        if os.path.isdir(old_dir) and os.path.realpath(old_dir) != os.path.realpath(dest_dir):
            _migrate_user_data(old_dir, dest_dir)

        try:
            os.remove(tmp_zip)
        except Exception:
            pass
        return True, folder_name
    except Exception as e:
        log_error(f"update_zapret_data error: {e}")
        return False, str(e)


def validate_port_range(value):
    """Проверяет диапазон портов в формате service.bat (12 или 1024-1934,1936-65535)."""
    try:
        clean = re.sub(r'\s+', '', value or '')
        if not clean:
            return None
        for item in clean.split(','):
            match = re.fullmatch(r'([1-9]\d{0,4})(?:-([1-9]\d{0,4}))?', item)
            if not match:
                return None
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            if start > 65535 or end > 65535 or start > end:
                return None
        return clean
    except Exception:
        return None


def read_game_filter(zapret_dir):
    r"""Читает utils\game_filter.enabled. Возвращает (tcp, udp, all)."""
    try:
        path = os.path.join(zapret_dir, "utils", GAME_FILTER_FILE)
        data = {}
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    if '=' in line:
                        key, _, value = line.partition('=')
                        data[key.strip().lower()] = value.strip()
        mode = data.get("mode", "disabled").lower()
        tcp_range = validate_port_range(data.get("tcp", "")) or "12"
        udp_range = validate_port_range(data.get("udp", "")) or "12"
        if mode == "all":
            return tcp_range, udp_range, tcp_range
        if mode == "tcp":
            return tcp_range, "12", tcp_range
        if mode == "udp":
            return "12", udp_range, udp_range
    except Exception as e:
        log_error(f"read_game_filter error: {e}")
    return "12", "12", "12"


def ensure_user_lists(zapret_dir):
    """Создаёт плейсхолдеры user-списков (аналог service.bat load_user_lists)."""
    try:
        lists_dir = os.path.join(zapret_dir, "lists")
        os.makedirs(lists_dir, exist_ok=True)
        defaults = {
            "list-general-user.txt": "# Never leave this file empty\ndomain.example.abc\n",
            "list-exclude-user.txt": "domain.example.abc\n",
            "ipset-exclude-user.txt": "203.0.113.113/32\n",
        }
        for name, content in defaults.items():
            path = os.path.join(lists_dir, name)
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
    except Exception as e:
        log_error(f"ensure_user_lists error: {e}")


def enable_tcp_timestamps():
    """Включает TCP timestamps, если они выключены (аналог service.bat :tcp_enable)."""
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        result = subprocess.run(
            ["netsh", "interface", "tcp", "show", "global"],
            capture_output=True, text=True,
            startupinfo=si, creationflags=0x08000000
        )
        output = (result.stdout or "").lower()
        enabled = any("timestamps" in line and "enabled" in line for line in output.splitlines())
        if not enabled:
            subprocess.call(
                ["netsh", "interface", "tcp", "set", "global", "timestamps=enabled"],
                startupinfo=si, creationflags=0x08000000
            )
    except Exception as e:
        log_error(f"enable_tcp_timestamps error: {e}")


def parse_strategy_bat(bat_path, zapret_dir, gf_tcp="12", gf_udp="12", gf_all="12"):
    """Извлекает и нормализует аргументы winws.exe из .bat стратегии."""
    try:
        try:
            with open(bat_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(bat_path, 'r', encoding='cp1251', errors='replace') as f:
                content = f.read()

        content = re.sub(r'\^\s*\n', ' ', content)
        args_str = ""
        for line in content.split('\n'):
            if 'winws.exe' in line.lower() and not line.strip().lower().startswith(('rem', '::')):
                match = re.search(r'winws\.exe["\']?\s+(.*)', line, re.IGNORECASE)
                if match:
                    args_str = match.group(1).strip()
                    break

        if not args_str:
            return None

        zapret_dir_slash = zapret_dir + "\\"
        args_str = args_str.replace('%~dp0', zapret_dir_slash)
        args_str = args_str.replace('%%BIN%%', zapret_dir_slash + "bin\\")
        args_str = args_str.replace('%BIN%', zapret_dir_slash + "bin\\")
        args_str = args_str.replace('%%LISTS%%', zapret_dir_slash + "lists\\")
        args_str = args_str.replace('%LISTS%', zapret_dir_slash + "lists\\")
        args_str = re.sub(r'%%?GameFilterTCP%%?', gf_tcp, args_str, flags=re.IGNORECASE)
        args_str = re.sub(r'%%?GameFilterUDP%%?', gf_udp, args_str, flags=re.IGNORECASE)
        args_str = re.sub(r'%%?GameFilter%%?', gf_all, args_str, flags=re.IGNORECASE)
        args_str = args_str.replace('^', '')
        args_str = re.sub(r'\s+', ' ', args_str)
        return args_str
    except Exception as e:
        log_error(f"parse_strategy_bat error: {e}")
        return None


def _safe_extractall(zip_ref, dest_dir):
    """extractall с защитой от zip-slip и абсолютных путей."""
    dest_root = os.path.realpath(dest_dir)
    for member in zip_ref.infolist():
        name = member.filename.replace('\\', '/')
        if name.startswith('/') or re.match(r'^[A-Za-z]:', name) or '..' in name.split('/'):
            log_error(f"Пропущена подозрительная запись архива: {member.filename}")
            continue
        target = os.path.realpath(os.path.join(dest_root, name))
        if target != dest_root and not target.startswith(dest_root + os.sep):
            log_error(f"Пропущена запись вне каталога: {member.filename}")
            continue
        zip_ref.extract(member, dest_root)


_tcp_timestamps_done = False


def install_zapret_service(zapret_dir, bat_path):
    """Ставит службу zapret с аргументами из .bat стратегии. Общая логика для всех UI."""
    global _tcp_timestamps_done
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        cf = 0x08000000

        gf_tcp, gf_udp, gf_all = read_game_filter(zapret_dir)
        ensure_user_lists(zapret_dir)
        if not _tcp_timestamps_done:
            enable_tcp_timestamps()
            _tcp_timestamps_done = True

        args_str = parse_strategy_bat(bat_path, zapret_dir, gf_tcp, gf_udp, gf_all)
        if not args_str:
            log_error(f"Не удалось найти аргументы winws в файле {bat_path}")
            return False

        bin_path = os.path.join(zapret_dir, 'bin', 'winws.exe')
        if not os.path.exists(bin_path):
            log_error(f"winws.exe не найден: {bin_path}")
            return False
        check_winws_hash(bin_path)

        subprocess.call(["net", "stop", "zapret"], startupinfo=si, creationflags=cf)
        subprocess.call(["sc", "delete", "zapret"], startupinfo=si, creationflags=cf)
        subprocess.call(["taskkill", "/F", "/IM", "winws.exe"], startupinfo=si, creationflags=cf)
        time.sleep(0.5)

        service_cmd = f'"{bin_path}" {args_str}'
        subprocess.call(
            ["sc", "create", "zapret", "binPath=", service_cmd,
             "DisplayName=", "zapret", "start=", "auto"],
            startupinfo=si, creationflags=cf
        )
        subprocess.call(
            ["sc", "description", "zapret", "Zapret DPI bypass software"],
            startupinfo=si, creationflags=cf
        )
        subprocess.call(
            ["sc", "failure", "zapret", "reset=", "86400",
             "actions=", "restart/5000/restart/10000/restart/30000"],
            startupinfo=si, creationflags=cf
        )

        bat_name = os.path.basename(bat_path).replace(".bat", "")
        subprocess.call(
            ["reg", "add", r"HKLM\System\CurrentControlSet\Services\zapret",
             "/v", "zapret-discord-youtube", "/t", "REG_SZ", "/d", bat_name, "/f"],
            startupinfo=si, creationflags=cf
        )

        res = subprocess.call(["sc", "start", "zapret"], startupinfo=si, creationflags=cf)
        time.sleep(0.5)
        return res == 0 or winws_process_running()
    except Exception as e:
        log_error(f"Ошибка установки службы: {e}")
        return False


def launch_winws_direct(zapret_dir, bat_path):
    """Прямой запуск winws.exe процессом (фолбэк, если служба не ставится)."""
    try:
        gf_tcp, gf_udp, gf_all = read_game_filter(zapret_dir)
        args_str = parse_strategy_bat(bat_path, zapret_dir, gf_tcp, gf_udp, gf_all)
        if not args_str:
            return False

        bin_path = os.path.join(zapret_dir, 'bin', 'winws.exe')
        if not os.path.exists(bin_path):
            return False

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        subprocess.call(["taskkill", "/F", "/IM", "winws.exe"], startupinfo=si, creationflags=0x08000000)
        time.sleep(0.3)

        argv = [bin_path] + split_windows_args(args_str)
        subprocess.Popen(argv, cwd=zapret_dir, startupinfo=si,
                         creationflags=0x08000000, close_fds=True)
        time.sleep(0.8)
        return winws_process_running()
    except Exception as e:
        log_error(f"launch_winws_direct error: {e}")
        return False


def run_custom_strategy_probe(zapret_dir, args_str, restore_bat_path=None, seconds=12.0, on_tick=None):
    """17.5: проверить произвольные аргументы winws (конструктор стратегий).

    Останавливает службу, запускает winws.exe напрямую с args_str, каждые ~2 c
    пробы сервисов; затем останавливает winws и восстанавливает службу из
    restore_bat_path (если она была включена). Возвращает score/результаты.
    """
    result = {"ok": False, "score": 0.0, "results": {}, "restored": None}
    bin_path = os.path.join(zapret_dir, 'bin', 'winws.exe')
    if not os.path.exists(bin_path) or not (args_str or "").strip():
        return result
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    was_on = winws_health_ok()
    process = None
    try:
        stop_services_and_processes()
        time.sleep(0.5)
        argv = [bin_path] + split_windows_args(args_str)
        process = subprocess.Popen(argv, cwd=zapret_dir, startupinfo=si,
                                   creationflags=0x08000000, close_fds=True)
        deadline = time.time() + max(4.0, float(seconds))
        last_results = {}
        while time.time() < deadline and process.poll() is None:
            try:
                last_results = probe_services(timeout=2.0)
            except Exception:
                last_results = {}
            if on_tick:
                try:
                    on_tick(max(0.0, deadline - time.time()), last_results)
                except Exception:
                    pass
            time.sleep(1.0)
        result["results"] = last_results
        result["score"] = round(score_probe_results(last_results), 3)
        result["ok"] = process.poll() is None or result["score"] > 0.0
    except Exception as e:
        log_error(f"run_custom_strategy_probe error: {e}")
    finally:
        try:
            if process is not None and process.poll() is None:
                process.terminate()
        except Exception:
            pass
        subprocess.call(["taskkill", "/F", "/IM", "winws.exe"], startupinfo=si, creationflags=0x08000000)
        time.sleep(0.5)
        if was_on and restore_bat_path and os.path.exists(restore_bat_path):
            result["restored"] = install_zapret_service(zapret_dir, restore_bat_path)
        log_event("probe_custom_strategy", score=result["score"], restored=result["restored"])
    return result


def stop_services_and_processes():
    """Останавливает службу zapret, WinDivert и процессы winws."""
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    cf = 0x08000000

    subprocess.call(["net", "stop", "zapret"], startupinfo=si, creationflags=cf)
    subprocess.call(["sc", "delete", "zapret"], startupinfo=si, creationflags=cf)
    subprocess.call(["net", "stop", "WinDivert"], startupinfo=si, creationflags=cf)
    subprocess.call(["sc", "delete", "WinDivert"], startupinfo=si, creationflags=cf)
    subprocess.call(["net", "stop", "WinDivert14"], startupinfo=si, creationflags=cf)
    subprocess.call(["sc", "delete", "WinDivert14"], startupinfo=si, creationflags=cf)
    for target in TARGET_PROCESSES:
        subprocess.call(["taskkill", "/F", "/IM", target], startupinfo=si, creationflags=cf)


def is_strategy_bat(filename):
    """Стратегия — любой .bat, кроме служебного service.bat (17.5: не фильтруем подстроку)."""
    return (str(filename).lower().endswith(".bat")
            and os.path.splitext(str(filename))[0].lower() != "service")


def list_strategies(zapret_dir):
    """Список .bat-стратегий в каталоге данных."""
    try:
        if zapret_dir and os.path.isdir(zapret_dir):
            return sorted(f for f in os.listdir(zapret_dir) if is_strategy_bat(f))
    except Exception as e:
        log_error(f"list_strategies error: {e}")
    return []


def run_strategy_tests(zapret_dir, on_line=None, should_continue=None):
    """Общий PS-раннер тестов стратегий: возвращает имя лучшей .bat или None.

    on_line(clean_line) вызывается по мере вывода; should_continue() может
    прервать обход (для отмены из UI).
    """
    ps1_path = os.path.join(zapret_dir, "utils", "test zapret.ps1")
    if not os.path.exists(ps1_path):
        log_error(f"Test script not found: {ps1_path}")
        return None
    process = None
    best = None
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        env = dict(os.environ, NO_UPDATE_CHECK="1")
        process = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            startupinfo=si, creationflags=0x08000000, text=True,
            encoding='cp866', errors='replace', env=env)
        process.stdin.write("1\n1\n")
        process.stdin.flush()
        for line in iter(process.stdout.readline, ''):
            if should_continue is not None and not should_continue():
                break
            line = re.sub(r'\x1b\[[0-9;]*m', '', line.strip())
            if not line:
                continue
            if on_line is not None:
                on_line(line)
            if "Best config:" in line and best is None:
                name = line.split("Best config:")[-1].strip()
                for f in list_strategies(zapret_dir):
                    if f.lower() == name.lower() or name.replace(".bat", "").lower() in f.lower():
                        best = f
                        break
                process.terminate()
                break
    except Exception as e:
        log_error(f"run_strategy_tests error: {e}")
    finally:
        if process:
            try:
                process.terminate()
            except Exception:
                pass
    return best


KNOWN_WINWS_SHA256 = {
    "affb4f69d2ea302a7abccd5325d81826e140ddae014f1e070bc4a6c0dd555188",
}


def check_winws_hash(bin_path):
    """Сверяет winws.exe с известными хэшами. Не блокирует, только предупреждает."""
    try:
        actual = sha256_of_file(bin_path)
        if actual in KNOWN_WINWS_SHA256:
            return True
        log_error(f"winws.exe хэш неизвестен: {actual} — возможно, обновлённая или подменённая версия")
        return False
    except Exception as e:
        log_error(f"check_winws_hash error: {e}")
        return False


def list_active_interfaces():
    """Список активных сетевых интерфейсов (для диагностики мультиадаптеров)."""
    try:
        stats = psutil.net_if_stats()
        return sorted(name for name, st in stats.items() if st.isup and name != "Loopback Pseudo-Interface 1")
    except Exception:
        return []


def get_current_network():
    """Текущая сеть: SSID для Wi-Fi или 'ethernet'. -> {ssid, network_key}."""
    ssid = ""
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        result = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True,
                                text=True, startupinfo=si, creationflags=0x08000000,
                                encoding="cp866", errors="replace")
        for line in (result.stdout or "").splitlines():
            if "SSID" in line and "BSSID" not in line and ":" in line:
                value = line.split(":", 1)[1].strip()
                if value:
                    ssid = value
                    break
    except Exception:
        pass
    if ssid:
        return {"ssid": ssid, "network_key": ssid}
    return {"ssid": "", "network_key": "ethernet"}


SERVICE_PROBES = (
    ("YouTube", "www.youtube.com", 443),
    ("Discord", "discord.com", 443),
    ("Telegram", "telegram.org", 443),
    ("Google", "www.google.com", 443),
)


def probe_services(timeout=2.0):
    """TCP-пробы доступности сервисов. Возвращает {name: ms|-1}."""
    results = {}
    for name, host, port in SERVICE_PROBES:
        results[name] = tcp_connect_ms(host, port, timeout=timeout)
    return results


def score_probe_results(results):
    """Доля доступных сервисов (0..1)."""
    try:
        if not results:
            return 0.0
        return sum(1 for v in results.values() if v >= 0) / len(results)
    except Exception:
        return 0.0


class AudioEngine:

    @staticmethod
    def create_click_sound(freq_start, freq_end, duration_ms=100, volume=0.8):
        try:
            sample_rate = 44100
            num_channels = 1
            bits_per_sample = 8
            num_samples = int(sample_rate * duration_ms / 1000)
            data = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                val = int(127 * volume * (1.0 - i/num_samples) * math.sin(2 * math.pi * (freq_start + (freq_end - freq_start) * (i/num_samples)) * t) + 128)
                data.extend(struct.pack('B', min(255, max(0, val))))
            byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
            block_align = num_channels * (bits_per_sample // 8)
            wav = bytearray(b'RIFF')
            wav.extend(struct.pack('<I', 36 + len(data)))
            wav.extend(b'WAVEfmt ')
            wav.extend(struct.pack('<IHHIIHH', 16, 1, num_channels, sample_rate, byte_rate, block_align, bits_per_sample))
            wav.extend(b'data')
            wav.extend(struct.pack('<I', len(data)))
            wav.extend(data)
            return bytes(wav)
        except Exception as e: 
            log_error(f"Sound gen error: {e}")
            return None

class WarpParticle:
    def __init__(self):
        self.reset(initial=True)
    def reset(self, initial=False):
        self.x = random.uniform(-1000, 1000)
        self.y = random.uniform(-1000, 1000)
        self.z = random.uniform(1, 1000) if initial else 1000
        self.type = random.choice(['dot', 'square', 'cross'])
        self.base_size = random.uniform(1, 3)
    def update(self, speed):
        self.z -= speed
        if self.z <= 1: self.reset()
    def draw(self, canvas, cx, cy, w, h, active_color, interpolate_fn):
        fov = 400
        scale = fov / self.z
        sx, sy = cx + self.x * scale, cy + self.y * scale
        if sx < -50 or sx > w + 50 or sy < -50 or sy > h + 50: return
        depth = 1.0 - (self.z / 1000)
        col = interpolate_fn("#0a0b1e", active_color, depth * 0.7)
        if self.type == 'cross': col = interpolate_fn("#111a33", "#ffffff", depth)
        size = self.base_size * scale
        if self.type == 'dot':
            canvas.create_oval(sx, sy, sx+size, sy+size, fill=col, outline="")
        elif self.type == 'square':
            if size > 3: canvas.create_rectangle(sx, sy, sx+size, sy+size, outline=col, width=1)
            else: canvas.create_rectangle(sx, sy, sx+size, sy+size, fill=col, outline="")
        elif self.type == 'cross':
            l = size
            canvas.create_line(sx, sy-l, sx, sy+l, fill=col, width=1)
            canvas.create_line(sx-l, sy, sx+l, sy, fill=col, width=1)

class SnowFlake:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.reset(initial=True)
    def reset(self, initial=False):
        self.x = random.randint(0, self.w)
        self.y = random.randint(-self.h, 0) if initial else random.randint(-50, -10)
        self.size = random.uniform(1.5, 3.5)
        self.speed = random.uniform(1.0, 3.0)
        self.sway_amp, self.sway_freq, self.phase = random.uniform(0, 4), random.uniform(0.01, 0.04), random.uniform(0, math.pi*2)
    def update(self, w, h):
        self.w, self.h = w, h
        self.y += self.speed
        self.x += math.sin(self.y * self.sway_freq + self.phase) * self.sway_amp
        if self.y > self.h: self.reset()
    def draw(self, canvas):
        canvas.create_oval(self.x, self.y, self.x+self.size, self.y+self.size, fill="white", outline="")

# ======================================================================
# 3. ГЛАВНОЕ ОКНО
# ======================================================================
class ZapretLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 1. МГНОВЕННОЕ СКРЫТИЕ И ПОКРАСКА
        self.attributes("-alpha", 0) 
        self.configure(fg_color="#0a0b1e") 

        try:
            myappid = f'mycompany.zapret.launcher.v{CURRENT_VERSION}'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception: pass

        self.current_lang = "RU" 
        self.translations_data = TRANSLATIONS_DATA
        self.themes_data = THEMES_DATA
        self.ui_scale = 1.0 
        
        self.update_data = None 

        

        self.title(f"Zapret by A1kio v{CURRENT_VERSION}")
        ws, self.hs = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{(ws - WINDOW_WIDTH) // 2}+{(self.hs - WINDOW_HEIGHT) // 2}")
        self.resizable(True, True)
        self.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.fullscreen = False
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.quit_fullscreen)
        self.bind("<F12>", lambda _e: self.toggle_profile())
        try:
            self.icon_path = resource_path("icon.ico")
            if os.path.exists(self.icon_path): self.iconbitmap(self.icon_path)
        except Exception: self.icon_path = None
        self.canvas = tk.Canvas(self, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, bg="#0a0b1e", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.launcher_status = "OFF"
        self.start_time, self.animation_step, self.status_text = 0, 0, "READY"
        self.hud_values = {"CPU": "00", "GPU": "00", "RAM": "00", "NET": "00", "PING": "---"}
        self._watchdog_running = True  # Флаг для watchdog-потока
        self._total_uptime_sec = 0     # Кумулятивное время работы в секундах
        self._launch_count = 0         # Количество запусков обхода
        self.proxy_status = "OFF"      # TgWsProxy: OFF / ON / BUSY
        self._proxy_process = None     # subprocess.Popen прокси
        self.compact_mode = False      # Мини-оверлей
        self.idle_hide_min = 0         # G14: авто-скрытие при простое (0 = выключено)
        self._idle_hidden = False
        self.intro_enabled = True      # Стартовая анимация (osu-style)
        self.discord_client_id = ""    # G12: Client ID (если не задан — спросим при включении)
        self._intro_start = 0.0
        self._intro_end = 0.0
        self.discord_rpc = False       # G12: Discord Rich Presence (по умолчанию выключено)
        self.discord = None            # discord_rpc.DiscordPresence | None
        self._discord_ts = 0.0         # троттлинг обновлений presence из render_loop
        self._bypass_check = "---"     # Детектор: ---, OK, FAIL
        self.changelog_open = False    # Overlay «Что нового»
        
        self.settings_open, self.settings_anim = False, 0.0 
        self.menu_last_active = time.time() # <-- Таймер активности меню
        
        self.mode_menu_open, self.mode_menu_anim, self.menu_scroll_offset = False, 0.0, 0
        self.snow_enabled, self.minimal_mode, self.start_minimized, self.auto_repair = True, False, False, False
        self.autorun_enabled = True
        self.auto_restart = True       # Авто-перезапуск при падении службы
        # 17.5: Windows-интеграция, OSD и «Иммунитет»
        self.taskbar_ui = True         # Оверлей/кнопки/прогресс на панели задач
        self.osd_enabled = True        # Всплывающее OSD при переключении обхода
        self.self_heal = True          # Лестница самовосстановления (restart→recreate→repack)
        self.auto_rotate = False       # Ротация стратегии при деградации доступности
        self.taskbar = None
        self._tb_last_status = None
        self._tb_last_progress = None
        self._repair_history = []
        self._repair_attempts = []
        self._repair_active = False
        self._degrade_streak = 0
        self._degrade_running = False
        self._degrade_counter = 0
        self._builder_probe_active = False
        self.desired_bypass = True     # Последнее состояние обхода (ON/OFF)
        self.proxy_enabled = False     # TgWsProxy: включать при старте
        self.notifications_enabled = True  # Уведомления в системном трее
        self.exe_path = None           # Путь к .exe для автозапуска
        self.theme_name = DEFAULT_THEME
        self.theme_color = self.themes_data[DEFAULT_THEME]
        self.selected_bat, self.favorite_bat = DEFAULT_BAT, None
        self.bat_files = STRATEGY_LIST

        self.zapret_dir = locate_zapret_dir()
        self._refresh_bat_files()

        self._color_cache = {}
        self._stats_dirty = False
        self._stats_last_save = 0.0
        self._install_lock = threading.Lock()
        self._repair_lock = threading.Lock()
        self._ui_queue = queue.Queue()
        self._tcp_timestamps_done = False
        self._last_render_error = 0.0
        self._profile = False
        self._frame_times = []
        self._frame_ts = 0.0
        self._app_cpu = 0.0
        self._app_cpu_ts = 0.0
        self._proc = None

        
        # --- Переменные прогресса тестирования ---
        self.test_log_line = ""
        self.test_is_running = False 
        self.test_progress = 0
        self.test_total = 1
        self.auto_start_after_test = False
        self.test_eta = ""
        self._test_config_times = []
        self._test_last_progress = 0
        self._test_last_config_time = 0
        self._test_start_time = 0
        # -----------------------------------------

        self.load_config()
        set_autorun(self.autorun_enabled)
        self.autorun_enabled = check_autorun()
        self._intro_start = time.time()
        self._intro_end = (self._intro_start + 2.4) if (self.intro_enabled and not self.minimal_mode) else 0.0

        self.update_state = "idle"
        self.remote_version = None
        self.update_available, self.is_updating = False, False
        self.mouse_x, self.mouse_y = 0, 0
        self.switch_snow_pos = 1.0 if self.snow_enabled else 0.0
        self.switch_style_pos = 1.0 if self.minimal_mode else 0.0
        self.switch_minimized_pos = 1.0 if self.start_minimized else 0.0
        self.switch_autorun_pos = 1.0 if self.autorun_enabled else 0.0
        self.switch_autorestart_pos = 1.0 if self.auto_restart else 0.0
        self.switch_proxy_pos = 1.0 if self.proxy_enabled else 0.0

        threading.Thread(target=self.run_startup_tasks, daemon=True).start()

        try:
            self.sound_start = self._load_sound_bytes(SOUND_START_FILE)
            self.sound_stop = self._load_sound_bytes(SOUND_STOP_FILE)
            self.synth_on = None if self.sound_start else AudioEngine.create_click_sound(150, 600, duration_ms=40, volume=0.3)
            self.synth_off = None if self.sound_stop else AudioEngine.create_click_sound(500, 100, duration_ms=60, volume=0.3)
        except Exception:
            self.sound_start = self.sound_stop = None
            self.synth_on, self.synth_off = None, None
        self.warp_particles = [WarpParticle() for _ in range(200)]
        self.snowflakes = [SnowFlake(WINDOW_WIDTH, WINDOW_HEIGHT) for _ in range(90)]
        self.current_warp_speed = 2.5
        self.viz_bars = [random.uniform(0.1, 0.8) for _ in range(8)]
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<MouseWheel>", self.on_scroll)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        self.update_idletasks()
        self.render_loop() 
        self.update() 
        
        # Тихий старт = только трей, НЕ в панели задач
        # Если тихий старт включён — сворачиваем и скрываем из задач
        if self.start_minimized:
            self.withdraw()
            self.attributes("-alpha", 1) 
        else:
            self.deiconify() 
            self.attributes("-alpha", 1) 
            self.lift()
            self.focus_force()

        self.after(2000, lambda: threading.Thread(target=self.check_for_updates, args=(True,), daemon=True).start())
        self.after(1000, lambda: threading.Thread(target=self.sys_monitor_loop, daemon=True).start())
        self.after(3000, lambda: threading.Thread(target=self.watchdog_loop, daemon=True).start())
        self.after(5000, lambda: threading.Thread(target=self.bypass_check_loop, daemon=True).start())
        self._load_stats()
        self.setup_tray()
        self.setup_hotkeys()
        self.after(50, self._pump_ui_queue)
        self.after(1200, self._init_taskbar)

    def setup_tray(self):
        try:
            icon_img = None
            try:
                if self.icon_path and os.path.exists(self.icon_path):
                    icon_img = Image.open(self.icon_path)
            except Exception: pass
            if not icon_img:
                icon_img = Image.new('RGB', (64, 64), color=(10, 11, 30))
                d = ImageDraw.Draw(icon_img)
                d.rectangle([16, 16, 48, 48], fill=(0, 255, 136))
            def on_show(icon, item):
                self.deiconify()
                self.attributes("-alpha", 1)
                self.lift()
                self.focus_force()
            def on_exit(icon, item):
                self.tray_icon.stop()
                try: self._save_stats()
                except Exception: pass
                self.stop_process_logic()
                self.destroy()
                os._exit(0)
            def on_toggle(icon, item):
                self.toggle_system()
            menu = pystray.Menu(
                pystray.MenuItem("Показать", on_show, default=True),
                pystray.MenuItem("Вкл / Выкл Обход", on_toggle),
                pystray.MenuItem("Выход", on_exit)
            )
            def _update_tray_title():
                """Обновляем tooltip трея со стратегией и аптаймом."""
                while True:
                    try:
                        if self.launcher_status == "ON":
                            el = int(time.time() - self.start_time)
                            strat_short = re.sub(r'[\(\)]', '', self.selected_bat.replace('.bat','').replace('general','').strip()) or 'Standard'
                            title = f"Zapret | {strat_short[:15]} | {el//3600:02}:{(el%3600)//60:02}:{el%60:02}"
                        elif self.proxy_status == "ON":
                            title = "Zapret | TgWsProxy ВКЛ"
                        else:
                            title = "Zapret Launcher"
                        if hasattr(self, 'tray_icon') and self.tray_icon:
                            self.tray_icon.title = title
                    except Exception: pass
                    time.sleep(1)
            threading.Thread(target=_update_tray_title, daemon=True).start()
            self.tray_icon = pystray.Icon("ZapretLauncher", icon_img, "Zapret Launcher", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            log_error(f"Tray setup error: {e}")

    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey("ctrl+shift+z", lambda: threading.Thread(target=self.toggle_system, daemon=True).start())
            keyboard.add_hotkey("ctrl+shift+c", lambda: self.ui_call(self.toggle_compact_mode))
        except Exception as e:
            log_error(f"Hotkey setup error: {e}")

    def run_startup_tasks(self):
        try:
            ensure_app_data()
            migrate_from_legacy_dir()
            cleanup_old_logs()
            migrate_old_files()
            self.cleanup_old_exe()
            self._ensure_payload()
            cleanup_old_zapret_folders()

            foreign = detect_foreign_dpi_tools()
            if foreign:
                log_error(f"Обнаружены другие DPI-инструменты: {', '.join(foreign)}")
                if self.notifications_enabled:
                    try: self.tray_icon.notify("Найдены другие DPI-утилиты: " + ", ".join(foreign), "Zapret Launcher")
                    except Exception: pass

            self.ui_call(self._refresh_bat_files)
            if getattr(self, 'is_first_run', False):
                self.ui_call(lambda: threading.Thread(target=self.run_service_tests, daemon=True).start())
            elif self.desired_bypass:
                self.ui_call(lambda: threading.Thread(target=self.start_process_logic, daemon=True).start())
        except Exception as e:
            log_error(f"Startup Tasks Error: {e}")

    def cleanup_old_exe(self):
        try:
            cleanup_stale_update_files()
            temp_dir = os.environ.get('TEMP', os.path.expanduser('~'))
            vbs_path = os.path.join(temp_dir, "updater.vbs")
            bat_path = os.path.join(temp_dir, "updater.bat")
            if os.path.exists(vbs_path):
                try: os.remove(vbs_path)
                except Exception: pass
            if os.path.exists(bat_path):
                try: os.remove(bat_path)
                except Exception: pass
                
            old_exe = os.path.abspath(sys.executable) + ".old"
            if os.path.exists(old_exe):
                try: os.remove(old_exe)
                except Exception: pass
        except Exception: pass

    def ui_call(self, fn, *args):
        """Потокобезопасная передача вызова в главный поток (Tk)."""
        try:
            self._ui_queue.put((fn, args))
        except Exception as e:
            log_error(f"ui_call error: {e}")

    def _pump_ui_queue(self):
        try:
            while True:
                fn, args = self._ui_queue.get_nowait()
                try:
                    fn(*args)
                except Exception as e:
                    log_error(f"UI task error: {e}")
        except queue.Empty:
            pass
        finally:
            self.after(50, self._pump_ui_queue)

    # ---------- 17.5: панель задач, OSD, самовосстановление ----------

    def _init_taskbar(self):
        if not self.taskbar_ui:
            return
        try:
            if self.taskbar is None:
                self.taskbar = win_taskbar.TaskbarIntegration(
                    self.winfo_id(), icon_dir=os.path.join(APP_DATA_DIR, "taskbar_icons"),
                    logger=log_error)
                if self.taskbar.enabled:
                    self.taskbar.register_button(1001, self._taskbar_toggle)
                    self.taskbar.register_button(1002, self._taskbar_run_tests)
                    self.taskbar.register_button(1003, self._taskbar_open_strategies)
                    self.taskbar.add_buttons(self._taskbar_buttons())
                    self._tb_last_status = None
                    self._sync_taskbar()
        except Exception as e:
            log_error(f"_init_taskbar error: {e}")

    def _apply_taskbar_setting(self):
        if self.taskbar_ui:
            self._init_taskbar()
        elif self.taskbar is not None:
            try:
                self.taskbar.close()
            except Exception:
                pass
            self.taskbar = None
            self._tb_last_status = None
            self._tb_last_progress = None

    def _taskbar_buttons(self):
        return [
            (1001, self.get_text("tb_toggle"), "power"),
            (1002, self.get_text("tb_tests"), "test"),
            (1003, self.get_text("tb_strategies"), "list"),
        ]

    def _sync_taskbar(self):
        """Статус/прогресс на панели задач (вызывается из render_loop)."""
        taskbar = getattr(self, "taskbar", None)
        if taskbar is None or not taskbar.enabled:
            return
        try:
            if not taskbar.buttons_added and self.winfo_viewable():
                now_ts = time.time()
                if now_ts - getattr(self, "_tb_buttons_retry", 0.0) > 10.0:
                    self._tb_buttons_retry = now_ts
                    taskbar.add_buttons(self._taskbar_buttons())
            if self.launcher_status != self._tb_last_status:
                self._tb_last_status = self.launcher_status
                taskbar.set_overlay(self.launcher_status)
            progress = None
            if self.is_updating and isinstance(self.update_state, str) and self.update_state.startswith("dl_"):
                try:
                    progress = (int(self.update_state[3:]), 100)
                except Exception:
                    progress = None
            elif self.launcher_status == "TESTING" and getattr(self, "test_total", 0):
                progress = (getattr(self, "test_progress", 0), self.test_total)
            if progress != self._tb_last_progress:
                self._tb_last_progress = progress
                if progress is None:
                    taskbar.set_progress(None)
                else:
                    taskbar.set_progress(progress[0], max(1, progress[1]))
        except Exception:
            pass

    def _taskbar_toggle(self):
        if self.launcher_status not in ("BUSY", "TESTING"):
            threading.Thread(target=self.toggle_system, daemon=True).start()

    def _taskbar_run_tests(self):
        if self.launcher_status != "TESTING":
            self.run_service_tests()

    def _taskbar_open_strategies(self):
        self.settings_open = True
        self.mode_menu_open = True
        self.menu_last_active = time.time()
        self._refresh_bat_files()

    def show_osd(self, text, color=None):
        """Короткое всплывающее уведомление внизу справа (по настройке OSD)."""
        if not self.osd_enabled or self.compact_mode:
            return
        try:
            win = tk.Toplevel(self)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.attributes("-alpha", 0.0)
            width, height = 240, 64
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            win.geometry(f"{width}x{height}+{sw-width-24}+{sh-height-64}")
            frame = tk.Frame(win, bg="#0e1124",
                             highlightbackground=(color or self.theme_color), highlightthickness=2)
            frame.pack(fill="both", expand=True)
            tk.Label(frame, text=text, bg="#0e1124", fg="white",
                     font=("Segoe UI", 11, "bold")).pack(expand=True)
            steps = 8

            def fade(step, direction):
                try:
                    alpha = step / steps if direction > 0 else 1.0 - step / steps
                    win.attributes("-alpha", max(0.0, min(1.0, alpha)))
                    if direction > 0 and step < steps:
                        win.after(25, lambda: fade(step + 1, 1))
                    elif direction > 0:
                        win.after(1300, lambda: fade(1, -1))
                    elif step < steps:
                        win.after(25, lambda: fade(step + 1, -1))
                    else:
                        win.destroy()
                except Exception:
                    try:
                        win.destroy()
                    except Exception:
                        pass

            fade(1, 1)
        except Exception as e:
            log_error(f"show_osd error: {e}")

    def _attempt_recovery(self, reason):
        """Лестница самовосстановления (watchdog/монитор деградации); check-then-act под lock."""
        try:
            now = time.time()
            action = next_recovery_step(reason, self._repair_attempts, self._repair_history, now)
            if not action:
                return
            if action == "notify":
                with self._repair_lock:
                    if self._repair_active:
                        return
                    self._repair_attempts.append("notify")
                log_incident("notify", "help_needed", level="error", details=reason)
                self.ui_call(self._notify_help_needed)
                return
            with self._repair_lock:
                if self._repair_active or getattr(self, "_builder_probe_active", False):
                    return
                self._repair_active = True
                self._repair_attempts.append(action)
                self._repair_history.append({"action": action, "ts": now})
            log_event("recovery", action=action, reason=reason)
            try:
                threading.Thread(target=self._run_recovery_action, args=(action, reason),
                                 daemon=True).start()
            except Exception as e:
                with self._repair_lock:
                    self._repair_active = False
                    if action in self._repair_attempts:
                        self._repair_attempts.remove(action)
                log_error(f"recovery thread start error: {e}")
        except Exception as e:
            with self._repair_lock:
                self._repair_active = False
            log_error(f"_attempt_recovery error: {e}")

    def _ensure_active_bat(self):
        """Закалка Immunity: активная стратегия существует в актуальном пакете, иначе — первая доступная."""
        try:
            self.zapret_dir = locate_zapret_dir()
            self._refresh_bat_files()
        except Exception as e:
            log_error(f"_ensure_active_bat refresh error: {e}")
        if not self.selected_bat or self.selected_bat not in self.bat_files:
            self.selected_bat = self.bat_files[0] if self.bat_files else self.selected_bat
            self.save_config()
        if self.selected_bat:
            return os.path.join(self.zapret_dir, self.selected_bat)
        return ""

    def _run_recovery_action(self, action, reason):
        result = "failed"
        try:
            self.launcher_status = "BUSY"
            self.status_text = self.get_text("status_busy")
            bat_path = self._ensure_active_bat()
            if action == "rotate":
                target = pick_rotation_target(self.selected_bat, self.favorite_bat,
                                              self.bat_files, getattr(self, "scores", {}) or {})
                if target and target != self.selected_bat:
                    self.selected_bat = target
                    bat_path = os.path.join(self.zapret_dir, target)
                    self.save_config()
                    self.ui_call(self._refresh_bat_files)
                    result = "ok" if install_zapret_service(self.zapret_dir, bat_path) else "failed"
                else:
                    result = "skipped"
            elif action == "restart":
                result = "ok" if install_zapret_service(self.zapret_dir, bat_path) else "failed"
            elif action == "recreate":
                stop_services_and_processes()
                time.sleep(1)
                result = "ok" if install_zapret_service(self.zapret_dir, bat_path) else "failed"
            elif action == "repack":
                stop_services_and_processes()
                time.sleep(0.5)
                repacked, _message = repack_payload()
                bat_path = self._ensure_active_bat()
                result = "ok" if (repacked and bat_path
                                  and install_zapret_service(self.zapret_dir, bat_path)) else "failed"
            if result == "ok" and winws_health_ok():
                self.launcher_status, self.start_time = "ON", time.time()
                self.status_text = self.get_text("status_on")
                self.desired_bypass = True
                self._repair_attempts = []
                log_incident(action, "ok", level="info", details=reason)
                self.ui_call(self.show_osd, self.get_text("heal_fixed"), "#22c55e")
            elif result == "skipped":
                log_incident(action, "skipped", level="warn", details=reason)
            else:
                result = "failed"
                log_incident(action, "failed", level="warn", details=reason)
        except Exception as e:
            log_incident(action, "error", level="error", details=str(e))
        finally:
            if self.launcher_status == "BUSY" and self.desired_bypass:
                self.launcher_status = "ON"
                self.status_text = self.get_text("status_on")
            with self._repair_lock:
                self._repair_active = False
            self._update_discord(force=True)

    def _notify_help_needed(self):
        self.launcher_status = "OFF"
        self.status_text = self.get_text("status_error")
        self._update_discord(force=True)
        if self.notifications_enabled:
            try:
                self.tray_icon.notify(self.get_text("heal_help"), "Zapret Launcher")
            except Exception:
                pass
        if self.taskbar is not None:
            self.taskbar.flash_error()

    def _degrade_check(self):
        """Пробы при включённой авто-ротации: 3 подряд низких — ротация стратегии."""
        try:
            score = score_probe_results(probe_services(timeout=2.0))
            if score < 0.5:
                self._degrade_streak += 1
                log_event("rotate_degraded", score=round(score, 3), streak=self._degrade_streak)
                if self._degrade_streak >= 3:
                    self._degrade_streak = 0
                    self._attempt_recovery("degraded")
            else:
                self._degrade_streak = 0
        except Exception as e:
            log_error(f"_degrade_check error: {e}")
        finally:
            self._degrade_running = False

    # ---------- 17.5: окна «Дополнительно», «Журнал», «Конструктор» ----------

    def open_more_settings(self):
        if getattr(self, "_more_win", None) is not None and self._more_win.winfo_exists():
            self._more_win.lift()
            return
        self.play_sound("ON")
        win = ctk.CTkToplevel(self)
        self._more_win = win
        win.title(self.get_text("more_title"))
        win.geometry("380x340")
        win.configure(fg_color="#0a0b1e")
        win.transient(self)
        ctk.CTkLabel(win, text=self.get_text("more_title"),
                     font=("Segoe UI", 16, "bold")).pack(pady=(18, 12))

        def add_switch(label_key, attr, command=None):
            var = tk.BooleanVar(value=bool(getattr(self, attr)))

            def on_toggle():
                setattr(self, attr, bool(var.get()))
                self.save_config()
                self.play_sound("ON" if var.get() else "OFF")
                if command:
                    command()

            ctk.CTkSwitch(win, text=self.get_text(label_key), variable=var, command=on_toggle,
                          progress_color=self.theme_color, font=("Segoe UI", 12)).pack(anchor="w",
                                                                                      padx=28, pady=7)

        add_switch("taskbar_lbl", "taskbar_ui", self._apply_taskbar_setting)
        add_switch("osd_lbl", "osd_enabled")
        add_switch("self_heal_lbl", "self_heal")
        add_switch("auto_rotate_lbl", "auto_rotate")

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(pady=16)
        ctk.CTkButton(btns, text=self.get_text("inc_open"), command=self.open_incidents_window,
                      fg_color="#15182e", hover_color="#1a1e3d", width=150).pack(side="left", padx=6)
        ctk.CTkButton(btns, text=self.get_text("builder_open"), command=self.open_builder_window,
                      fg_color="#15182e", hover_color="#1a1e3d", width=170).pack(side="left", padx=6)

    def open_incidents_window(self):
        if getattr(self, "_inc_win", None) is not None and self._inc_win.winfo_exists():
            self._inc_win.lift()
            self._refresh_incidents_view()
            return
        self.play_sound("ON")
        win = ctk.CTkToplevel(self)
        self._inc_win = win
        win.title(self.get_text("inc_title"))
        win.geometry("560x430")
        win.configure(fg_color="#0a0b1e")
        win.transient(self)
        self._inc_text = ctk.CTkTextbox(win, fg_color="#0e1124", text_color="#d7d9e5",
                                        font=("Consolas", 11))
        self._inc_text.pack(fill="both", expand=True, padx=14, pady=(14, 8))
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(pady=(0, 12))
        ctk.CTkButton(row, text=self.get_text("inc_refresh"), command=self._refresh_incidents_view,
                      fg_color="#15182e", hover_color="#1a1e3d", width=110).pack(side="left", padx=6)
        ctk.CTkButton(row, text=self.get_text("inc_copy"), command=self._copy_incidents,
                      fg_color="#15182e", hover_color="#1a1e3d", width=110).pack(side="left", padx=6)
        ctk.CTkButton(row, text=self.get_text("btn_close"), command=win.destroy,
                      fg_color="#15182e", hover_color="#1a1e3d", width=110).pack(side="left", padx=6)
        self._refresh_incidents_view()

    def _format_incidents(self):
        items = read_incidents(60)
        if not items:
            return self.get_text("inc_empty")
        lines = []
        for item in reversed(items):
            stamp = item.get("time") or time.strftime("%Y-%m-%d %H:%M:%S",
                                                      time.localtime(float(item.get("ts", 0) or 0)))
            line = f"[{stamp}] {str(item.get('level', '?')).upper():5} {item.get('action', '?')} → {item.get('result', '')}"
            if item.get("details"):
                line += f"  ({item.get('details')})"
            lines.append(line)
        return "\n".join(lines)

    def _refresh_incidents_view(self):
        try:
            self._inc_text.configure(state="normal")
            self._inc_text.delete("1.0", "end")
            self._inc_text.insert("1.0", self._format_incidents())
            self._inc_text.configure(state="disabled")
        except Exception as e:
            log_error(f"_refresh_incidents_view error: {e}")

    def _copy_incidents(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self._format_incidents())
            self.play_sound("ON")
        except Exception:
            pass

    def open_builder_window(self):
        if getattr(self, "_builder_win", None) is not None and self._builder_win.winfo_exists():
            self._builder_win.lift()
            return
        self.play_sound("ON")
        self._refresh_bat_files()
        win = ctk.CTkToplevel(self)
        self._builder_win = win
        win.title(self.get_text("builder_open"))
        win.geometry("880x640")
        win.configure(fg_color="#0a0b1e")
        win.transient(self)
        self._builder_segments = []
        self._builder_widgets = []
        self._builder_testing = False

        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(top, text=self.get_text("sb_base"), font=("Segoe UI", 12, "bold")).pack(side="left")
        self._builder_base = ctk.StringVar(
            value=self.selected_bat or (self.bat_files[0] if self.bat_files else ""))
        ctk.CTkOptionMenu(top, values=self.bat_files or [""], variable=self._builder_base,
                          fg_color="#15182e", button_color="#2a305e", width=280).pack(side="left", padx=10)
        ctk.CTkButton(top, text=self.get_text("sb_load"), command=self._builder_load,
                      fg_color="#1a3328", hover_color="#224433", width=110).pack(side="left", padx=6)
        ctk.CTkButton(top, text=self.get_text("sb_import"), command=self._builder_import,
                      fg_color="#15182e", hover_color="#1a1e3d", width=90).pack(side="right", padx=4)

        self._builder_body = ctk.CTkScrollableFrame(win, fg_color="#080914")
        self._builder_body.pack(fill="both", expand=True, padx=14, pady=8)

        bottom = ctk.CTkFrame(win, fg_color="transparent")
        bottom.pack(fill="x", padx=14, pady=(4, 4))
        ctk.CTkLabel(bottom, text=self.get_text("sb_name")).pack(side="left")
        self._builder_name = ctk.CTkEntry(bottom, width=190, fg_color="#0e1124")
        self._builder_name.pack(side="left", padx=8)
        ctk.CTkButton(bottom, text=self.get_text("sb_test"), command=self._builder_test,
                      fg_color="#3a2f10", hover_color="#4a3d16", width=130).pack(side="left", padx=6)
        ctk.CTkButton(bottom, text=self.get_text("sb_save"), command=self._builder_save,
                      fg_color="#1a3328", hover_color="#224433", width=160).pack(side="left", padx=6)
        ctk.CTkButton(bottom, text=self.get_text("sb_export"), command=self._builder_export,
                      fg_color="#15182e", hover_color="#1a1e3d", width=90).pack(side="left", padx=6)
        self._builder_status = ctk.CTkLabel(win, text="", font=("Consolas", 11), text_color="#9aa0b5")
        self._builder_status.pack(pady=(0, 8))

        self._builder_load()

    def _builder_set_status(self, text, color="#9aa0b5"):
        try:
            self._builder_status.configure(text=text, text_color=color)
        except Exception:
            pass

    def _builder_load(self):
        name = self._builder_base.get()
        bat_path = os.path.join(self.zapret_dir, name)
        if not os.path.exists(bat_path):
            self._builder_set_status(self.get_text("status_no_file"), "#ef4444")
            return
        args = strategy_builder.load_strategy_args(bat_path, self.zapret_dir)
        self._builder_segments = strategy_builder.parse_args(args)
        if not self._builder_segments:
            self._builder_set_status(self.get_text("status_error"), "#ef4444")
            return
        self._builder_name.set(strategy_builder.normalize_name(os.path.splitext(name)[0]))
        self._builder_render()
        self._builder_set_status("", "")

    def _builder_render(self):
        for child in self._builder_body.winfo_children():
            child.destroy()
        self._builder_widgets = []
        for seg_index, segment in enumerate(self._builder_segments):
            header = self.get_text("sb_global") if seg_index == 0 else f"{self.get_text('sb_profile')} {seg_index + 1}"
            frame = ctk.CTkFrame(self._builder_body, fg_color="#0e1124")
            frame.pack(fill="x", pady=4)
            ctk.CTkLabel(frame, text=f"{header} · {segment.summary()}",
                         font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x", padx=10, pady=(8, 2))
            for opt_index, option in enumerate(segment.options):
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=1)
                ctk.CTkLabel(row, text=option.flag, width=280, anchor="w",
                             font=("Consolas", 10), text_color="#9aa0b5").pack(side="left")
                entry = ctk.CTkEntry(row, fg_color="#15182e", font=("Consolas", 10))
                if option.value is not None:
                    entry.insert(0, option.value)
                entry.pack(side="left", fill="x", expand=True, padx=6)
                self._builder_widgets.append((seg_index, opt_index, entry))
                ctk.CTkButton(row, text="✕", width=30, fg_color="#2a1520", hover_color="#3a1c2a",
                              command=lambda s=seg_index, o=opt_index: self._builder_remove(s, o)).pack(side="left")
            add_row = ctk.CTkFrame(frame, fg_color="transparent")
            add_row.pack(fill="x", padx=10, pady=(2, 8))
            used = {opt.flag.lower() for opt in segment.options}
            flags = [flag for flag in strategy_builder.EDITABLE_ORDER
                     if flag not in used or strategy_builder.KNOWN_FLAGS[flag].get("multi")]
            pick = ctk.StringVar(value=flags[0] if flags else "")
            ctk.CTkOptionMenu(add_row, values=flags or [""], variable=pick, width=280,
                              fg_color="#15182e", button_color="#2a305e").pack(side="left")
            ctk.CTkButton(add_row, text=self.get_text("sb_add"), width=90, fg_color="#15182e",
                          hover_color="#1a1e3d",
                          command=lambda s=seg_index, v=pick: self._builder_add(s, v.get())).pack(side="left", padx=6)

    def _builder_collect(self):
        try:
            for seg_index, opt_index, entry in self._builder_widgets:
                value = entry.get().strip()
                self._builder_segments[seg_index].options[opt_index].value = value if value else None
            return True
        except Exception as e:
            log_error(f"_builder_collect error: {e}")
            return False

    def _builder_args(self):
        self._builder_collect()
        return strategy_builder.serialize_args(self._builder_segments)

    def _builder_add(self, seg_index, flag):
        if not flag:
            return
        self._builder_collect()
        self._builder_segments[seg_index].options.append(strategy_builder.Option(flag, "", True))
        self._builder_render()

    def _builder_remove(self, seg_index, opt_index):
        self._builder_collect()
        try:
            del self._builder_segments[seg_index].options[opt_index]
            self._builder_render()
        except Exception:
            pass

    def _builder_save(self):
        args = self._builder_args()
        name = self._builder_name.get().strip()
        normalized = strategy_builder.normalize_name(name)
        bat_path = os.path.join(self.zapret_dir, strategy_builder.CUSTOM_PREFIX + normalized + ".bat")
        overwrite = True
        if os.path.exists(bat_path):
            overwrite = messagebox.askyesno(self.get_text("builder_open"),
                                            self.get_text("sb_overwrite").replace("{name}", normalized))
        result = strategy_builder.save_custom_strategy(self.zapret_dir, name, args,
                                                       title=name, overwrite=overwrite)
        if result.get("ok"):
            self._refresh_bat_files()
            self._builder_set_status(
                self.get_text("sb_saved").replace("{name}", result.get("bat", name)), "#22c55e")
            self.play_sound("ON")
        else:
            self._builder_set_status(
                self.get_text("sb_error").replace("{error}", str(result.get("error"))), "#ef4444")

    def _builder_test(self):
        if getattr(self, "_builder_testing", False):
            return
        if (self.launcher_status in ("TESTING", "BUSY") or getattr(self, "_repair_active", False)
                or getattr(self, "test_is_running", False)):
            self._builder_set_status(self.get_text("sb_busy"), "#eab308")
            return
        args = self._builder_args()
        errors = strategy_builder.validate_args(args)
        if errors:
            self._builder_set_status(
                self.get_text("sb_error").replace("{error}", str(errors[0].get("error"))), "#ef4444")
            return
        if not messagebox.askyesno(self.get_text("builder_open"), self.get_text("sb_test_warn")):
            return
        self._builder_testing = True
        self._builder_set_status(self.get_text("sb_testing"), "#eab308")
        restore = os.path.join(self.zapret_dir, self.selected_bat) if self.selected_bat else None
        previous_status = self.launcher_status

        def worker():
            result = {"ok": False, "score": 0.0, "restored": None}
            self._builder_probe_active = True
            self.ui_call(self._set_probe_status, True)
            try:
                result = run_custom_strategy_probe(self.zapret_dir, args,
                                                   restore_bat_path=restore, seconds=12.0)
            except Exception as e:
                log_error(f"builder probe error: {e}")
            finally:
                self._builder_probe_active = False
                self.ui_call(self._set_probe_status, False, previous_status,
                             bool(result.get("restored")))
            try:
                text = self.get_text("sb_score").replace("{score}", f"{result.get('score', 0.0):.0%}")
                if result.get("restored"):
                    text += " · " + self.get_text("sb_restored")
                color = "#22c55e" if result.get("score", 0.0) >= 0.5 else "#ef4444"
                self.ui_call(self._builder_set_status, text, color)
            finally:
                self._builder_testing = False

        threading.Thread(target=worker, daemon=True).start()

    def _set_probe_status(self, active, previous_status=None, restored=False):
        """На время проверки в конструкторе — TESTING (watchdog/ротация не вмешиваются)."""
        if active:
            self.launcher_status = "TESTING"
            self.status_text = self.get_text("sb_testing")
        elif previous_status == "ON":
            healthy = bool(restored) or winws_health_ok()
            self.launcher_status = "ON"
            self.status_text = self.get_text("status_on" if healthy else "status_error")
            if not healthy:
                log_incident("probe_restore", "service_down", level="warn", details="builder probe")
                threading.Thread(target=self._attempt_recovery, args=("service_down",),
                                 daemon=True).start()
        else:
            self.launcher_status = previous_status or "OFF"
            self.status_text = self.get_text("status_ready")
        self._update_discord(force=True)

    def _builder_export(self):
        custom = strategy_builder.list_custom_strategies(self.zapret_dir)
        if not custom:
            self._builder_set_status(
                self.get_text("sb_error").replace("{error}", self.get_text("sb_no_custom")), "#ef4444")
            return
        target_name = self._builder_name.get().strip()
        chosen = next((item for item in custom
                       if item["bat"].lower() == (strategy_builder.CUSTOM_PREFIX + target_name + ".bat").lower()),
                      custom[0])
        target = filedialog.asksaveasfilename(parent=self._builder_win, defaultextension=".zip",
                                              filetypes=[("Zip", "*.zip")],
                                              initialfile=os.path.splitext(chosen["bat"])[0] + ".zip")
        if not target:
            return
        result = strategy_builder.export_custom_strategy(self.zapret_dir, chosen["bat"], target)
        if result.get("ok"):
            self._builder_set_status(self.get_text("sb_exported").replace("{name}", chosen["bat"]), "#22c55e")
        else:
            self._builder_set_status(
                self.get_text("sb_error").replace("{error}", str(result.get("error"))), "#ef4444")

    def _builder_import(self):
        source = filedialog.askopenfilename(parent=self._builder_win, filetypes=[("Zip", "*.zip")])
        if not source:
            return
        result = strategy_builder.import_custom_strategy(self.zapret_dir, source)
        if result.get("ok"):
            self._refresh_bat_files()
            self._builder_set_status(
                self.get_text("sb_saved").replace("{name}", result.get("bat", "")), "#22c55e")
        else:
            self._builder_set_status(
                self.get_text("sb_error").replace("{error}", str(result.get("error"))), "#ef4444")

    def s(self, v): return v * self.ui_scale
    def fs(self, size): return max(8, int(size * self.ui_scale))

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.attributes("-fullscreen", self.fullscreen)

    def quit_fullscreen(self, event=None):
        self.fullscreen = False
        self.attributes("-fullscreen", False)

    def _refresh_bat_files(self):
        try:
            self.zapret_dir = locate_zapret_dir()
            if self.zapret_dir and os.path.exists(self.zapret_dir):
                files = [f for f in os.listdir(self.zapret_dir) if is_strategy_bat(f)]
                if files:
                    files.sort()
                    self.bat_files = files
                    if self.selected_bat not in self.bat_files:
                        self.selected_bat = self.bat_files[0]
        except Exception as e:
            log_error(f"_refresh_bat_files error: {e}")

    def sys_monitor_loop(self):
        ping_counter = 0
        while True:
            try:
                self.hud_values["CPU"] = f"{int(psutil.cpu_percent(interval=None))}"
                self.hud_values["RAM"] = f"{int(psutil.virtual_memory().percent)}"
            except Exception as e:
                log_error(f"Sys monitor loop error: {e}")
                self.hud_values["CPU"] = "0"
            # Пинг обновляем раз в 15 секунд — не грузим сеть
            ping_counter += 1
            if ping_counter >= 15:
                ping_counter = 0
                try:
                    ms = tcp_connect_ms("8.8.8.8", 443, timeout=1.0)
                    self.hud_values["PING"] = f"{ms}ms" if ms >= 0 else "---"
                except Exception:
                    self.hud_values["PING"] = "---"
            time.sleep(1)

    def watchdog_loop(self):
        """Следит за состоянием службы winws.exe (SCM + процесс)."""
        fail_streak = 0
        restart_attempts = 0
        restart_window_start = 0.0
        while getattr(self, '_watchdog_running', True):
            try:
                if self.launcher_status == "ON":
                    if winws_health_ok():
                        fail_streak = 0
                        self._total_uptime_sec += 5
                        self._stats_dirty = True
                        self._maybe_save_stats()
                        if self._repair_attempts:
                            self._repair_attempts = []
                        if self.auto_rotate and not self._degrade_running:
                            self._degrade_counter += 1
                            if self._degrade_counter >= 12:
                                self._degrade_counter = 0
                                self._degrade_running = True
                                try:
                                    threading.Thread(target=self._degrade_check, daemon=True).start()
                                except Exception as e:
                                    self._degrade_running = False
                                    log_error(f"degrade thread start error: {e}")
                    else:
                        fail_streak += 1
                        if fail_streak < 2:
                            log_error(f"Watchdog: winws.exe не найден (проверка {fail_streak}/2)")
                        elif self.self_heal:
                            log_error(f"Watchdog: служба упала (SCM={service_state('zapret')}), самовосстановление")
                            self._attempt_recovery("service_down")
                            fail_streak = 0
                        else:
                            log_error(f"Watchdog: служба упала (SCM={service_state('zapret')})")
                            if getattr(self, 'auto_restart', False):
                                now = time.time()
                                if now - restart_window_start > 300:
                                    restart_window_start = now
                                    restart_attempts = 0
                                if restart_attempts < 3:
                                    restart_attempts += 1
                                    log_error(f"Watchdog: auto-restart, попытка {restart_attempts}/3")
                                    self.launcher_status = "BUSY"
                                    threading.Thread(target=self.start_process_logic, daemon=True).start()
                                else:
                                    log_error("Watchdog: лимит перезапусков исчерпан")
                                    self.launcher_status = "OFF"
                                    self.status_text = self.get_text("status_error")
                                    if self.notifications_enabled:
                                        try: self.tray_icon.notify("Обход не запускается — проверьте стратегию", "Zapret Launcher")
                                        except Exception: pass
                            else:
                                self.launcher_status = "OFF"
                                self.status_text = self.get_text("status_ready")
                                if self.notifications_enabled:
                                    try: self.tray_icon.notify("Обход упал!", "Zapret Launcher")
                                    except Exception: pass
                            fail_streak = 0
                else:
                    fail_streak = 0

                if self.proxy_status == "ON" and self._proxy_process and self._proxy_process.poll() is not None:
                    log_error("Proxy watchdog: TgWsProxy завершился")
                    self.proxy_status = "OFF"
                    self._proxy_process = None
            except Exception as e:
                log_error(f"Watchdog error: {e}")
            time.sleep(5)

    def bypass_check_loop(self):
        """Периодически проверяет работает ли обход: TCP-подключение к discord.com:443."""
        while True:
            try:
                if self.launcher_status == "ON":
                    ms = tcp_connect_ms("discord.com", 443, timeout=2.0)
                    self._bypass_check = "OK" if ms >= 0 else "FAIL"
                else:
                    self._bypass_check = "---"
            except Exception:
                self._bypass_check = "---"
            time.sleep(30)

    def _load_stats(self):
        try:
            stats_path = os.path.join(APP_DATA_DIR, "stats.json")
            if os.path.exists(stats_path):
                with open(stats_path, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    self._total_uptime_sec = d.get("uptime_sec", 0)
                    self._launch_count = d.get("launches", 0)
        except Exception: pass

    def _save_stats(self):
        try:
            ensure_app_data()
            stats_path = os.path.join(APP_DATA_DIR, "stats.json")
            temp_path = stats_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump({"uptime_sec": self._total_uptime_sec, "launches": self._launch_count}, f)
            os.replace(temp_path, stats_path)
            self._stats_dirty = False
        except Exception: pass

    def _maybe_save_stats(self, force=False):
        now = time.time()
        if not force and (not self._stats_dirty or now - self._stats_last_save < 60):
            return
        self._stats_last_save = now
        self._save_stats()

    # --- TgWsProxy методы ---
    def start_proxy(self):
        try:
            # Убиваем старые зависшие процессы прокси, чтобы освободить порт
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.call(["taskkill", "/F", "/IM", TGWS_PROXY_EXE], startupinfo=si, creationflags=0x08000000)
            time.sleep(0.3)

            self.zapret_dir = locate_zapret_dir()
            # Ищем исполняемый файл прокси во всех возможных местах
            proxy_exe = ""
            search_dirs = [
                self.zapret_dir,
                os.path.join(self.zapret_dir, "bin"),
                os.path.join(APP_DATA_DIR, "zapret_data", FOLDER_NAME),
                os.path.join(APP_DATA_DIR, "zapret_data", FOLDER_NAME, "bin"),
                os.path.join(APP_DATA_DIR, FOLDER_NAME),
                os.path.join(APP_DATA_DIR, FOLDER_NAME, "bin"),
                APP_DATA_DIR,
                EXE_DIR,
                os.path.join(EXE_DIR, "zapret_data", FOLDER_NAME),
                os.path.join(EXE_DIR, "zapret_data", FOLDER_NAME, "bin"),
            ]
            for d in search_dirs:
                candidate = os.path.join(d, TGWS_PROXY_EXE)
                if os.path.exists(candidate):
                    proxy_exe = candidate
                    break
            if not proxy_exe:
                log_error(f"TgWsProxy: файл '{TGWS_PROXY_EXE}' не найден ни в одном из путей")
                self.proxy_status = "OFF"
                return

            self._proxy_process = subprocess.Popen(
                [proxy_exe], cwd=os.path.dirname(proxy_exe), startupinfo=si,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            time.sleep(0.5)
            if self._proxy_process.poll() is not None:
                log_error(f"TgWsProxy мгновенно завершился с кодом {self._proxy_process.poll()}")
                self.proxy_status = "OFF"
                self._proxy_process = None
                return

            self.proxy_status = "ON"
            log_error(f"TgWsProxy запущен: {proxy_exe}")
            if self.notifications_enabled:
                try: self.tray_icon.notify("TgWsProxy включён", "Zapret Launcher")
                except Exception: pass
        except Exception as e:
            log_error(f"TgWsProxy start error: {e}")
            self.proxy_status = "OFF"

    def stop_proxy(self):
        try:
            if self._proxy_process and self._proxy_process.poll() is None:
                self._proxy_process.terminate()
                self._proxy_process = None
            # Дополнительно убиваем по имени если запустили внешне
            # Важно: /IM принимает имя без кавычек
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = subprocess.SW_HIDE
            subprocess.call(["taskkill", "/F", "/IM", TGWS_PROXY_EXE], startupinfo=si, creationflags=0x08000000)
            self.proxy_status = "OFF"
            log_error("TgWsProxy остановлен")
        except Exception as e:
            log_error(f"TgWsProxy stop error: {e}")

    def toggle_proxy(self):
        if self.proxy_status == "ON":
            self.stop_proxy()
            self.play_sound("OFF")
        else:
            threading.Thread(target=self.start_proxy, daemon=True).start()
            self.play_sound("ON")

    def export_config(self):
        """Export config to user-chosen location."""
        try:
            import tkinter.filedialog as fd
            path = fd.asksaveasfilename(
                title="Сохранить конфиг",
                defaultextension=".json",
                filetypes=[("JSON", "*.json")],
                initialfile="zapret_config.json"
            )
            if path:
                shutil.copy2(CONFIG_PATH, path)
                self.play_sound("ON")
                log_error(f"Конфиг экспортирован: {path}")
        except Exception as e:
            log_error(f"Export config error: {e}")

    def import_config(self):
        """Import config from user-chosen file."""
        try:
            import tkinter.filedialog as fd
            path = fd.askopenfilename(
                title="Загрузить конфиг",
                filetypes=[("JSON", "*.json")]
            )
            if path:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Проверяем что это валидный конфиг (не посторонний файл)
                if "snow" in data or "bat" in data or "theme" in data:
                    shutil.copy2(path, CONFIG_PATH)
                    self.load_config()
                    self.play_sound("ON")
                    log_error(f"Конфиг импортирован: {path}")
        except Exception as e:
            log_error(f"Import config error: {e}")

    def toggle_compact_mode(self):
        """Мини-оверлей: маленькое окно поверх всех (выход — клик по нему или Ctrl+Shift+C)."""
        self.compact_mode = not self.compact_mode
        self.play_sound("ON" if self.compact_mode else "OFF")
        if self.compact_mode:
            self.attributes("-topmost", True)
            self.resizable(False, False)
            self.geometry("220x50")
            self.deiconify()
            self.lift()
        else:
            self.attributes("-topmost", False)
            self.resizable(True, True)
            ws = self.winfo_screenwidth()
            self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{(ws - WINDOW_WIDTH)//2}+{(self.winfo_screenheight()-WINDOW_HEIGHT)//2}")
            self.deiconify()
            self.lift()

    def _ensure_payload(self):
        """Гарантирует полный пакет; распаковка bundled zip при неполном/старом (core.ensure_payload)."""
        self.zapret_dir = ensure_payload()
        self._refresh_bat_files()
        return payload_complete(self.zapret_dir)

    def get_text(self, key):
        lang_dict = self.translations_data.get(self.current_lang, self.translations_data["EN"])
        return lang_dict.get(key, key)

    def load_config(self):
        self.is_first_run = not os.path.exists(CONFIG_PATH)
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.snow_enabled = data.get("snow", True)
                    self.minimal_mode = data.get("minimal", False)
                    self.start_minimized = data.get("minimized", False)
                    self.auto_repair = data.get("repair", False)
                    self.auto_restart = data.get("auto_restart", True)
                    self.taskbar_ui = bool(data.get("taskbar_ui", True))
                    self.osd_enabled = bool(data.get("osd", True))
                    self.self_heal = bool(data.get("self_heal", True))
                    self.auto_rotate = bool(data.get("auto_rotate", False))
                    self.desired_bypass = data.get("desired_bypass", True)
                    self.proxy_enabled = data.get("proxy_enabled", False)
                    self.notifications_enabled = data.get("notifications", True)
                    self.autorun_enabled = data.get("autorun", True)
                    self.theme_name = data.get("theme", DEFAULT_THEME)
                    self.theme_color = self.themes_data.get(self.theme_name, self.themes_data[DEFAULT_THEME])
                    self.selected_bat = data.get("bat", self.bat_files[0] if self.bat_files else DEFAULT_BAT)
                    self.favorite_bat = data.get("fav", None)
                    self.current_lang = data.get("lang", "RU")
                    self.discord_rpc = bool(data.get("discord_rpc", False))
                    self.intro_enabled = bool(data.get("intro", True))
                    self.discord_client_id = str(data.get("discord_client_id", "") or "")
                    try:
                        self.idle_hide_min = max(0, min(240, int(data.get("idle_hide_min", 0) or 0)))
                    except Exception:
                        self.idle_hide_min = 0
                    if int(data.get("schema_version", 1) or 1) < CONFIG_SCHEMA_VERSION:
                        self.save_config()
        except Exception as e:
            log_error(f"Load config error: {e}")
        self._apply_discord_setting()

    def _apply_discord_setting(self):
        """G12: включить/выключить presence по настройке (тихий no-op без client_id/pypresence)."""
        try:
            client_id = (self.discord_client_id or discord_client_id()).strip()
            if self.discord_rpc and discord_rpc.PYPRESENCE_AVAILABLE and client_id:
                if self.discord is None:
                    self.discord = discord_rpc.DiscordPresence(client_id)
                self._update_discord(force=True)
            elif self.discord is not None:
                self.discord.close()
                self.discord = None
        except Exception:
            pass

    def _update_discord(self, force=False):
        try:
            if self.discord is None:
                return
            payload = discord_payload(self.launcher_status, self.selected_bat,
                                      self.start_time, self.current_lang)
            self.discord.update(**payload, force=force)
        except Exception:
            pass

    def save_config(self):
        try:
            ensure_app_data()
            data = {}
            if os.path.exists(CONFIG_PATH):
                try:
                    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data.update({
                "schema_version": CONFIG_SCHEMA_VERSION,
                "snow": self.snow_enabled,
                "minimal": self.minimal_mode,
                "minimized": self.start_minimized,
                "repair": self.auto_repair,
                "auto_restart": self.auto_restart,
                "taskbar_ui": self.taskbar_ui,
                "osd": self.osd_enabled,
                "self_heal": self.self_heal,
                "auto_rotate": self.auto_rotate,
                "desired_bypass": self.desired_bypass,
                "proxy_enabled": self.proxy_enabled,
                "notifications": self.notifications_enabled,
                "autorun": self.autorun_enabled,
                "theme": self.theme_name,
                "bat": self.selected_bat,
                "fav": self.favorite_bat,
                "lang": self.current_lang,
                "idle_hide_min": self.idle_hide_min,
                "discord_rpc": self.discord_rpc,
                "intro": self.intro_enabled,
                "discord_client_id": self.discord_client_id
            })
            temp_path = CONFIG_PATH + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, CONFIG_PATH)
        except Exception as e:
            log_error(f"Save config error: {e}")

    def _load_sound_bytes(self, relative_path):
        try:
            path = resource_path(relative_path)
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return f.read()
        except Exception as e:
            log_error(f"Sound load error ({relative_path}): {e}")
        return None

    def play_sound(self, effect_type):
        def _play():
            try:
                sound = self.sound_start if effect_type == "ON" else self.sound_stop
                if not sound:
                    sound = self.synth_on if effect_type == "ON" else self.synth_off
                if sound:
                    winsound.PlaySound(sound, winsound.SND_MEMORY)
            except Exception: pass
        threading.Thread(target=_play, daemon=True).start()

    def toggle_profile(self):
        self._profile = not self._profile
        if self._profile:
            try:
                self._proc = psutil.Process()
                self._proc.cpu_percent(None)
            except Exception:
                self._proc = None
        self.play_sound("ON" if self._profile else "OFF")

    def run_service_tests(self):
        # Ищем ps1 скрипт в папке utils
        ps1_path = os.path.join(self.zapret_dir, "utils", "test zapret.ps1")
        if not os.path.exists(ps1_path):
            log_error(f"Test script not found: {ps1_path}")
            self.status_text = "НЕТ СКРИПТА"
            return

        # Останавливаем службу если она запущена (PS-скрипт не работает с активной службой)
        if self.launcher_status == "ON":
            self.stop_process_logic()
            time.sleep(1)

        self.play_sound("ON")
        self.launcher_status = "TESTING"
        self._update_discord(force=True)
        self.test_is_running = True

        self.test_progress = 0
        self.test_total = len(self.bat_files) if self.bat_files else 1
        self.auto_start_after_test = False
        self.test_log_line = "Запуск PowerShell..."
        self.test_eta = ""
        self._test_config_times = []
        self._test_last_progress = 0
        self._test_last_config_time = time.time()
        self._test_start_time = time.time()

        def on_test_line(clean_line):
            self.test_log_line = clean_line

            progress_match = re.search(r'\[(\d+)/(\d+)\]', clean_line)
            if progress_match:
                new_progress = int(progress_match.group(1))
                new_total = int(progress_match.group(2))
                self.test_total = new_total

                if new_progress > self._test_last_progress:
                    now = time.time()
                    if self._test_last_progress > 0:
                        self._test_config_times.append(now - self._test_last_config_time)
                    self._test_last_config_time = now
                    self._test_last_progress = new_progress
                    self.test_progress = new_progress

                    if self._test_config_times:
                        avg_time = sum(self._test_config_times) / len(self._test_config_times)
                        remaining = (new_total - new_progress) * avg_time
                        if remaining > 60:
                            self.test_eta = f"~{int(remaining//60)}м {int(remaining%60)}с"
                        else:
                            self.test_eta = f"~{int(remaining)}с"

        def background_worker():
            best_config = run_strategy_tests(
                self.zapret_dir, on_line=on_test_line,
                should_continue=lambda: getattr(self, "test_is_running", False))
            try:
                if best_config:
                    self.selected_bat = best_config
                    self.favorite_bat = best_config
                    self.save_config()
                    self.auto_start_after_test = True
                    self.ui_call(self._refresh_bat_files)
            except Exception as e:
                log_error(f"Silent test error: {e}")
            finally:
                self.test_is_running = False
                self.launcher_status = "OFF"
                self.status_text = self.get_text("status_ready")
                self._update_discord(force=True)
                self.test_log_line = ""
                self.test_eta = ""

                duration = time.time() - self._test_start_time
                self._save_test_history(best_config, duration)

                if getattr(self, 'auto_start_after_test', False):
                    self.auto_start_after_test = False
                    self.ui_call(lambda: threading.Thread(target=self.toggle_system, daemon=True).start())
                else:
                    self.ui_call(self.play_sound, "ON")

        threading.Thread(target=background_worker, daemon=True).start()

    def _save_test_history(self, best_config, duration):
        try:
            ensure_app_data()
            history_path = os.path.join(APP_DATA_DIR, "test_history.json")
            history = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except Exception: history = []
            
            history.append({
                "date": time.strftime('%Y-%m-%d %H:%M:%S'),
                "best": best_config,
                "duration_sec": int(duration),
                "total_configs": self.test_total
            })
            
            # Храним последние 50 записей
            history = history[-50:]
            
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            log_error(f"Test history saved: best={best_config}, duration={int(duration)}s")
        except Exception as e:
            log_error(f"Save test history error: {e}")

    def interpolate_color(self, c1, c2, t):
        try:
            t = max(0.0, min(1.0, float(t)))
            cache = getattr(self, '_color_cache', None)
            key = (c1, c2, int(t * 64))
            if cache is not None:
                cached = cache.get(key)
                if cached is not None:
                    return cached
            def to_rgb(c):
                if len(c) == 4: c = "#" + "".join([x*2 for x in c[1:]])
                return tuple(int(c.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            r1, g1, b1 = to_rgb(c1)
            r2, g2, b2 = to_rgb(c2)
            r, g, b = int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t)
            result = f'#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}'
            if cache is not None:
                if len(cache) > 8192:
                    cache.clear()
                cache[key] = result
            return result
        except Exception: return c1

    def rounded_rect(self, x1, y1, x2, y2, r=10, fill_col="", outline_col="", width=1):
        points = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1]
        if fill_col: self.canvas.create_polygon(points, fill=fill_col, outline="", smooth=True)
        if outline_col: self.canvas.create_polygon(points, fill="", outline=outline_col, width=width, smooth=True)

    def draw_icon(self, name, x, y, size, color):
        if name == "snow":
            self.canvas.create_line(x+size/2, y, x+size/2, y+size, fill=color, width=2)
            self.canvas.create_line(x, y+size/2, x+size, y+size/2, fill=color, width=2)
            self.canvas.create_line(x+size*0.2, y+size*0.2, x+size*0.8, y+size*0.8, fill=color, width=2)
            self.canvas.create_line(x+size*0.8, y+size*0.2, x+size*0.2, y+size*0.8, fill=color, width=2)
        elif name == "eye": self.canvas.create_oval(x, y+size*0.2, x+size, y+size*0.8, outline=color, width=2); self.canvas.create_oval(x+size*0.3, y+size*0.3, x+size*0.7, y+size*0.7, fill=color, outline="")
        elif name == "rocket": self.canvas.create_polygon(x+size/2, y, x+size, y+size, x+size/2, y+size*0.8, x, y+size, fill=color, outline="")
        elif name == "logs": 
            self.canvas.create_rectangle(x+size*0.2, y, x+size*0.8, y+size, outline=color, width=2)
            self.canvas.create_line(x+size*0.35, y+size*0.3, x+size*0.65, y+size*0.3, fill=color, width=2)
            self.canvas.create_line(x+size*0.35, y+size*0.5, x+size*0.65, y+size*0.5, fill=color, width=2)
            self.canvas.create_line(x+size*0.35, y+size*0.7, x+size*0.65, y+size*0.7, fill=color, width=2)
        elif name == "arrow_down": self.canvas.create_line(x+size/2, y, x+size/2, y+size, fill=color, width=2); self.canvas.create_line(x+size/2, y+size, x, y+size/2, fill=color, width=2); self.canvas.create_line(x+size/2, y+size, x+size, y+size/2, fill=color, width=2)
        elif name == "globe": 
            self.canvas.create_oval(x, y, x+size, y+size, outline=color, width=2)
            self.canvas.create_line(x, y+size/2, x+size, y+size/2, fill=color, width=2)
            self.canvas.create_line(x+size/2, y, x+size/2, y+size, fill=color, width=2)
            self.canvas.create_arc(x, y, x+size, y+size, start=0, extent=359, style=tk.ARC, outline=color, width=1) 
        elif name == "star":
            pts = []
            for i in range(10):
                ang = i * math.pi / 5 - math.pi/2
                rad = size/2 if i % 2 == 0 else size/5
                pts.extend([x+size/2 + rad*math.cos(ang), y+size/2 + rad*math.sin(ang)])
            return pts

    def check_for_updates(self, silent=False):
        """Проверяет обновления на GitHub. Проверка SSL обязательна."""
        try:
            if not is_trusted_update_url(UPDATE_VERSION_URL):
                raise ValueError(f"Недоверенный URL манифеста: {UPDATE_VERSION_URL}")
            ctx = ssl.create_default_context()
            req = urllib.request.Request(UPDATE_VERSION_URL, headers={"User-Agent": f"ZapretLauncher/{CURRENT_VERSION}"})
            with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
                raw = r.read()
            data = json.loads(raw.decode('utf-8'))
            remote_ver = data.get("version", "").strip()
            self.update_data = data

            def _ver_tuple(v):
                try: return tuple(int(x) for x in v.split('.'))
                except Exception: return (0,)

            if remote_ver and _ver_tuple(remote_ver) > _ver_tuple(CURRENT_VERSION):
                self.update_available = True
                self.remote_version = remote_ver
                self.update_state = "available"
                if not silent and self.notifications_enabled:
                    try: self.tray_icon.notify(f"Обновление v{remote_ver}", "Нажмите чтобы установить")
                    except Exception: pass
            else:
                self.update_available = False
                self.remote_version = None
                self.update_state = "up_to_date"
        except Exception as e:
            self.update_state = "failed"
            log_error(f"Check update error: {e}")

    def on_mouse_move(self, event): 
        self.mouse_x, self.mouse_y = event.x, event.y
        if getattr(self, 'settings_open', False) and event.x > self.canvas.winfo_width() - self.s(280):
            self.menu_last_active = time.time()


    def run_logs_console(self):
        if not os.path.exists(LOG_PATH):
             with open(LOG_PATH, 'w', encoding='utf-8') as f:
                 f.write("[LOG START]\nNo previous logs found.\n")
        try:
            os.startfile(LOG_PATH)
            self.play_sound("ON")
        except Exception as e:
             log_error(f"Failed to open logs: {e}")
            
    def toggle_language(self):
        self.current_lang = "EN" if self.current_lang == "RU" else "RU"
        self.save_config()
        self.play_sound("ON")
        if self.launcher_status == "OFF":
             self.status_text = self.get_text("status_ready")

    def on_scroll(self, event):
        if self.settings_open and self.mode_menu_open:
            delta = 1 if event.delta < 0 else -1
            max_off = max(0, len(self.bat_files) - 16)
            self.menu_scroll_offset = max(0, min(max_off, self.menu_scroll_offset + delta))

    def on_click(self, event):
        self.menu_last_active = time.time() # Любой клик сбрасывает таймер
        if self._intro_end > time.time():
            self._intro_end = 0.0
            return
        if self.compact_mode:
            self.toggle_compact_mode()
            return
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        s = self.s
        cx, cy = w/2, h/2
        dx, dy = event.x - (w-s(40)), event.y - s(40)

        # --- Changelog overlay (первый приоритет) ---
        if getattr(self, 'changelog_open', False):
            px, py = s(30), s(20)
            pw = w - s(60)
            if abs(event.x-(px+pw-s(18))) < s(14) and abs(event.y-(py+s(18))) < s(14):
                self.changelog_open = False
                self.play_sound("OFF")
            else:
                self.changelog_open = False
            return

        # Кнопка уведомлений (слева сверху)
        if s(28) <= event.x <= s(52) and s(28) <= event.y <= s(52):
            self.notifications_enabled = not self.notifications_enabled
            self.save_config()
            self.play_sound("ON" if self.notifications_enabled else "OFF")
            return
        
        # Кнопка настройки (шестеренка вверху справа)
        if math.sqrt(dx*dx + dy*dy) < s(25):
            self.settings_open = not self.settings_open
            self.mode_menu_open = False
            self.play_sound("ON")
            return

        # 1. ГЛАВНАЯ КНОПКА СТАРТ В ЦЕНТРЕ — ВЫСОКИЙ ПРИОРИТЕТ! (только если меню настроек закрыто,
        # иначе перехватывает клики по кнопкам внутри панели настроек, например TgWsProxy)
        if not self.settings_open and math.sqrt((event.x-cx)**2 + (event.y-cy)**2) < s(165):
            if self.launcher_status == "TESTING":
                stop_y = cy + s(65)
                if abs(event.x - cx) < s(40) and abs(event.y - stop_y) < s(12):
                    self.test_is_running = False
                    self.play_sound("OFF")
                return
            elif self.launcher_status != "BUSY":
                self.mode_menu_open = False
                threading.Thread(target=self.toggle_system, daemon=True).start()
                return

        # 2. ОБРАБОТКА МЕНЮ НАСТРОЕК В ПРАВОЙ ЧАСТИ
        if self.settings_open:
            mx = w - s(260)
            if self.mode_menu_open:
                # Список профилей открывается ВВЕРХ от s(628)
                v_cnt = min(len(self.bat_files), 16)
                list_h = v_cnt * s(28)
                top_y = s(628) - list_h
                lx, iw = mx+s(20), s(220)
                if lx <= event.x <= lx+iw and top_y <= event.y <= s(628):
                    idx = int((event.y - top_y)//s(28)) + self.menu_scroll_offset
                    if 0 <= idx < len(self.bat_files):
                        new_bat = self.bat_files[idx]
                        old_bat = self.selected_bat
                        self.selected_bat = new_bat
                        self.save_config()
                        self._update_discord(force=True)
                        self.mode_menu_open = False
                        self.play_sound("ON")
                        if self.launcher_status == "ON" and new_bat != old_bat:
                            threading.Thread(target=self._hot_switch_strategy, daemon=True).start()
                    return
            if event.x > mx:
                def chk_action(x, y, attr):
                    if x <= event.x <= x+s(105) and y <= event.y <= y+s(68):
                        if attr == "open_logs": self.run_logs_console()
                        elif attr == "toggle_lang": self.toggle_language()
                        else:
                            val = not getattr(self, attr)
                            setattr(self, attr, val)
                            if attr == 'autorun_enabled' and set_autorun(val):
                                self.switch_autorun_pos = 1.0 if val else 0.0

                            self.save_config()
                            self.play_sound("ON" if val else "OFF")
                        return True
                    return False

                if chk_action(mx+s(20), s(95), 'snow_enabled') or chk_action(mx+s(135), s(95), 'minimal_mode') or \
                   chk_action(mx+s(20), s(175), 'autorun_enabled') or chk_action(mx+s(135), s(175), 'open_logs') or \
                   chk_action(mx+s(20), s(255), 'start_minimized') or chk_action(mx+s(135), s(255), 'toggle_lang'):
                    return

                # Ряд 4: TgWsProxy и авто-рестарт (Y=330..410)
                if mx+s(20) <= event.x <= mx+s(125) and s(330) <= event.y <= s(410):
                    threading.Thread(target=self.toggle_proxy, daemon=True).start()
                    return
                if mx+s(135) <= event.x <= mx+s(240) and s(330) <= event.y <= s(410):
                    self.auto_restart = not self.auto_restart
                    self.save_config()
                    self.play_sound("ON" if self.auto_restart else "OFF")
                    return
                
                # Экспорт / Импорт конфига (Y=445..470)
                if mx+s(20) <= event.x <= mx+s(125) and s(445) <= event.y <= s(470):
                    threading.Thread(target=self.export_config, daemon=True).start()
                    return
                if mx+s(135) <= event.x <= mx+s(240) and s(445) <= event.y <= s(470):
                    threading.Thread(target=self.import_config, daemon=True).start()
                    return

                # Выбор темы (Y=480..570, точечки в Y=518, 546)
                for i, name in enumerate(self.themes_data):
                     dx_dot = (mx + s(130)) + (i % 3 - 1) * s(40)
                     dy_dot = s(518) + (i // 3) * s(28)
                     if math.sqrt((event.x-dx_dot)**2+(event.y-dy_dot)**2) < s(15):
                        self.theme_name = name
                        self.theme_color = self.themes_data[name]
                        self.save_config()
                        self.play_sound("ON")
                        return

                # Запуск тестов (по всей ширине Y=580..615)
                if mx+s(20) <= event.x <= mx+s(240) and s(580) <= event.y <= s(615):
                    if self.launcher_status != "TESTING":
                        self.run_service_tests()
                    return

                # G12: Discord RPC (Y=676..706)
                if mx+s(20) <= event.x <= mx+s(240) and s(676) <= event.y <= s(706):
                    if not self.discord_rpc and not (self.discord_client_id or discord_client_id()):
                        answer = simpledialog.askstring("Discord RPC", self.get_text("discord_client_id_hint"), parent=self)
                        if not answer or not answer.strip().isdigit():
                            return
                        self.discord_client_id = answer.strip()
                    self.discord_rpc = not self.discord_rpc
                    self._apply_discord_setting()
                    self.save_config()
                    self.play_sound("ON" if self.discord_rpc else "OFF")
                    return

                # 17.5: дополнительные настройки (Y=708..736)
                if mx+s(20) <= event.x <= mx+s(240) and s(708) <= event.y <= s(736):
                    self.open_more_settings()
                    return

                # Звездочка избранного
                if math.sqrt((event.x-(mx+s(190)))**2+(event.y-s(642))) < s(15):
                     if self.selected_bat:
                        self.favorite_bat = self.selected_bat if self.favorite_bat != self.selected_bat else None
                        self.save_config()
                        self.play_sound("ON")
                     return

                # Открытие списка стратегий (Y=622..662)
                if mx+s(20) <= event.x <= mx+s(240) and s(622) <= event.y <= s(662):
                    self.mode_menu_open = not self.mode_menu_open
                    self._refresh_bat_files()
                    self.play_sound("ON")
                    return

                if mx+s(20) <= event.x <= mx+s(240) and h-s(60) <= event.y <= h-s(20):
                    if self.update_available and not self.is_updating:
                        self.perform_update()
                        self.play_sound("ON")
                    elif not self.update_available:
                        threading.Thread(target=self.check_for_updates, args=(False,), daemon=True).start()
                        self.play_sound("ON")
                    return

                # Клик на версию — открыть changelog
                if (mx+s(70) <= event.x <= mx+s(190) and h-s(20) <= event.y <= h-s(2)
                        and not self.update_available):
                    self.changelog_open = True
                    self.play_sound("ON")
                    return

                return
            self.settings_open = False; return
        

    def toggle_system(self):
        old = self.launcher_status
        if old == "TESTING": return
        if (getattr(self, "_repair_active", False) or getattr(self, "_builder_probe_active", False)
                or old == "BUSY"):
            return

        self.status_text = self.get_text("status_busy") if old != "BUSY" else "..."
        self.launcher_status = "BUSY"
        self._update_discord(force=True)
        time.sleep(0.2)
        if old == "ON": self.stop_process_logic()
        else: self.start_process_logic()

    def _hot_switch_strategy(self):
        """Атомарная смена стратегии без ручного стоп/старт — работает пока статус ON."""
        self.launcher_status = "BUSY"
        self.status_text = self.get_text("status_busy")
        self._update_discord(force=True)
        self.stop_process_logic()
        time.sleep(0.5)
        self.start_process_logic()

    def install_zapret_service(self, bat_path):
        return install_zapret_service(self.zapret_dir, bat_path)


    def launch_winws_direct(self, bat_path):
        return launch_winws_direct(self.zapret_dir, bat_path)


    def start_process_logic(self):
        self.zapret_dir = locate_zapret_dir()
        if self.auto_repair:
             si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = subprocess.SW_HIDE
             subprocess.call(["ipconfig", "/flushdns"], startupinfo=si, creationflags=0x08000000)
             subprocess.call(["netsh", "interface", "ip", "delete", "arpcache"], startupinfo=si, creationflags=0x08000000)
        
        if not self._ensure_payload():
            self.launcher_status, self.status_text = "OFF", self.get_text("status_no_file")
            return

        if not self.selected_bat or self.selected_bat not in self.bat_files:
            self._refresh_bat_files()

        bat_path = os.path.join(self.zapret_dir, self.selected_bat)
        if not os.path.exists(bat_path):
            bats = [f for f in os.listdir(self.zapret_dir) if is_strategy_bat(f)]
            if bats:
                self.selected_bat = bats[0]
                bat_path = os.path.join(self.zapret_dir, self.selected_bat)

        if os.path.exists(bat_path):
            success = self.install_zapret_service(bat_path)
            if not success:
                log_error("Служба не запустилась, попытка прямого запуска winws.exe...")
                success = self.launch_winws_direct(bat_path)

            if success:
                self.launcher_status, self.start_time, self.status_text = "ON", time.time(), self.get_text("status_on")
                self._update_discord(force=True)
                self._launch_count += 1
                self.desired_bypass = True
                self._save_stats()
                self.save_config()
                self.play_sound("ON")
                self.ui_call(self.show_osd, f"{self.get_text('osd_on')}: {self.selected_bat.replace('.bat', '')}",
                             "#22c55e")
                if self.notifications_enabled:
                    try: self.tray_icon.notify("Обход включён", "Zapret Launcher")
                    except Exception: pass
            else:
                self.launcher_status, self.status_text = "OFF", self.get_text("status_error")
                self._update_discord(force=True)
        else: 
            self._ensure_payload()
            self.launcher_status, self.status_text = "OFF", self.get_text("status_no_file")

    def stop_process_logic(self):
        stop_services_and_processes()

        self.launcher_status, self.status_text = "OFF", self.get_text("status_ready")
        self._update_discord(force=True)
        self.desired_bypass = False
        self.save_config()
        self.play_sound("OFF")
        self.ui_call(self.show_osd, self.get_text("osd_off"), "#ef4444")
        if self.notifications_enabled:
            try: self.tray_icon.notify("Обход выключен", "Zapret Launcher")
            except Exception: pass


    def _log_render_error(self, msg):
        now = time.time()
        if now - getattr(self, "_last_render_error", 0.0) >= 5.0:
            self._last_render_error = now
            log_error(msg)

    def _render_compact(self, w, h, s, fs):
        self.canvas.create_rectangle(0, 0, w, h, fill="#080914", outline="")
        color = self.theme_color if self.launcher_status == "ON" else "#5a6591"
        if self.launcher_status == "ON":
            label = self.get_text("status_on")
        elif self.launcher_status == "BUSY":
            label = self.get_text("status_busy")
            color = "#ff9900"
        else:
            label = "OFF"
        self.canvas.create_oval(s(10), h / 2 - s(6), s(10) + s(12), h / 2 + s(6), fill=color, outline="")
        self.canvas.create_text(s(30), h / 2, text=f"ZAPRET {label}", fill=color, anchor="w",
                                font=("Consolas", fs(13), "bold"))
        if self.launcher_status == "ON" and self.start_time:
            el_time = int(time.time() - self.start_time)
            self.canvas.create_text(w - s(12), h / 2,
                                    text=f"{el_time//3600:02}:{(el_time%3600)//60:02}:{el_time%60:02}",
                                    fill="#ccffdd", anchor="e", font=("Consolas", fs(11)))

    def _render_intro(self, w, h):
        """Стартовая анимация (osu-style): кольца, вращающиеся дуги, частицы, логотип."""
        t = max(0.0, min(1.0, (time.time() - self._intro_start) / 2.4))
        accent = self.theme_color
        self.canvas.create_rectangle(0, 0, w, h, fill="#080914", outline="")
        cx, cy = w / 2, h / 2 - 24

        for i in range(4):
            phase = (t * 1.8 - i * 0.16) % 1.0
            if phase <= 0.02:
                continue
            r = 50 + phase * 300
            color = self.interpolate_color("#080914", accent, max(0.0, 1.0 - phase))
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=2)

        spin = t * 720.0
        for i in range(3):
            start = (spin + i * 120) % 360
            self.canvas.create_arc(cx - 92, cy - 92, cx + 92, cy + 92, start=start, extent=54,
                                   style="arc", outline=accent, width=3)

        r0 = 56 + 5 * math.sin(t * math.pi * 3)
        self.canvas.create_oval(cx - r0, cy - r0, cx + r0, cy + r0, outline=accent, width=3)
        self.canvas.create_line(cx, cy - 24, cx, cy + 24, fill=accent, width=6)

        for i in range(10):
            phase = (t * 2 + i / 10.0) % 1.0
            ang = (i / 10.0) * 2 * math.pi + t * 4.0
            rad = 120 + 70 * phase
            px, py = cx + math.cos(ang) * rad, cy + math.sin(ang) * rad
            self.canvas.create_oval(px - 2, py - 2, px + 2, py + 2,
                                    fill=self.interpolate_color("#080914", accent, max(0.0, 1.0 - phase)),
                                    outline="")

        alpha = min(1.0, t * 2.4)
        self.canvas.create_text(cx, cy + 122, text="ZAPRET",
                                fill=self.interpolate_color("#080914", "white", alpha),
                                font=("Segoe UI", self.fs(27), "bold"))
        self.canvas.create_text(cx, cy + 158, text="L A U N C H E R",
                                fill=self.interpolate_color("#080914", accent, alpha),
                                font=("Segoe UI", self.fs(11), "bold"))

    def render_loop(self):
        self._render_delay = RENDER_FRAME_MS
        self._sync_taskbar()
        try:
            if self.discord is not None and time.time() - self._discord_ts >= 15.0:
                self._discord_ts = time.time()
                self._update_discord()
            if self.idle_hide_min and not self.compact_mode:
                try:
                    if seconds_since_last_input() > self.idle_hide_min * 60:
                        if not self._idle_hidden:
                            self._idle_hidden = True
                            self.iconify()
                    else:
                        self._idle_hidden = False
                except Exception:
                    pass
            self.canvas.delete("all")
            self.animation_step += 1
            if self._intro_end > time.time():
                cw_i, ch_i = self.canvas.winfo_width(), self.canvas.winfo_height()
                self._render_intro(cw_i if cw_i > 10 else WINDOW_WIDTH,
                                   ch_i if ch_i > 10 else WINDOW_HEIGHT)
                return

            if self._profile:
                now_ts = time.time()
                if self._frame_ts:
                    self._frame_times.append(now_ts - self._frame_ts)
                    if len(self._frame_times) > 30:
                        self._frame_times.pop(0)
                self._frame_ts = now_ts
                if now_ts - self._app_cpu_ts >= 1.0:
                    self._app_cpu_ts = now_ts
                    try:
                        self._app_cpu = self._proc.cpu_percent(None) if self._proc else 0.0
                    except Exception:
                        self._app_cpu = 0.0
            else:
                self._frame_ts = 0.0

            if not self.winfo_viewable():
                self._render_delay = RENDER_HIDDEN_MS
                return

            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            w, h = (cw if cw > 10 else WINDOW_WIDTH), (ch if ch > 10 else WINDOW_HEIGHT)
            self.ui_scale = min(w / WINDOW_WIDTH, h / WINDOW_HEIGHT)
            self.ui_scale = max(self.ui_scale, 0.1)
            s = self.s
            fs = self.fs

            cx, cy = w/2, h/2

            if self.compact_mode:
                self._render_compact(w, h, s, fs)
                self._render_delay = RENDER_COMPACT_MS
                return

            
            # --- ЛОГИКА ТАЙМЕРА ЗАКРЫТИЯ МЕНЮ (10 СЕКУНД) ---
            if self.settings_open and (time.time() - getattr(self, 'menu_last_active', 0) > 10.0):
                self.settings_open = False
                self.mode_menu_open = False
            # -----------------------------------------------

            def lerp(curr, target, factor=0.4): return curr + (target - curr) * factor
            self.switch_snow_pos = lerp(self.switch_snow_pos, 1.0 if self.snow_enabled else 0.0)
            self.switch_style_pos = lerp(self.switch_style_pos, 1.0 if self.minimal_mode else 0.0)
            self.switch_autorun_pos = lerp(self.switch_autorun_pos, 1.0 if self.autorun_enabled else 0.0)
            self.switch_minimized_pos = lerp(self.switch_minimized_pos, 1.0 if self.start_minimized else 0.0)
            self.switch_autorestart_pos = lerp(self.switch_autorestart_pos, 1.0 if self.auto_restart else 0.0)
            self.switch_proxy_pos = lerp(self.switch_proxy_pos, 1.0 if self.proxy_status == "ON" else 0.0)
            
            self.settings_anim = lerp(self.settings_anim, 1.0 if self.settings_open else 0.0, factor=0.08)
            self.mode_menu_anim = lerp(self.mode_menu_anim, 1.0 if self.mode_menu_open else 0.0, factor=0.12)
            
            self.current_warp_speed = lerp(self.current_warp_speed, 68.0 if self.launcher_status == "ON" else 3.8, 0.05)
            active_color = self.theme_color

            # 1. Базовая заливка фона
            self.canvas.create_rectangle(0, 0, w, h, fill="#0a0b1e", outline="")

            # 2. Эффекты стандартного режима (если минимализм отключён)
            if not self.minimal_mode:
                glow_pulse = (math.sin(self.animation_step * 0.04) + 1) * 0.5
                for i in range(10, 0, -1):
                    r_glow = s(350) * (i/10)
                    c_glow = self.interpolate_color("#0a0b1e", active_color, (0.02 * (11-i)/11) * glow_pulse)
                    self.canvas.create_oval(cx-r_glow, cy-r_glow, cx+r_glow, cy+r_glow, fill=c_glow, outline="")

                grid_c = self.interpolate_color("#1a1e3d", active_color, 0.12)
                spacing = s(60)
                grid_speed = (self.animation_step * 1.5) % spacing
                
                grid_half = int((w / 2 + s(60)) / max(1.0, s(20))) + 1
                for i in range(-grid_half, grid_half + 1):
                    x_far = cx + i * s(20)
                    x_near = cx + i * s(400)
                    self.canvas.create_line(x_far, cy, x_near, h, fill=grid_c, width=1)
                    self.canvas.create_line(x_far, cy, x_near, 0, fill=grid_c, width=1)

                for i in range(16):
                    z_val = (i * spacing + grid_speed) / 1000
                    if z_val > 1.0: continue
                    y_bottom = cy + (h - cy) * (z_val ** 2.2)
                    y_top = cy - cy * (z_val ** 2.2)
                    alpha = 0.5 * (1.0 - abs(z_val - 0.5) * 2.0)
                    lc = self.interpolate_color("#0a0b1e", active_color, max(0.0, alpha))
                    self.canvas.create_line(0, y_bottom, w, y_bottom, fill=lc, width=1)
                    self.canvas.create_line(0, y_top, w, y_top, fill=lc, width=1)

                for p in self.warp_particles:
                    p.update(self.current_warp_speed)
                    p.draw(self.canvas, cx, cy, w, h, active_color, self.interpolate_color)

                hud_c = active_color if self.launcher_status == "ON" else "#444b6e"
                g, l = s(20), s(30)
                for x_hud, y_hud, dx_hud, dy_hud in [(g, g, 1, 1), (w-g, g, -1, 1), (g, h-g, 1, -1), (w-g, h-g, -1, -1)]:
                    self.canvas.create_line(x_hud, y_hud, x_hud+dx_hud*l, y_hud, fill=hud_c, width=2)
                    self.canvas.create_line(x_hud, y_hud, x_hud, y_hud+dy_hud*l, fill=hud_c, width=2)
                
                self.canvas.create_text(g+s(10), g+s(15), text=f"CPU: {self.hud_values.get('CPU', '0')}%", fill="#5a6591", font=("Consolas", fs(9)), anchor="w")
                self.canvas.create_text(g+s(10), g+s(30), text=f"RAM: {self.hud_values.get('RAM', '0')}%", fill="#5a6591", font=("Consolas", fs(9)), anchor="w")
                ping_val = self.hud_values.get('PING', '---')
                ping_col = "#5a6591" if ping_val == '---' else (active_color if self.launcher_status == "ON" else "#5a6591")
                self.canvas.create_text(g+s(10), g+s(45), text=f"PING: {ping_val}", fill=ping_col, font=("Consolas", fs(9)), anchor="w")
                if self._profile:
                    avg_dt = sum(self._frame_times) / len(self._frame_times) if self._frame_times else 0.0
                    fps = int(1.0 / avg_dt) if avg_dt > 0 else 0
                    self.canvas.create_text(g+s(10), g+s(60), text=f"FPS: {fps}  APP: {self._app_cpu:.0f}%",
                                            fill="#ff9900", font=("Consolas", fs(9)), anchor="w")

                viz_x, viz_y = w - g - s(10), h - g - s(15)
                for i in range(len(self.viz_bars)):
                    if self.animation_step % (i+3) == 0: self.viz_bars[i] = lerp(self.viz_bars[i], random.uniform(0.1, 0.95), 0.3)
                    bh = self.viz_bars[i] * s(25)
                    bx_pos = viz_x - (i * s(6))
                    self.canvas.create_rectangle(bx_pos-s(2), viz_y, bx_pos, viz_y - bh, fill=active_color if bh > s(15) else "#3d446e", outline="")

            # Эффект снега отрисовывается отдельно и работает всегда при включении
            if self.snow_enabled:
                for s_flake in self.snowflakes: s_flake.update(w, h); s_flake.draw(self.canvas)

            bx, by, rb = cx, cy, s(155) 
            breath = math.sin(self.animation_step * 0.05) * s(5)
            if self.minimal_mode: 
                self.canvas.create_oval(bx-rb-s(10), by-rb-s(10), bx+rb+s(10), by+rb+s(10), fill="", outline=self.interpolate_color("#1a203c", active_color, 0.3 if self.launcher_status == "ON" else 0.1), width=1)
                self.canvas.create_oval(bx-rb, by-rb, bx+rb, by+rb, fill="#0d1124", outline=active_color if self.launcher_status == "ON" else "#333b5c", width=3)
            else:
                for i in range(5):
                    gr = rb + s(22) - i*s(4) + breath
                    self.canvas.create_oval(bx-gr, by-gr, bx+gr, by+gr, outline=self.interpolate_color("#000000", active_color, 0.04 + i*0.02), width=2)
                self.canvas.create_oval(bx-rb, by-rb, bx+rb, by+rb, fill="#0a0b1e", outline="#2a305e", width=4)
                r1, r2 = rb-s(10) + breath*0.5, rb-s(20) + breath*0.5
                c_orb1, c_orb2 = (active_color if self.launcher_status == "ON" else "#444b6e"), (active_color if self.launcher_status == "ON" else "#333b5c")
                for i in range(3): 
                    start = math.degrees(self.animation_step*0.02 + (i*2*math.pi/3))
                    self.canvas.create_arc(bx-r1, by-r1, bx+r1, by+r1, start=start, extent=80, style=tk.ARC, outline=c_orb1, width=2)
                for i in range(2): 
                    start = math.degrees(-self.animation_step*0.05 + (i*math.pi))
                    self.canvas.create_arc(bx-r2, by-r2, bx+r2, by+r2, start=start, extent=65, style=tk.ARC, outline=c_orb2, width=5 if self.launcher_status == "ON" else 3)
                cr_base = rb - s(40)
                for i in range(12):
                    cr = cr_base * (1 - i/12)
                    col_core = self.interpolate_color(active_color if self.launcher_status == "ON" else "#1a1e3d", "#000000", (i/12) + (1-((0.6 + math.sin(self.animation_step*0.1)*0.25) if self.launcher_status == "ON" else 0.2)))
                    ox_core, oy_core = math.sin(self.animation_step*0.06+i)*s(3), math.cos(self.animation_step*0.06+i)*s(3)
                    self.canvas.create_oval(bx-cr+ox_core, by-cr+oy_core, bx+cr+ox_core, by+cr+oy_core, fill=col_core, outline="")

            main_title_txt = self.get_text("main_title")
            title_base_y = s(55)
            float_y = math.sin(self.animation_step * 0.05) * s(2.5) if not self.minimal_mode else 0
            is_heavy = (self.animation_step % 150 > 135) if not self.minimal_mode else False
            is_random = (random.random() < 0.10) if not self.minimal_mode else False
            
            if is_heavy or is_random:
                display_txt_chars = list(main_title_txt)
                if random.random() < 0.6:
                    chaos_chars = ['?', '$', '#', '0', '1', '<', '>', '_', '!']
                    count = random.randint(1, 3)
                    for _ in range(count):
                        idx = random.randint(0, len(display_txt_chars)-1)
                        display_txt_chars[idx] = random.choice(chaos_chars)
                display_txt = "".join(display_txt_chars)

                shift = random.randint(4, 10) if is_heavy else random.randint(2, 5)
                self.canvas.create_text(cx - s(shift), title_base_y + float_y + s(random.randint(-2, 2)), text=display_txt, fill="#ff0040", font=("Segoe UI", fs(48), "bold"))
                self.canvas.create_text(cx + s(shift), title_base_y + float_y + s(random.randint(-2, 2)), text=display_txt, fill="#00f2ff", font=("Segoe UI", fs(48), "bold"))
                if random.random() < 0.3:
                    ghost_off = random.randint(10, 30) * random.choice([-1, 1])
                    self.canvas.create_text(cx + s(ghost_off), title_base_y + float_y, text=display_txt, fill="#3d446e", font=("Segoe UI", fs(48), "bold"))
                if random.random() > 0.15:
                    self.canvas.create_text(cx, title_base_y + float_y, text=display_txt, fill="white", font=("Segoe UI", fs(48), "bold"))
                num_blocks = random.randint(3, 9)
                for _ in range(num_blocks):
                    bx_b = cx + s(random.randint(-110, 110))
                    by_b = title_base_y + float_y + s(random.randint(-20, 20))
                    bw = s(random.randint(5, 50))
                    bh = s(random.randint(2, 12))
                    col = random.choice(["#0a0b1e", "#0a0b1e", active_color, "#ff00a0", "white"])
                    outline = ""
                    if col == "#0a0b1e" and random.random() < 0.3: outline = active_color 
                    self.canvas.create_rectangle(bx_b, by_b, bx_b+bw, by_b+bh, fill=col, outline=outline)
                if random.random() < 0.5:
                    ly = title_base_y + float_y + s(random.randint(-25, 25))
                    self.canvas.create_line(cx - s(120), ly, cx + s(120), ly, fill="white", width=1)
            else:
                self.canvas.create_text(cx, title_base_y + float_y, text=main_title_txt, fill="white", font=("Segoe UI", fs(48), "bold"))
            
            self.canvas.create_text(cx, s(105), text="by A1kio", fill="#7a89c2", font=("Segoe UI", fs(16)))
            
            # --- ЛОГИКА ЦЕНТРАЛЬНОГО КРУГА (Включая режим ТЕСТИРОВАНИЯ) ---
            if self.launcher_status == "ON":
                el_time = int(time.time() - self.start_time)
                self.canvas.create_text(cx, cy-s(10), text=f"{el_time//3600:02}:{(el_time%3600)//60:02}:{el_time%60:02}", fill="white", font=("Consolas", fs(26), "bold"))
                self.canvas.create_text(cx, cy+s(30), text=self.get_text("btn_active"), fill="#ccffdd", font=("Segoe UI", fs(12), "bold"))
                # Имя активной стратегии под кнопкой
                strat_disp = re.sub(r'[\(\)]', '', self.selected_bat.replace('.bat','').replace('general','').strip()) or 'Standard'
                self.canvas.create_text(cx, cy+s(50), text=strat_disp, fill=self.interpolate_color("#3d446e", active_color, 0.5), font=("Consolas", fs(8)))
            
            elif self.launcher_status == "TESTING":
                # Надпись TESTING
                self.canvas.create_text(cx, cy-s(30), text="TESTING", fill=active_color, font=("Segoe UI", fs(36), "bold"))
                
                # Прогресс + ETA
                prog = getattr(self, 'test_progress', 0)
                tot = getattr(self, 'test_total', 1)
                eta_str = getattr(self, 'test_eta', '')
                prog_text = f"Проверено: {prog} / {tot}"
                if eta_str:
                    prog_text += f"  ({eta_str})"
                self.canvas.create_text(cx, cy+s(10), text=prog_text, fill="#ff9900", font=("Consolas", fs(14), "bold"))
                
                # Бегущая строка логов
                log_txt = getattr(self, 'test_log_line', '')
                if len(log_txt) > 35: log_txt = "..." + log_txt[-32:]
                self.canvas.create_text(cx, cy+s(35), text=log_txt, fill="#ccffdd", font=("Consolas", fs(9)))
                
                # Кнопка СТОП
                stop_y = cy + s(65)
                hvr_stop = (abs(self.mouse_x - cx) < s(40) and abs(self.mouse_y - stop_y) < s(12))
                stop_col = "#ff4444" if hvr_stop else "#aa3333"
                self.canvas.create_text(cx, stop_y, text="[ СТОП ]", fill=stop_col, font=("Consolas", fs(11), "bold"))
                # ------------------------------------
            
            elif self.launcher_status == "BUSY": 
                self.canvas.create_text(cx, cy, text="...", fill="white", font=("Consolas", fs(40), "bold"))
            
            else: 
                self.canvas.create_text(cx, cy, text=self.get_text("btn_start"), fill="white", font=("Segoe UI", fs(36), "bold"))
                # Показываем выбранную стратегию под кнопкой START
                strat_idle = re.sub(r'[\(\)]', '', self.selected_bat.replace('.bat','').replace('general','').strip()) or 'Standard'
                self.canvas.create_text(cx, cy+s(45), text=strat_idle, fill="#3d446e", font=("Consolas", fs(8)))
            # --------------------------------------------------------------

            if self.settings_anim > 0.01:
                mx_menu = w - (s(260) * self.settings_anim)
                self.canvas.create_rectangle(mx_menu, 0, w, h, fill="#080914", outline=""); self.canvas.create_line(mx_menu, 0, mx_menu, h, fill=active_color, width=2)
                self.canvas.create_text(mx_menu + s(130), s(50), text=self.get_text("settings_title"), fill="white", font=("Segoe UI", fs(19), "bold"))
                
                def draw_tgl_menu(x, y, label, icon, val, anim, is_btn=False):
                    hvr_m = (x <= self.mouse_x <= x+s(105) and y <= self.mouse_y <= y+s(70))
                    bg_m, brd_m = ("#15182e" if hvr_m else "#0e1124"), (active_color if val else ("#5a6591" if hvr_m else "#2a305e"))
                    self.rounded_rect(x, y, x+s(105), y+s(70), r=s(10), fill_col=bg_m, outline_col=brd_m)
                    if anim > 0.01 and not is_btn: self.canvas.create_rectangle(x+2, y+s(70)-(s(70)*anim)+1, x+s(104), y+s(69), fill=self.interpolate_color("#0e1124", active_color, 0.25), outline="")
                    c_m = "white" if (val or hvr_m) else "#5a6591"
                    self.draw_icon(icon, x+s(10), y+s(8), s(20), c_m)
                    self.canvas.create_text(x+s(10), y+s(42), text=label, fill=c_m, anchor="w", font=("Segoe UI", fs(9), "bold"))
                
                draw_tgl_menu(mx_menu+s(20), s(95), self.get_text("snow_fx"), "snow", self.snow_enabled, self.switch_snow_pos)
                draw_tgl_menu(mx_menu+s(135), s(95), self.get_text("minimal_mode"), "eye", self.minimal_mode, self.switch_style_pos)
                draw_tgl_menu(mx_menu+s(20), s(175), self.get_text("auto_run"), "rocket", self.autorun_enabled, self.switch_autorun_pos)
                draw_tgl_menu(mx_menu+s(135), s(175), self.get_text("logs"), "logs", False, 0, is_btn=True)
                draw_tgl_menu(mx_menu+s(20), s(255), self.get_text("start_min"), "arrow_down", self.start_minimized, self.switch_minimized_pos)
                draw_tgl_menu(mx_menu+s(135), s(255), self.get_text("lang_name"), "globe", False, 0, is_btn=True)
                # Ряд 4: TgWsProxy и Авто-рестарт
                proxy_lbl = "TgProxy ON" if self.proxy_status == "ON" else "TgProxy"
                draw_tgl_menu(mx_menu+s(20), s(335), proxy_lbl, "globe", self.proxy_status == "ON", self.switch_proxy_pos)
                draw_tgl_menu(mx_menu+s(135), s(335), "AutoRST", "rocket", self.auto_restart, self.switch_autorestart_pos)
                
                # Детектор bypass + статистика (Y=415..435)
                bypass_col = active_color if self._bypass_check == "OK" else ("#ff2a2a" if self._bypass_check == "FAIL" else "#3d446e")
                bypass_txt = "\u2713 WORK" if self._bypass_check == "OK" else ("\u2717 FAIL" if self._bypass_check == "FAIL" else "CHECK...")
                self.rounded_rect(mx_menu+s(20), s(415), mx_menu+s(125), s(435), r=s(5), fill_col="#0e1124", outline_col=bypass_col)
                self.canvas.create_text(mx_menu+s(72), s(425), text=bypass_txt, fill=bypass_col, font=("Consolas", fs(8), "bold"))

                # Статистика аптайма
                total_h = self._total_uptime_sec // 3600
                total_m = (self._total_uptime_sec % 3600) // 60
                self.rounded_rect(mx_menu+s(135), s(415), mx_menu+s(240), s(435), r=s(5), fill_col="#0e1124", outline_col="#2a305e")
                self.canvas.create_text(mx_menu+s(187), s(425), text=f"▶ {total_h}ч {total_m}м | {self._launch_count} зап.", fill="#5a6591", font=("Consolas", fs(7)))

                # Экспорт / Импорт конфига (Y=445..470)
                hvr_exp = (mx_menu+s(20) <= self.mouse_x <= mx_menu+s(125) and s(445) <= self.mouse_y <= s(470))
                hvr_imp = (mx_menu+s(135) <= self.mouse_x <= mx_menu+s(240) and s(445) <= self.mouse_y <= s(470))
                self.rounded_rect(mx_menu+s(20), s(445), mx_menu+s(125), s(470), r=s(4), fill_col="#15182e" if hvr_exp else "#0e1124", outline_col=active_color if hvr_exp else "#2a305e")
                self.canvas.create_text(mx_menu+s(72), s(457), text="⬇ Экспорт", fill="white" if hvr_exp else "#5a6591", font=("Consolas", fs(7)))
                self.rounded_rect(mx_menu+s(135), s(445), mx_menu+s(240), s(470), r=s(4), fill_col="#15182e" if hvr_imp else "#0e1124", outline_col=active_color if hvr_imp else "#2a305e")
                self.canvas.create_text(mx_menu+s(187), s(457), text="⬆ Импорт", fill="white" if hvr_imp else "#5a6591", font=("Consolas", fs(7)))

                # Блок тем (Y=480..570, высота 90px)
                self.rounded_rect(mx_menu+s(20), s(480), mx_menu+s(240), s(570), r=s(10), fill_col="#0e1124", outline_col="#2a305e")
                self.canvas.create_text(mx_menu+s(130), s(495), text=self.get_text("theme"), fill="white", anchor="center", font=("Segoe UI", fs(9), "bold"))
                
                for i, (name, col) in enumerate(self.themes_data.items()):
                    dx_dot = (mx_menu + s(130)) + (i % 3 - 1) * s(40)
                    dy_dot = s(520) + (i // 3) * s(28)
                    d_dot = math.sqrt((self.mouse_x-dx_dot)**2+(self.mouse_y-dy_dot)**2)
                    self.canvas.create_oval(dx_dot-s(8), dy_dot-s(8), dx_dot+s(8), dy_dot+s(8), fill=col, outline="white" if name == self.theme_name or d_dot < s(10) else "", width=2 if name == self.theme_name else 1)

                # Запуск тестов (полноширинная кнопка Y=580..615)
                hvr_test = (mx_menu+s(20) <= self.mouse_x <= mx_menu+s(240) and s(580) <= self.mouse_y <= s(615))
                self.rounded_rect(mx_menu+s(20), s(580), mx_menu+s(240), s(615), r=s(5), fill_col="#1a3328" if hvr_test else "#0e1124", outline_col=active_color if hvr_test else "#2a305e")
                self.canvas.create_text(mx_menu+s(130), s(597), text=self.get_text("btn_tests"), fill="white" if hvr_test else "#5a6591", font=("Segoe UI", fs(9), "bold"))

                # Активная стратегия (Y=622..662)
                self.canvas.create_text(mx_menu+s(20), s(622), text=self.get_text("active_strategy"), fill="#5a6591", anchor="w", font=("Segoe UI", fs(8), "bold"))
                disp_strat = re.sub(r'[\(\)]', '', self.selected_bat.replace(".bat", "").replace("general", "").strip()) or "Standard"
                
                self.rounded_rect(mx_menu+s(20), s(632), mx_menu+s(240), s(668), r=s(5), fill_col="#0e1124", outline_col=active_color if self.mode_menu_open else "#2a305e")
                self.canvas.create_text(mx_menu+s(35), s(650), text=disp_strat[:22]+".." if len(disp_strat)>24 else disp_strat, fill="white", anchor="w", font=("Consolas", fs(10)))
                
                s_pts_m = self.draw_icon("star", mx_menu+s(190), s(642), s(20), "")
                self.canvas.create_polygon(s_pts_m, fill="yellow" if self.selected_bat == self.favorite_bat else "", outline="#5a6591", width=1)

                # G12: Discord RPC (кнопка-тумблер Y=676..706)
                hvr_dsc = (mx_menu+s(20) <= self.mouse_x <= mx_menu+s(240) and s(676) <= self.mouse_y <= s(706))
                dsc_col = active_color if self.discord_rpc else "#2a305e"
                self.rounded_rect(mx_menu+s(20), s(676), mx_menu+s(240), s(706), r=s(5),
                                  fill_col="#1a3328" if self.discord_rpc else ("#15182e" if hvr_dsc else "#0e1124"),
                                  outline_col=dsc_col)
                dsc_state = "ON" if self.discord_rpc else "OFF"
                self.canvas.create_text(mx_menu+s(130), s(691),
                                        text=f"{self.get_text('discord_rpc_lbl')}: {dsc_state}",
                                        fill="white" if (self.discord_rpc or hvr_dsc) else "#5a6591",
                                        font=("Segoe UI", fs(9), "bold"))

                # 17.5: дополнительные настройки (Y=708..736)
                hvr_more = (mx_menu+s(20) <= self.mouse_x <= mx_menu+s(240) and s(708) <= self.mouse_y <= s(736))
                self.rounded_rect(mx_menu+s(20), s(708), mx_menu+s(240), s(736), r=s(5),
                                  fill_col="#15182e" if hvr_more else "#0e1124",
                                  outline_col=active_color if hvr_more else "#2a305e")
                self.canvas.create_text(mx_menu+s(130), s(722), text=self.get_text("more_settings"),
                                        fill="white" if hvr_more else "#5a6591",
                                        font=("Segoe UI", fs(8), "bold"))

                if self.mode_menu_anim > 0.01:
                    actual_files = self.bat_files
                    v_cnt = min(len(actual_files), 16)
                    list_height = (v_cnt * s(28)) * self.mode_menu_anim
                    top_y_list = s(628) - list_height
                    self.rounded_rect(mx_menu+s(20), top_y_list, mx_menu+s(240), s(628), r=s(5), fill_col="#0a0b1e", outline_col=active_color)
                    for i in range(self.menu_scroll_offset, min(self.menu_scroll_offset + 16, len(actual_files))):
                        iy_item = top_y_list + (i - self.menu_scroll_offset) * s(28)
                        if iy_item + s(28) > s(628) + 1: break
                        b_n = actual_files[i]
                        clean_n = re.sub(r'[\(\)]', '', b_n.replace(".bat","").replace("general","").strip()) or "Standard"
                        hvr_i = (mx_menu+s(20) <= self.mouse_x <= mx_menu+s(240) and iy_item <= self.mouse_y <= iy_item+s(28))
                        is_s = (b_n == self.selected_bat)
                        if hvr_i: self.canvas.create_rectangle(mx_menu+s(22), iy_item+2, mx_menu+s(238), iy_item+s(26), fill="#1a1e3d", outline="")
                        if is_s: self.canvas.create_line(mx_menu+s(22), iy_item+4, mx_menu+s(22), iy_item+s(24), fill=active_color, width=3)
                        c_i = active_color if hvr_i or is_s else "white"
                        self.canvas.create_text(mx_menu+s(30), iy_item+s(14), text=("★ " if b_n==self.favorite_bat else "  ") + clean_n, fill=c_i, anchor="w", font=("Consolas", fs(8)))
                
                self.rounded_rect(mx_menu+s(20), h-s(60), mx_menu+s(240), h-s(20), r=s(20), fill_col="#1a3328" if self.update_available else "#15182e", outline_col=active_color if self.update_available else "#2a305e")
                
                upd_text = self.get_text("update_check")
                if self.is_updating:
                    st = self.update_state
                    if isinstance(st, str) and st.startswith("dl_"):
                        pct = st[3:]
                        upd_text = f"{'ЗАГРУЗКА' if self.current_lang == 'RU' else 'LOADING'} {pct}%"
                    elif st == "verifying":
                        upd_text = "ПРОВЕРКА..." if self.current_lang == "RU" else "VERIFYING..."
                    else:
                        upd_text = self.get_text("update_downloading")
                elif self.update_state == "failed": upd_text = self.get_text("update_failed")
                elif self.update_state == "hash_fail": upd_text = self.get_text("update_hash_fail")
                elif self.update_state == "available": upd_text = self.get_text("update_found")
                elif self.update_state == "up_to_date": upd_text = self.get_text("update_latest")
                
                self.canvas.create_text(mx_menu+s(130), h-s(40), text=upd_text, fill="white" if self.update_available else "#5a6591", font=("Segoe UI", fs(10), "bold"))
                
                if self.update_available and self.remote_version:
                    v_text = f"v{CURRENT_VERSION}  >>  v{self.remote_version}"
                    self.canvas.create_text(mx_menu+s(130), h-s(10), text=v_text, fill="#00ff88", font=("Consolas", fs(9), "bold"))
                else:
                    hvr_ver = (mx_menu+s(70) <= self.mouse_x <= mx_menu+s(190) and h-s(20) <= self.mouse_y <= h-s(2))
                    ver_col = "#00ccff" if hvr_ver else "#3d446e"
                    self.canvas.create_text(mx_menu+s(130), h-s(10), text=f"v{CURRENT_VERSION}  •  что нового?", fill=ver_col, font=("Arial", fs(8)))

            # Changelog overlay — рисуется поверх всего
            if getattr(self, 'changelog_open', False):
                # Затемнение фона
                self.canvas.create_rectangle(0, 0, w, h, fill="#000000", stipple="gray50", outline="")
                # Панель
                px, py, pw, ph = s(30), s(20), w-s(60), h-s(40)
                self.rounded_rect(px, py, px+pw, py+ph, r=s(14), fill_col="#080a1c", outline_col=active_color)
                # Заголовок
                self.canvas.create_text(px+pw//2, py+s(22), text="ЧТО НОВОГО", fill=active_color, font=("Segoe UI", fs(13), "bold"))
                self.canvas.create_line(px+s(15), py+s(38), px+pw-s(15), py+s(38), fill="#1e2240", width=1)
                # Кнопка закрыть
                hvr_cl = (abs(self.mouse_x-(px+pw-s(18))) < s(12) and abs(self.mouse_y-(py+s(18))) < s(12))
                self.canvas.create_text(px+pw-s(18), py+s(18), text="✕", fill="#ff4466" if hvr_cl else "#5a6591", font=("Arial", fs(12), "bold"))
                # Контент
                cy_log = py + s(50)
                for ver, lines in CHANGELOG:
                    if cy_log > py+ph-s(25): break
                    self.canvas.create_text(px+s(15), cy_log, text=ver, fill=active_color, font=("Consolas", fs(10), "bold"), anchor="w")
                    cy_log += s(18)
                    for line in lines:
                        if cy_log > py+ph-s(20): break
                        col = "#cc4466" if line.startswith("-") else ("#5a7faa" if line.startswith("*") else "#ccddff")
                        self.canvas.create_text(px+s(20), cy_log, text=line, fill=col, font=("Consolas", fs(8)), anchor="w")
                        cy_log += s(15)
                    cy_log += s(5)

            # КНОПКА МЕНЮ
            gc_b = active_color if self.settings_open else "white"
            self.canvas.create_oval(w-s(52), s(28), w-s(28), s(52), outline=gc_b, width=2); self.canvas.create_oval(w-s(44), s(36), w-s(36), s(44), fill=gc_b, outline="")
            
            # КНОПКА УВЕДОМЛЕНИЙ (слева сверху) - красивая иконка
            notif_x, notif_y = s(40), s(40)
            notif_hvr = (s(28) <= self.mouse_x <= s(52) and s(28) <= self.mouse_y <= s(52))
            notif_col = "#00ff88" if self.notifications_enabled else "#5a6591"
            
            # Круг кнопки
            if notif_hvr: self.canvas.create_oval(s(28), s(28), s(52), s(52), fill="#1a1e3d", outline="")
            self.canvas.create_oval(s(28), s(28), s(52), s(52), outline=notif_col, width=2)
            
            # Иконка громкости
            if self.notifications_enabled:
                # Громкость (дуги снизу)
                self.canvas.create_arc(notif_x-s(5), notif_y-s(2), notif_x+s(5), notif_y+s(6), start=180, extent=180, style=tk.ARC, outline=notif_col, width=2)
                self.canvas.create_arc(notif_x-s(3), notif_y-s(2), notif_x+s(3), notif_y+s(4), start=180, extent=180, style=tk.ARC, outline=notif_col, width=2)
                # Круг в центре
                self.canvas.create_oval(notif_x-s(2), notif_y-s(2), notif_x+s(2), notif_y+s(2), fill=notif_col, outline="")
            else:
                # Крестик (выключено)
                self.canvas.create_line(notif_x-s(4), notif_y-s(4), notif_x+s(4), notif_y+s(4), fill=notif_col, width=2)
                self.canvas.create_line(notif_x-s(4), notif_y+s(4), notif_x+s(4), notif_y-s(4), fill=notif_col, width=2)

        except Exception as e:
            self._log_render_error(f"Render Error: {e}")
        finally:
            self.after(getattr(self, "_render_delay", RENDER_FRAME_MS), self.render_loop)


    def perform_update(self):
        if self.is_updating: return
        self.is_updating, self.update_state = True, "downloading"

        if not self.update_data:
            self.is_updating = False
            self.update_state = "failed"
            return

        target_url = self.update_data.get("download_url")
        target_hash = (self.update_data.get("hash") or "").strip().lower()

        if not target_hash:
            log_error("Апдейт отклонён: в манифесте нет хэша")
            self.is_updating = False
            self.update_state = "failed"
            return
        if not is_trusted_update_url(target_url):
            log_error(f"Апдейт отклонён: недоверенный URL {target_url}")
            self.is_updating = False
            self.update_state = "failed"
            return

        def _download(url, dest):
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={"User-Agent": f"ZapretLauncher/{CURRENT_VERSION}"})
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp, open(dest, 'wb') as out:
                total = int(resp.headers.get('Content-Length', 0))
                if total and total > MAX_UPDATE_BYTES:
                    raise ValueError(f"Слишком большой файл обновления: {total} байт")
                done = 0
                while True:
                    chunk = resp.read(65536)
                    if not chunk: break
                    out.write(chunk)
                    done += len(chunk)
                    if done > MAX_UPDATE_BYTES:
                        raise ValueError("Превышен лимит размера обновления")
                    if total > 0:
                        self.update_state = f"dl_{int(done*100/total)}"
                out.flush()

        def _upd():
            try:
                cur_exe = current_exe_path()
                temp_dir = os.environ.get('TEMP', os.path.expanduser('~'))
                upd_exe = os.path.join(temp_dir, "Zapret_Update.exe")
                try:
                    if os.path.exists(upd_exe): os.remove(upd_exe)
                except Exception: pass

                _download(target_url, upd_exe)
                self.update_state = "verifying"

                new_exe = cur_exe + ".new"

                h = hashlib.sha256()
                with open(upd_exe, 'rb') as src_f, open(new_exe, 'wb') as dst_f:
                    for block_data in iter(lambda: src_f.read(65536), b""):
                        h.update(block_data)
                        dst_f.write(block_data)
                    dst_f.flush()
                    os.fsync(dst_f.fileno())

                if h.hexdigest().lower() != target_hash:
                    self.update_state = "hash_fail"
                    log_error(f"Hash mismatch: expected {target_hash}, got {h.hexdigest()}")
                    for path in (new_exe, upd_exe):
                        try: os.remove(path)
                        except Exception: pass
                    self.is_updating = False
                    return

                old_exe = cur_exe + ".old"
                try:
                    if os.path.exists(old_exe): os.remove(old_exe)
                except Exception: pass

                try:
                    os.replace(cur_exe, old_exe)
                except Exception as e:
                    log_error(f"Не удалось переименовать текущий exe: {e}")
                    self.is_updating = False
                    self.update_state = "failed"
                    try: os.remove(new_exe)
                    except Exception: pass
                    return

                try:
                    os.replace(new_exe, cur_exe)
                except Exception as e:
                    log_error(f"Не удалось установить обновление: {e}")
                    try: os.replace(old_exe, cur_exe)
                    except Exception: pass
                    self.is_updating = False
                    self.update_state = "failed"
                    return

                try: os.remove(upd_exe)
                except Exception: pass

                subprocess.Popen([cur_exe], close_fds=True)
                os._exit(0)
            except Exception as e:
                self.is_updating = False
                self.update_state = "failed"
                log_error(f"perform_update error: {e}")

        threading.Thread(target=_upd, daemon=True).start()

if __name__ == "__main__":
    install_crash_handler("tk")
    if "--install-service" in sys.argv:
        sys.exit(0 if cli_install_service() else 1)
    record_install_mode()
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "ZapretLauncherSingleInstanceMutex")
    if ctypes.windll.kernel32.GetLastError() == 183:
        sys.exit(0)
        
    if is_admin():
        try:
            app_launcher = ZapretLauncher()
            
            # --- ИСПРАВЛЕННОЕ ЗАКРЫТИЕ ОКНА ---
            def on_closing():
                app_launcher.withdraw()
                try: app_launcher._save_stats()
                except Exception: pass
                try:
                    if app_launcher.taskbar is not None:
                        app_launcher.taskbar.close()
                except Exception: pass
                app_launcher.stop_process_logic()
                app_launcher.destroy()
                os._exit(0)
                
            app_launcher.protocol("WM_DELETE_WINDOW", on_closing)
            # ----------------------------------
            
            app_launcher.mainloop()
        except Exception: 
            import traceback
            log_error(traceback.format_exc())
    else:
        if getattr(sys, 'frozen', False):
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "", None, 1)
        else:
            script_abs = os.path.abspath(sys.argv[0])
            params_str = " ".join([f'"{a_arg}"' for a_arg in sys.argv[1:]])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_abs}" {params_str}', None, 1)
