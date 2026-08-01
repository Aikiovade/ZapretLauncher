# Сборка: python -m PyInstaller --noconfirm --onefile --windowed --uac-admin --name "Zapret" --icon "icon.ico" --add-data "zapret_data.zip;." --add-data "icon.ico;." zapret.py

import customtkinter as ctk
import tkinter as tk
import os
import subprocess
import threading
import time
import math
import random
import sys
import ctypes
import winsound 
import struct 
import traceback 
import winreg 
import json
import urllib.request 
import urllib.error
import zipfile
import shutil
import re 
import ssl
import hashlib 
import webbrowser 
import psutil
import pystray
from PIL import Image, ImageDraw
import keyboard

# ======================================================================
# 1. КОНФИГУРАЦИЯ И ПУТИ
# ======================================================================
CURRENT_VERSION = "17.3"
UPDATE_VERSION_URL = "https://raw.githubusercontent.com/Aikiovade/ZapretLauncher/main/update_info.json"

# --- GLOBAL UI SETTINGS (Critical for fast start) ---
try:
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
except: pass
# ----------------------------------------------------

DATA_ARCHIVE_NAME = "zapret_data.zip"
FOLDER_NAME = "zapret-discord-youtube-1.10.0"
DEFAULT_BAT = "general (ALT).bat"
CONFIG_FILE_NAME = "launcher_config.json"
LOG_FILE_NAME = "launcher_debug.txt"

RUSSIAN_ANTHEM_FILE = "yarusskiy.mp3"
AMERICAN_ANTHEM_FILE = "americanets.mp3"
TGWS_PROXY_EXE = "TgWsProxy_windows.exe"  # TgWsProxy — запускается из папки zapret

CHANGELOG = [
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

TARGET_PROCESSES = ["winws.exe"]      
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 800

# --- ОПРЕДЕЛЕНИЕ ПУТЕЙ ---
if getattr(sys, 'frozen', False):
    EXE_DIR = os.path.dirname(sys.executable)
else:
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))

APP_DATA_DIR = os.path.join(os.environ['LOCALAPPDATA'], 'ZapretLauncher')

def locate_zapret_dir():
    candidates = [
        os.path.join(APP_DATA_DIR, "zapret_data", FOLDER_NAME),
        os.path.join(APP_DATA_DIR, FOLDER_NAME),
        os.path.join(EXE_DIR, "zapret_data", FOLDER_NAME),
        os.path.join(EXE_DIR, FOLDER_NAME),
        os.path.join(APP_DATA_DIR, "zapret_data"),
        os.path.join(APP_DATA_DIR)
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.exists(os.path.join(c, "bin", "winws.exe")):
            return c
    return candidates[0]

ZAPRET_DIR = locate_zapret_dir()

def get_autorun_exe_path():
    """Путь к .exe для автозапуска - всегда в папке с данными"""
    return os.path.join(APP_DATA_DIR, FOLDER_NAME, "Zapret.exe")
CONFIG_PATH = os.path.join(APP_DATA_DIR, CONFIG_FILE_NAME)
LOG_PATH = os.path.join(APP_DATA_DIR, LOG_FILE_NAME)

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
        "status_off": "ВЫКЛ",
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
        "btn_russian": "Я ТОЧНО РУССКИЙ",
        "btn_american": "FKNG AMERICANETS",
        "btn_tests": "ЗАПУСК ТЕСТОВ"
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
        "status_on": "ONs",
        "status_off": "OFF",
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
        "btn_russian": "I AM RUSSIAN",
        "btn_american": "FKNG AMERICANETS",
        "btn_tests": "RUN TESTS"
    }
}

# ======================================================================
# 2. СИСТЕМНЫЕ ФУНКЦИИ
# ======================================================================

def cleanup_old_zapret_folders():
    try:
        ensure_app_data()
        # Перебираем всё, что лежит в папке AppData\Local\ZapretLauncher
        for item in os.listdir(APP_DATA_DIR):
            item_path = os.path.join(APP_DATA_DIR, item)
            
            # Проверяем, что это папка, и что ее имя начинается с нужного префикса, 
            # но при этом она НЕ является нашей текущей рабочей папкой
            if os.path.isdir(item_path) and item.startswith("zapret-discord-youtube") and item != FOLDER_NAME:
                try:
                    # Снимаем атрибуты скрытости/системности, чтобы можно было удалить
                    ctypes.windll.kernel32.SetFileAttributesW(item_path, 128)
                    shutil.rmtree(item_path, ignore_errors=True)
                    log_error(f"Удалена старая папка версии: {item}")
                except Exception as e:
                    log_error(f"Не удалось удалить старую папку {item}: {e}")
    except Exception as e:
        log_error(f"Ошибка при очистке старых папок: {e}")

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def make_hidden(path):
    try:
        if not os.path.exists(path): return
        FILE_ATTRIBUTE_HIDDEN = 0x02
        current_attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        if current_attrs != -1:
            if not (current_attrs & FILE_ATTRIBUTE_HIDDEN):
                ctypes.windll.kernel32.SetFileAttributesW(path, current_attrs | FILE_ATTRIBUTE_HIDDEN)
    except Exception: pass

def ensure_app_data():
    try:
        if not os.path.exists(APP_DATA_DIR):
            os.makedirs(APP_DATA_DIR)
        make_hidden(APP_DATA_DIR)
    except: pass

def log_error(msg):
    try:
        ensure_app_data()
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            # Теперь пишем полный формат: Год-Месяц-День Часы:Минуты:Секунды
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        make_hidden(LOG_PATH)
    except: pass

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
                except:
                    keep_current_block = False # Если дата кривая — не сохраняем
                    
            # Если флаг включен, мы сохраняем и строку с датой, и все многострочные детали ошибки под ней
            if keep_current_block:
                valid_lines.append(line)

        ctypes.windll.kernel32.SetFileAttributesW(LOG_PATH, 128)
        with open(LOG_PATH, 'w', encoding='utf-8') as f:
            f.writelines(valid_lines)
        make_hidden(LOG_PATH)
    except: pass

def migrate_old_files():
    try:
        old_folder = os.path.join(EXE_DIR, FOLDER_NAME)
        old_config = os.path.join(EXE_DIR, CONFIG_FILE_NAME)
        old_log = os.path.join(EXE_DIR, LOG_FILE_NAME)
        if os.path.exists(old_folder):
            try:
                ctypes.windll.kernel32.SetFileAttributesW(old_folder, 128) 
                shutil.rmtree(old_folder, ignore_errors=True)
            except: pass
        if os.path.exists(old_config):
            try: os.remove(old_config)
            except: pass
        if os.path.exists(old_log):
            try: os.remove(old_log)
            except: pass
    except Exception: pass

def enable_debug_privilege():
    try:
        SE_DEBUG_NAME = "SeDebugPrivilege"
        TOKEN_ADJUST_PRIVILEGES = 0x0020
        TOKEN_QUERY = 0x0008
        SE_PRIVILEGE_ENABLED = 0x00000002
        class LUID(ctypes.Structure):
            _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]
        class LUID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", ctypes.c_ulong)]
        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [("PrivilegeCount", ctypes.c_ulong), ("Privileges", LUID_AND_ATTRIBUTES * 1)]
        k32 = ctypes.windll.kernel32
        advapi32 = ctypes.windll.advapi32
        token = ctypes.c_void_p()
        if not advapi32.OpenProcessToken(k32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(token)): return False
        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid)):
            k32.CloseHandle(token); return False
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
        if not advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None):
            k32.CloseHandle(token); return False
        k32.CloseHandle(token)
        return True
    except Exception as e:
        log_error(f"Debug priv error: {e}")
        return False

def get_exe_path():
    """Получает путь к .exe файлу (работает и для .py и для frozen .exe)"""
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return os.path.abspath(sys.argv[0])

def create_shortcut(target_path, shortcut_path, work_dir=None):
    """Создаёт .lnk ярлык Windows"""
    try:
        import pythoncom
        from win32com.shell import shell
        
        if work_dir is None:
            work_dir = os.path.dirname(target_path)
        
        shortcut = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None,
            pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
        )
        
        shortcut.SetPath(target_path)
        shortcut.SetWorkingDirectory(work_dir)
        shortcut.SetDescription("Zapret Launcher")
        shortcut.SetShowCmd(1)  # SW_SHOWNORMAL
        
        persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
        persist_file.Save(shortcut_path, 0)
        
        return True
    except Exception as e:
        log_error(f"Shortcut creation error: {e}")
        return False

def set_autorun(enable):
    try:
        # Папка автозагрузки пользователя
        autostart_folder = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        shortcut_path = os.path.join(autostart_folder, 'Zapret.lnk')
        
        if enable:
            # Ярлык ссылается на Zapret.exe в папке с данными (AppData)
            exe_path = get_autorun_exe_path()
            
            # Создаём ярлык
            create_shortcut(exe_path, shortcut_path)
        else:
            # Удаляем ярлык если есть
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
    except: return False

def get_ping_ms(host):
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        cmd = ["ping", "-n", "1", "-w", "1000", host]
        output = subprocess.check_output(cmd, shell=False, startupinfo=startupinfo, creationflags=0x08000000).decode('cp866', errors='ignore')
        match = re.search(r"(?:время|time)[=<](\d+)", output.lower())
        if match: return int(match.group(1))
        elif "TTL=" in output or "ttl=" in output: return 1 
        else: return -1 
    except Exception: return -1

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

def get_real_ram_usage():
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return str(stat.dwMemoryLoad)
    except: return "00"

def set_volume_max():
    try:
        for _ in range(50):
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
    except: pass

class AudioEngine:
    @staticmethod
    def play_mp3_path(file_path):
        try:
            if not os.path.exists(file_path): return False
            alias = f"mp3_anthem_{random.randint(0, 9999)}"
            ctypes.windll.winmm.mciSendStringW(f'open "{file_path}" type mpegvideo alias {alias}', None, 0, 0)
            ctypes.windll.winmm.mciSendStringW(f"play {alias}", None, 0, 0)
            return True
        except Exception as e:
            log_error(f"Play MP3 Error: {e}")
            return False

    @staticmethod
    def play_mp3(filename):
        try:
            file_path = resource_path(filename)
            if not os.path.exists(file_path): return False 
            alias = f"mp3_{random.randint(0, 9999)}"
            ctypes.windll.winmm.mciSendStringW(f'open "{file_path}" type mpegvideo alias {alias}', None, 0, 0)
            ctypes.windll.winmm.mciSendStringW(f"play {alias}", None, 0, 0)
            return True
        except: return False

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
        except: pass

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
        try:
            self.icon_path = resource_path("icon.ico")
            if os.path.exists(self.icon_path): self.iconbitmap(self.icon_path)
        except: self.icon_path = None
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
        self._bypass_check = "---"     # Детектор: ---, OK, FAIL
        self.changelog_open = False    # Overlay «Что нового»
        
        self.settings_open, self.settings_anim = False, 0.0 
        self.menu_last_active = time.time() # <-- Таймер активности меню
        
        self.mode_menu_open, self.mode_menu_anim, self.menu_scroll_offset = False, 0.0, 0
        self.snow_enabled, self.minimal_mode, self.start_minimized, self.auto_repair = True, False, False, False
        self.auto_restart = False      # Авто-перезапуск при падении службы
        self.proxy_enabled = False     # TgWsProxy: включать при старте
        self.notifications_enabled = True  # Уведомления в системном трее
        self.exe_path = None           # Путь к .exe для автозапуска
        self.theme_name = DEFAULT_THEME
        self.theme_color = self.themes_data[DEFAULT_THEME]
        self.selected_bat, self.favorite_bat = DEFAULT_BAT, None
        self.bat_files = STRATEGY_LIST

        self.zapret_dir = locate_zapret_dir()
        self._refresh_bat_files()
        
        # Копируем .exe в папку с данными (где он должен лежать для автозапуска)
        self.copy_exe_to_appdata()
        
        # Автозапуск всегда ссылается на папку с данными
        set_autorun(True)
        
        threading.Thread(target=self.run_startup_tasks, daemon=True).start()
        
        # --- Переменные прогресса тестирования ---
        self.test_log_line = ""
        self.test_is_running = False 
        self.test_progress = 0
        self.test_total = 1
        self.seen_configs = set()
        self.auto_start_after_test = False
        self.test_eta = ""
        self._test_config_times = []
        self._test_last_progress = 0
        self._test_last_config_time = 0
        self._test_start_time = 0
        # -----------------------------------------

        self.load_config() 
        self.update_msg_timer = 0
        self.update_state = "idle"
        self.remote_version = None
        
        self.autorun_enabled = check_autorun()
        self.update_available, self.is_updating = False, False
        self.mouse_x, self.mouse_y = 0, 0
        self.switch_snow_pos = 1.0 if self.snow_enabled else 0.0
        self.switch_style_pos = 1.0 if self.minimal_mode else 0.0
        self.switch_minimized_pos = 1.0 if self.start_minimized else 0.0
        self.switch_repair_pos = 1.0 if self.auto_repair else 0.0
        self.switch_autorun_pos = 1.0 if self.autorun_enabled else 0.0
        self.switch_autorestart_pos = 1.0 if self.auto_restart else 0.0
        self.switch_proxy_pos = 1.0 if self.proxy_enabled else 0.0
        self.switch_notifications_pos = 1.0 if self.notifications_enabled else 0.0
        try:
            self.synth_on = AudioEngine.create_click_sound(150, 600, duration_ms=40, volume=0.3)
            self.synth_off = AudioEngine.create_click_sound(500, 100, duration_ms=60, volume=0.3)
        except: self.synth_on, self.synth_off = None, None
        self.warp_particles = [WarpParticle() for _ in range(600)]
        self.snowflakes = [SnowFlake(WINDOW_WIDTH, WINDOW_HEIGHT) for _ in range(90)]
        self.current_warp_speed = 2.5
        self.viz_bars = [random.uniform(0.1, 0.8) for _ in range(8)]
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click) 
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

    def setup_tray(self):
        try:
            icon_img = None
            try:
                if self.icon_path and os.path.exists(self.icon_path):
                    icon_img = Image.open(self.icon_path)
            except: pass
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
                    except: pass
                    time.sleep(1)
            threading.Thread(target=_update_tray_title, daemon=True).start()
            self.tray_icon = pystray.Icon("ZapretLauncher", icon_img, "Zapret Launcher", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            log_error(f"Tray setup error: {e}")

    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey("ctrl+shift+z", lambda: threading.Thread(target=self.toggle_system, daemon=True).start())
        except Exception as e:
            log_error(f"Hotkey setup error: {e}")

    def run_startup_tasks(self):
        try:
            ensure_app_data()
            cleanup_old_logs() 
            cleanup_old_zapret_folders() # <--- Добавили очистку старых папок Запрета
            migrate_old_files()
            self.cleanup_old_exe() 
            enable_debug_privilege()
            self.check_and_install_files() 
            
            # При первом запуске копируем .exe в папку с данными для автозапуска
            if getattr(self, 'is_first_run', False):
                self.copy_exe_to_appdata()
            
            self.after(0, self._refresh_bat_files) 
            if getattr(self, 'is_first_run', False):
                self.after(2000, self.run_service_tests)
            elif self.autorun_enabled:
                self.after(2000, self.start_process_logic)
        except Exception as e:
            log_error(f"Startup Tasks Error: {e}")

    def cleanup_old_exe(self):
        try:
            temp_dir = os.environ.get('TEMP', os.path.expanduser('~'))
            vbs_path = os.path.join(temp_dir, "updater.vbs")
            bat_path = os.path.join(temp_dir, "updater.bat")
            if os.path.exists(vbs_path):
                try: os.remove(vbs_path)
                except: pass
            if os.path.exists(bat_path):
                try: os.remove(bat_path)
                except: pass
                
            old_exe = os.path.abspath(sys.executable) + ".old"
            if os.path.exists(old_exe):
                try: os.remove(old_exe)
                except: pass
        except: pass

    def copy_exe_to_appdata(self):
        """Копирует .exe в папку с данными для автозапуска"""
        try:
            src_exe = get_autorun_exe_path()
            dst_exe = get_autorun_exe_path()
            
            # Если .exe уже есть в папке с данными, не копируем
            if os.path.exists(src_exe):
                return
            
            # Определяем текущий путь к .exe
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                current_exe = os.path.abspath(sys.argv[0])
            
            # Копируем в папку с данными
            dst_dir = os.path.dirname(dst_exe)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            
            shutil.copy2(current_exe, dst_exe)
            log_error(f"Копировано .exe в папку с данными: {dst_exe}")
        except Exception as e:
            log_error(f"Ошибка копирования .exe: {e}")


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
                files = [f for f in os.listdir(self.zapret_dir) if f.endswith('.bat') and 'service' not in f.lower()]
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
            # Пинг обновляем раз в 5 секунд — не грузим сеть
            ping_counter += 1
            if ping_counter >= 5:
                ping_counter = 0
                try:
                    ms = get_ping_ms("8.8.8.8")
                    self.hud_values["PING"] = f"{ms}ms" if ms >= 0 else "---"
                except:
                    self.hud_values["PING"] = "---"
            time.sleep(1)

    def watchdog_loop(self):
        """Следит за тем, жива ли служба winws.exe. Если упала — сбрасывает статус."""
        while getattr(self, '_watchdog_running', True):
            try:
                if self.launcher_status == "ON":
                    alive = any(
                        p.info['name'].lower() == 'winws.exe'
                        for p in psutil.process_iter(['name'])
                        if p.info['name']
                    )
                    if not alive:
                        log_error("Watchdog: winws.exe не найден — служба упала")
                        if getattr(self, 'auto_restart', False):
                            log_error("Watchdog: auto-restart включён, перезапускаю службу")
                            self.launcher_status = "BUSY"
                            threading.Thread(target=self.start_process_logic, daemon=True).start()
                        else:
                            log_error("Watchdog: auto-restart отключён, сбрасываю статус")
                            self.launcher_status = "OFF"
                            self.status_text = self.get_text("status_ready")
                            if self.notifications_enabled:
                                try: self.tray_icon.notify("Обход упал!", "Zapret Launcher")
                                except: pass
                    else:
                        self._total_uptime_sec += 5
                        self._save_stats()
                else:
                    self._total_uptime_sec += 5
                    self._save_stats()
                
                if self.proxy_status == "ON" and self._proxy_process:
                    if self._proxy_process.poll() is not None:
                        log_error("Proxy watchdog: TgWsProxy завершился")
                        self.proxy_status = "OFF"
                        self._proxy_process = None
            except Exception as e:
                log_error(f"Watchdog error: {e}")
            time.sleep(5)

    def bypass_check_loop(self):
        """Периодически проверяет работает ли обход: пингует discord.com."""
        while True:
            try:
                if self.launcher_status == "ON":
                    ms = get_ping_ms("discord.com")
                    self._bypass_check = "OK" if ms >= 0 else "FAIL"
                else:
                    self._bypass_check = "---"
            except:
                self._bypass_check = "---"
            time.sleep(30)  # Проверка раз в 30 секунд

    def _load_stats(self):
        try:
            stats_path = os.path.join(APP_DATA_DIR, "stats.json")
            if os.path.exists(stats_path):
                with open(stats_path, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    self._total_uptime_sec = d.get("uptime_sec", 0)
                    self._launch_count = d.get("launches", 0)
        except: pass

    def _save_stats(self):
        try:
            ensure_app_data()
            stats_path = os.path.join(APP_DATA_DIR, "stats.json")
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump({"uptime_sec": self._total_uptime_sec, "launches": self._launch_count}, f)
        except: pass

    # --- TgWsProxy методы ---
    def start_proxy(self):
        try:
            # Убиваем старые зависшие процессы прокси, чтобы освободить порт
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.call(f'taskkill /F /IM {TGWS_PROXY_EXE}', shell=True, startupinfo=si, creationflags=0x08000000)
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
                except: pass
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
            subprocess.call(f'taskkill /F /IM {TGWS_PROXY_EXE}', shell=True, startupinfo=si, creationflags=0x08000000)
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
                    make_hidden(CONFIG_PATH)
                    self.load_config()
                    self.play_sound("ON")
                    log_error(f"Конфиг импортирован: {path}")
        except Exception as e:
            log_error(f"Import config error: {e}")

    def toggle_compact_mode(self):
        """Мини-оверлей: маленькое окно поверх всех."""
        self.compact_mode = not self.compact_mode
        self.play_sound("ON")
        if self.compact_mode:
            self.attributes("-topmost", True)
            self.geometry("220x50")
            self.resizable(False, False)
        else:
            self.attributes("-topmost", False)
            ws = self.winfo_screenwidth()
            self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{(ws - WINDOW_WIDTH)//2}+{(self.winfo_screenheight()-WINDOW_HEIGHT)//2}")
            self.resizable(True, True)

    def check_and_install_files(self):
        if not os.path.exists(self.zapret_dir): self.install_files(self.zapret_dir)
        else: make_hidden(self.zapret_dir)

    def install_files(self, dest_path):
        def _worker():
            self.status_text = self.get_text("status_installing")
            self.launcher_status = "BUSY"
            try:
                zip_path = resource_path(DATA_ARCHIVE_NAME)
                if os.path.exists(zip_path):
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(APP_DATA_DIR)
                    make_hidden(dest_path)
                    self.status_text = self.get_text("status_ready")
                    self.launcher_status = "OFF"
                    self._refresh_bat_files()
                else: 
                    self.status_text = self.get_text("status_no_file")
                    self.launcher_status = "OFF"
            except: 
                self.status_text = self.get_text("status_error")
                self.launcher_status = "OFF"
        threading.Thread(target=_worker, daemon=True).start()

    def get_text(self, key):
        lang_dict = self.translations_data.get(self.current_lang, self.translations_data["EN"])
        return lang_dict.get(key, key)

    def load_config(self):
        self.is_first_run = not os.path.exists(CONFIG_PATH)
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                    self.snow_enabled = data.get("snow", True)
                    self.minimal_mode = data.get("minimal", False)
                    self.start_minimized = data.get("minimized", False)
                    self.auto_repair = data.get("repair", False)
                    self.auto_restart = data.get("auto_restart", False)
                    self.proxy_enabled = data.get("proxy_enabled", False)
                    self.notifications_enabled = data.get("notifications", True)
                    self.theme_name = data.get("theme", DEFAULT_THEME)
                    self.theme_color = self.themes_data.get(self.theme_name, self.themes_data[DEFAULT_THEME])
                    self.selected_bat = data.get("bat", self.bat_files[0] if self.bat_files else DEFAULT_BAT)
                    self.favorite_bat = data.get("fav", None)
                    self.current_lang = data.get("lang", "RU")
                    self.exe_path = data.get("exe_path", None)
        except: pass

    def save_config(self):
        try:
            ensure_app_data()
            if os.path.exists(CONFIG_PATH):
                ctypes.windll.kernel32.SetFileAttributesW(CONFIG_PATH, 128) 
                
            with open(CONFIG_PATH, 'w') as f:
                json.dump({
                    "snow": self.snow_enabled, 
                    "minimal": self.minimal_mode, 
                    "minimized": self.start_minimized, 
                    "repair": self.auto_repair,
                    "auto_restart": self.auto_restart,
                    "proxy_enabled": self.proxy_enabled,
                    "notifications": self.notifications_enabled,
                    "theme": self.theme_name, 
                    "bat": self.selected_bat, 
                    "fav": self.favorite_bat, 
                    "lang": self.current_lang,
                    "exe_path": getattr(self, 'exe_path', None)
                }, f)
            make_hidden(CONFIG_PATH) 
        except Exception as e:
            log_error(f"Save config error: {e}")

    def _locate_zapret_dir(self):
        return locate_zapret_dir()

    def play_sound(self, effect_type):
        def _play():
            try:
                sound = self.synth_on if effect_type == "ON" else self.synth_off
                if sound: winsound.PlaySound(sound, winsound.SND_MEMORY)
            except: pass
        threading.Thread(target=_play, daemon=True).start()

    def play_russian_anthem(self):
        threading.Thread(target=set_volume_max, daemon=True).start()
        def _play():
            if self.zapret_dir and os.path.exists(self.zapret_dir):
                file_path = os.path.join(self.zapret_dir, RUSSIAN_ANTHEM_FILE)
                if os.path.exists(file_path): AudioEngine.play_mp3_path(file_path)
                else: log_error(f"Anthem file not found: {file_path}")
        threading.Thread(target=_play, daemon=True).start()

    def play_american_anthem(self):
        threading.Thread(target=set_volume_max, daemon=True).start()
        def _play():
            if self.zapret_dir and os.path.exists(self.zapret_dir):
                file_path = os.path.join(self.zapret_dir, AMERICAN_ANTHEM_FILE)
                if os.path.exists(file_path): AudioEngine.play_mp3_path(file_path)
                else: log_error(f"American file not found: {file_path}")
        threading.Thread(target=_play, daemon=True).start()

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
        self.test_is_running = True 
        
        self.test_progress = 0
        self.test_total = len(self.bat_files) if self.bat_files else 1
        self.seen_configs = set()
        self.auto_start_after_test = False
        self.test_log_line = "Запуск PowerShell..."
        self.test_eta = ""
        self._test_config_times = []
        self._test_last_progress = 0
        self._test_last_config_time = time.time()
        self._test_start_time = time.time()

        def background_worker():
            process = None
            try:
                # Настраиваем скрытый запуск
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

                cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1_path]
                
                # Запускаем процесс, перехватывая ввод и вывод
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    startupinfo=si,
                    creationflags=0x08000000,
                    text=True,
                    encoding='cp866', # Кодировка консоли Windows по умолчанию
                    errors='replace'
                )

                # Программно отвечаем на запросы Read-Host из скрипта
                # 1 - Standard tests, 1 - All configs
                process.stdin.write("1\n1\n")
                process.stdin.flush()

                best_config = None

                # Читаем вывод PowerShell построчно в реальном времени
                for line in iter(process.stdout.readline, ''):
                    if not getattr(self, "test_is_running", False):
                        break # Если нужно прервать тест

                    line = line.strip()
                    if not line: continue

                    # ---- ДОБАВЬ ВОТ ЭТУ СТРОКУ ДЛЯ ОТЛАДКИ В ТЕРМИНАЛЕ ----
                    print(f"[PowerShell] {line}")
                    # -------------------------------------------------------

                    # Убираем возможные ANSI-коды цветов
                    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                    self.test_log_line = clean_line

                    # Обновляем прогресс по паттерну [X/Y] из вывода PowerShell
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
                            
                            # Расчёт ETA
                            if self._test_config_times:
                                avg_time = sum(self._test_config_times) / len(self._test_config_times)
                                remaining = (new_total - new_progress) * avg_time
                                if remaining > 60:
                                    self.test_eta = f"~{int(remaining//60)}м {int(remaining%60)}с"
                                else:
                                    self.test_eta = f"~{int(remaining)}с"

                    # Отлавливаем результат
                    if "Best config:" in clean_line and best_config is None:
                        config_name = clean_line.split("Best config:")[-1].strip()
                        
                        matched_file = None
                        for f in self.bat_files:
                            if f.lower() == config_name.lower() or config_name.replace(".bat", "").lower() in f.lower():
                                matched_file = f
                                break
                                
                        if matched_file:
                            best_config = matched_file
                            self.selected_bat = best_config
                            self.favorite_bat = best_config
                            self.save_config()
                            self.auto_start_after_test = True
                            self.after(0, self._refresh_bat_files)
                            
                            # Нашли лучший конфиг — убиваем процесс, чтобы не ждать [System.Console]::ReadKey
                            process.terminate()
                            break

            except Exception as e:
                log_error(f"Silent test error: {e}")
            finally:
                # Гарантированное закрытие процесса
                if process:
                    try: process.terminate()
                    except: pass
                
                self.test_is_running = False
                self.launcher_status = "OFF"
                self.status_text = self.get_text("status_ready")
                self.test_log_line = ""
                self.test_eta = ""
                
                # Сохраняем историю тестов
                duration = time.time() - self._test_start_time
                self._save_test_history(best_config, duration)
                
                # Запускаем найденную стратегию, если нужно
                if getattr(self, 'auto_start_after_test', False):
                    self.auto_start_after_test = False
                    self.after(1000, self.toggle_system) 
                else:
                    self.after(0, lambda: self.play_sound("ON"))

        # Запускаем в отдельном потоке, чтобы интерфейс не зависал
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
                except: history = []
            
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
            def to_rgb(c):
                if len(c) == 4: c = "#" + "".join([x*2 for x in c[1:]])
                return tuple(int(c.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            r1, g1, b1 = to_rgb(c1)
            r2, g2, b2 = to_rgb(c2)
            r, g, b = int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t)
            return '#%02x%02x%02x' % (max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))
        except: return c1

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
        """Checks GitHub for a new version. Robust SSL + timeout handling."""
        def _try_fetch(url, timeout=8):
            """Try with SSL, then without if any error."""
            try:
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(url, context=ctx, timeout=timeout) as r:
                    return r.read()
            except Exception:
                pass
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(url, context=ctx, timeout=timeout) as r:
                    return r.read()
            except Exception as e:
                raise e

        try:
            raw = _try_fetch(UPDATE_VERSION_URL)
            data = json.loads(raw.decode('utf-8'))
            remote_ver = data.get("version", "").strip()
            self.update_data = data

            def _ver_tuple(v):
                try: return tuple(int(x) for x in v.split('.'))
                except: return (0,)

            if remote_ver and _ver_tuple(remote_ver) > _ver_tuple(CURRENT_VERSION):
                self.update_available = True
                self.remote_version = remote_ver
                self.update_state = "available"
                if not silent and self.notifications_enabled:
                    try: self.tray_icon.notify(f"Обновление v{remote_ver}", "Нажмите чтобы установить")
                    except: pass
            else:
                self.update_available = False
                self.remote_version = None
                self.update_state = "up_to_date"
        except Exception as e:
            self.update_state = "failed"
            log_error(f"Check update error: {e}")

    def on_mouse_move(self, event): 
        self.mouse_x, self.mouse_y = event.x, event.y
        if getattr(self, 'settings_open', False):
            if event.x > self.canvas.winfo_width() - self.s(280):
                self.menu_last_active = time.time()

    def on_right_click(self, event):
        s = self.s
        w = self.canvas.winfo_width()
        if self.settings_open and event.x > w - s(260) and s(540) <= event.y < s(580):
            self.play_sound("ON")

    def run_logs_console(self):
        if not os.path.exists(LOG_PATH):
             with open(LOG_PATH, 'w', encoding='utf-8') as f:
                 f.write("[LOG START]\nNo previous logs found.\n")
        make_hidden(LOG_PATH) 
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
                            if attr == 'autorun_enabled': 
                                if set_autorun(val): self.switch_autorun_pos = 1.0 if val else 0.0
                            elif attr == 'notifications_enabled': self.switch_notifications_pos = 1.0 if val else 0.0
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
                
                # Ряд 5: Уведомления (Y=415..485)
                if mx+s(20) <= event.x <= mx+s(125) and s(415) <= event.y <= s(485):
                    self.notifications_enabled = not self.notifications_enabled
                    self.save_config()
                    self.play_sound("ON" if self.notifications_enabled else "OFF")
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
                        self.update_msg_text = self.get_text("update_check")
                        threading.Thread(target=self.check_for_updates, args=(False,), daemon=True).start()
                        self.play_sound("ON")
                    return

                # Клик на версию — открыть changelog
                if mx+s(70) <= event.x <= mx+s(190) and h-s(20) <= event.y <= h-s(2):
                    if not self.update_available:
                        self.changelog_open = True
                        self.play_sound("ON")
                        return

                return
            self.settings_open = False; return
        
        # Кнопка СТОП при тестировании
        if self.launcher_status == "TESTING":
            stop_y = cy + s(65)
            if abs(event.x - cx) < s(40) and abs(event.y - stop_y) < s(12):
                self.test_is_running = False
                self.play_sound("OFF")
                return
        
        if math.sqrt((event.x-cx)**2 + (event.y-cy)**2) < s(165) and self.launcher_status != "BUSY":
            threading.Thread(target=self.toggle_system, daemon=True).start()

    def toggle_system(self):
        old = self.launcher_status
        if old == "TESTING": return 
        
        self.status_text = self.get_text("status_busy") if old != "BUSY" else "..."
        self.launcher_status = "BUSY"
        time.sleep(0.2)
        if old == "ON": self.stop_process_logic()
        else: self.start_process_logic()

    def _hot_switch_strategy(self):
        """Атомарная смена стратегии без ручного стоп/старт — работает пока статус ON."""
        self.launcher_status = "BUSY"
        self.status_text = self.get_text("status_busy")
        self.stop_process_logic()
        time.sleep(0.5)
        self.start_process_logic()

    def install_zapret_service(self, bat_path):
        try:
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = subprocess.SW_HIDE
            
            # 1. Сначала удаляем старую службу (с небольшой паузой, чтобы Windows успела её "забыть")
            subprocess.call("net stop zapret", shell=True, startupinfo=si, creationflags=0x08000000)
            subprocess.call("sc delete zapret", shell=True, startupinfo=si, creationflags=0x08000000)
            subprocess.call('taskkill /F /IM "winws.exe"', shell=True, startupinfo=si, creationflags=0x08000000)
            time.sleep(0.5) 
            
            # 2. Читаем выбранный пользователем .bat файл
            # Пробуем utf-8, если не получается — fallback на cp1251 (стандартная кодировка Windows)
            try:
                with open(bat_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(bat_path, 'r', encoding='cp1251', errors='replace') as f:
                    content = f.read()
            
            # Склеиваем длинные команды, разорванные символом переноса (^)
            content = re.sub(r'\^\s*\n', ' ', content)
            
            args_str = ""
            for line in content.split('\n'):
                # Игнорируем закомментированные строки (rem или ::)
                if 'winws.exe' in line.lower() and not line.strip().lower().startswith(('rem', '::')):
                    match = re.search(r'winws\.exe["\']?\s+(.*)', line, re.IGNORECASE)
                    if match:
                        args_str = match.group(1).strip()
                        break
            
            if not args_str:
                log_error(f"Не удалось найти аргументы winws в файле {bat_path}")
                return False
                
            # 3. Превращаем переменные батника в абсолютные пути
            zapret_dir_slash = self.zapret_dir + "\\"
            args_str = args_str.replace('%~dp0', zapret_dir_slash)
            args_str = args_str.replace('%%BIN%%', zapret_dir_slash + "bin\\")
            args_str = args_str.replace('%BIN%', zapret_dir_slash + "bin\\")
            args_str = args_str.replace('%%LISTS%%', zapret_dir_slash + "lists\\")
            args_str = args_str.replace('%LISTS%', zapret_dir_slash + "lists\\")
            
            # ПРАВИЛЬНАЯ подстановка игровых фильтров (как в оригинале - 12)
            args_str = re.sub(r'%%?GameFilter(TCP|UDP)?%%?', '12', args_str, flags=re.IGNORECASE)
            
            # Убираем возможные остатки знаков переноса и лишние пробелы
            args_str = args_str.replace('^', '')
            args_str = re.sub(r'\s+', ' ', args_str)
            
            # Экранируем кавычки для системной утилиты sc
            args_str = args_str.replace('"', '\\"')
            
            bin_path = os.path.join(self.zapret_dir, 'bin', 'winws.exe')
            
            # 4. Формируем команду регистрации Службы Windows
            cmd_create = f'sc create zapret binPath= "\\"{bin_path}\\" {args_str}" DisplayName= "zapret" start= auto'
            
            # Создаем службу
            subprocess.call(cmd_create, shell=True, startupinfo=si, creationflags=0x08000000)
            subprocess.call('sc description zapret "Zapret DPI bypass software"', shell=True, startupinfo=si, creationflags=0x08000000)
            
            # 5. Делаем запись в реестр, чтобы оригинальный service.bat видел статус
            bat_name = os.path.basename(bat_path).replace(".bat", "")
            cmd_reg = f'reg add "HKLM\\System\\CurrentControlSet\\Services\\zapret" /v zapret-discord-youtube /t REG_SZ /d "{bat_name}" /f'
            subprocess.call(cmd_reg, shell=True, startupinfo=si, creationflags=0x08000000)
            
            # Запускаем службу
            res = subprocess.call("sc start zapret", shell=True, startupinfo=si, creationflags=0x08000000)
            time.sleep(0.5)
            is_running = any(p.name().lower() == "winws.exe" for p in psutil.process_iter(['name']))
            return (res == 0 or is_running)
            
        except Exception as e:
            log_error(f"Ошибка установки службы: {e}")
            return False

    def launch_winws_direct(self, bat_path):
        """Резервный запуск winws.exe напрямую процессом, если служба Windows недоступна."""
        try:
            try:
                with open(bat_path, 'r', encoding='utf-8') as f: content = f.read()
            except UnicodeDecodeError:
                with open(bat_path, 'r', encoding='cp1251', errors='replace') as f: content = f.read()
            
            content = re.sub(r'\^\s*\n', ' ', content)
            args_str = ""
            for line in content.split('\n'):
                if 'winws.exe' in line.lower() and not line.strip().lower().startswith(('rem', '::')):
                    match = re.search(r'winws\.exe["\']?\s+(.*)', line, re.IGNORECASE)
                    if match:
                        args_str = match.group(1).strip()
                        break
            
            if not args_str: return False

            zapret_dir_slash = self.zapret_dir + "\\"
            args_str = args_str.replace('%~dp0', zapret_dir_slash)
            args_str = args_str.replace('%%BIN%%', zapret_dir_slash + "bin\\")
            args_str = args_str.replace('%BIN%', zapret_dir_slash + "bin\\")
            args_str = args_str.replace('%%LISTS%%', zapret_dir_slash + "lists\\")
            args_str = args_str.replace('%LISTS%', zapret_dir_slash + "lists\\")
            args_str = re.sub(r'%%?GameFilter(TCP|UDP)?%%?', '12', args_str, flags=re.IGNORECASE)
            args_str = args_str.replace('^', '')
            args_str = re.sub(r'\s+', ' ', args_str)

            bin_path = os.path.join(self.zapret_dir, 'bin', 'winws.exe')
            if not os.path.exists(bin_path): return False

            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.call('taskkill /F /IM "winws.exe"', shell=True, startupinfo=si, creationflags=0x08000000)
            time.sleep(0.3)

            cmd_str = f'"{bin_path}" {args_str}'
            subprocess.Popen(cmd_str, cwd=self.zapret_dir, startupinfo=si, creationflags=0x08000000, shell=True)
            time.sleep(0.8)
            return any(p.name().lower() == "winws.exe" for p in psutil.process_iter(['name']))
        except Exception as e:
            log_error(f"launch_winws_direct error: {e}")
            return False

    def _install_files_sync(self, dest_path):
        self.status_text = self.get_text("status_installing")
        self.launcher_status = "BUSY"
        try:
            zip_path = resource_path(DATA_ARCHIVE_NAME)
            if os.path.exists(zip_path):
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(APP_DATA_DIR)
                make_hidden(dest_path)
                self._refresh_bat_files()
                return True
            else:
                log_error(f"Архив не найден: {zip_path}")
                return False
        except Exception as e:
            log_error(f"Install sync error: {e}")
            return False

    def start_process_logic(self):
        self.zapret_dir = locate_zapret_dir()
        if self.auto_repair:
             si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = subprocess.SW_HIDE
             subprocess.call("ipconfig /flushdns & netsh interface ip delete arpcache", shell=True, startupinfo=si, creationflags=0x08000000)
        
        # Если папки нет или она пуста (нет winws.exe), распаковываем файлы синхронно
        if not os.path.exists(self.zapret_dir) or not os.path.exists(os.path.join(self.zapret_dir, "bin", "winws.exe")): 
            success = self._install_files_sync(self.zapret_dir)
            if not success:
                self.launcher_status, self.status_text = "OFF", self.get_text("status_no_file")
                return

        if not self.selected_bat or self.selected_bat not in self.bat_files:
            self._refresh_bat_files()

        bat_path = os.path.join(self.zapret_dir, self.selected_bat)
        if not os.path.exists(bat_path):
            bats = [f for f in os.listdir(self.zapret_dir) if f.endswith('.bat') and 'service' not in f.lower()]
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
                self._launch_count += 1
                self._save_stats()
                self.play_sound("ON")
                if self.notifications_enabled:
                    try: self.tray_icon.notify("Обход включён", "Zapret Launcher")
                    except: pass
            else:
                self.launcher_status, self.status_text = "OFF", self.get_text("status_error")
        else: 
            self.check_and_install_files()
            self.launcher_status, self.status_text = "OFF", self.get_text("status_no_file")

    def stop_process_logic(self):
        si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = subprocess.SW_HIDE
        
        # 1. Корректно останавливаем и удаляем главную службу
        subprocess.call("net stop zapret", shell=True, startupinfo=si, creationflags=0x08000000)
        subprocess.call("sc delete zapret", shell=True, startupinfo=si, creationflags=0x08000000)
        
        # 2. На всякий случай сносим драйвер WinDivert (как советует оригинальный скрипт Запрета)
        subprocess.call("net stop WinDivert", shell=True, startupinfo=si, creationflags=0x08000000)
        subprocess.call("sc delete WinDivert", shell=True, startupinfo=si, creationflags=0x08000000)
        subprocess.call("net stop WinDivert14", shell=True, startupinfo=si, creationflags=0x08000000)
        subprocess.call("sc delete WinDivert14", shell=True, startupinfo=si, creationflags=0x08000000)
        
        # 3. Контрольный выстрел по всем остаткам процессов
        for target in TARGET_PROCESSES: 
            subprocess.call(f'taskkill /F /IM "{target}"', shell=True, startupinfo=si, creationflags=0x08000000)
        
        self.launcher_status, self.status_text = "OFF", self.get_text("status_ready")
        self.play_sound("OFF")
        if self.notifications_enabled:
            try: self.tray_icon.notify("Обход выключен", "Zapret Launcher")
            except: pass

    def render_loop(self):
        try:
            self.canvas.delete("all")
            self.animation_step += 1
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            w, h = (cw if cw > 10 else WINDOW_WIDTH), (ch if ch > 10 else WINDOW_HEIGHT)
            self.ui_scale = min(w / WINDOW_WIDTH, h / WINDOW_HEIGHT)
            if self.ui_scale < 0.1: self.ui_scale = 0.1
            s = self.s 
            fs = self.fs 

            cx, cy = w/2, h/2
            
            # --- ЛОГИКА ТАЙМЕРА ЗАКРЫТИЯ МЕНЮ (10 СЕКУНД) ---
            if self.settings_open and (time.time() - getattr(self, 'menu_last_active', 0) > 10.0):
                self.settings_open = False
                self.mode_menu_open = False
            # -----------------------------------------------

            if self.update_msg_timer > 0: self.update_msg_timer -= 1
            
            def lerp(curr, target, factor=0.4): return curr + (target - curr) * factor
            self.switch_snow_pos = lerp(self.switch_snow_pos, 1.0 if self.snow_enabled else 0.0)
            self.switch_style_pos = lerp(self.switch_style_pos, 1.0 if self.minimal_mode else 0.0)
            self.switch_autorun_pos = lerp(self.switch_autorun_pos, 1.0 if self.autorun_enabled else 0.0)
            self.switch_minimized_pos = lerp(self.switch_minimized_pos, 1.0 if self.start_minimized else 0.0)
            self.switch_repair_pos = lerp(self.switch_repair_pos, 1.0 if self.auto_repair else 0.0)
            self.switch_autorestart_pos = lerp(self.switch_autorestart_pos, 1.0 if self.auto_restart else 0.0)
            self.switch_proxy_pos = lerp(self.switch_proxy_pos, 1.0 if self.proxy_status == "ON" else 0.0)
            
            self.settings_anim = lerp(self.settings_anim, 1.0 if self.settings_open else 0.0, factor=0.08)
            self.mode_menu_anim = lerp(self.mode_menu_anim, 1.0 if self.mode_menu_open else 0.0, factor=0.12)
            
            self.current_warp_speed = lerp(self.current_warp_speed, 45.0 if self.launcher_status == "ON" else 2.5, 0.05)
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
                grid_speed = (self.animation_step * 1.0) % spacing
                
                for i in range(-60, 61):
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
                bypass_txt = f"\u2713 WORK" if self._bypass_check == "OK" else ("\u2717 FAIL" if self._bypass_check == "FAIL" else "CHECK...")
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
            log_error(f"Render Error: {e}")
        finally: 
            self.after(20, self.render_loop)

    def perform_update(self):
        if self.is_updating: return
        self.is_updating, self.update_state = True, "downloading"

        if not self.update_data:
            self.is_updating = False
            self.update_state = "failed"
            return

        target_url = self.update_data.get("download_url")
        target_hash = self.update_data.get("hash")

        def _fetch(url, dest):
            """Download with chunked progress + SSL fallback on any error."""
            for verify in (True, False):
                try:
                    ctx = ssl.create_default_context()
                    if not verify:
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(
                        url, headers={"User-Agent": f"ZapretLauncher/{CURRENT_VERSION}"}
                    )
                    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp, \
                         open(dest, 'wb') as out:
                        total = int(resp.headers.get('Content-Length', 0))
                        done = 0
                        while True:
                            chunk = resp.read(65536)
                            if not chunk: break
                            out.write(chunk)
                            done += len(chunk)
                            if total > 0:
                                self.update_state = f"dl_{int(done*100/total)}"
                        out.flush()
                    return
                except Exception as e:
                    if verify:
                        log_error(f"Download SSL=True failed: {e}, retrying without verify")
                        continue
                    raise

        def _upd():
            try:
                temp_dir = os.environ.get('TEMP', os.path.expanduser('~'))
                upd_exe  = os.path.join(temp_dir, "Zapret_Update.exe")
                upd_bat  = os.path.join(temp_dir, "zapret_updater.bat")

                _fetch(target_url, upd_exe)
                self.update_state = "verifying"

                # Hash verification
                if target_hash:
                    h = hashlib.sha256()
                    with open(upd_exe, "rb") as f:
                        for block in iter(lambda: f.read(65536), b""):
                            h.update(block)
                    if h.hexdigest().lower() != target_hash.lower():
                        self.is_updating = False
                        self.update_state = "hash_fail"
                        try: os.remove(upd_exe)
                        except: pass
                        log_error(f"Hash mismatch: expected {target_hash}, got {h.hexdigest()}")
                        return

                # Determine current exe (works in both frozen .exe and dev .py)
                cur_exe = sys.executable if getattr(sys, 'frozen', False) \
                          else os.path.abspath(sys.argv[0])

                # Get 8.3 short path to avoid Cyrillic/Unicode in bat file
                # GetShortPathNameW returns ASCII-safe path (e.g. C:\Users\ПАПКИ~1 -> C:\USERS\PAPKI~1)
                def _short_path(path):
                    try:
                        buf = ctypes.create_unicode_buffer(512)
                        ctypes.windll.kernel32.GetShortPathNameW(path, buf, 512)
                        return buf.value if buf.value else path
                    except Exception:
                        return path

                cur_exe_s = _short_path(cur_exe)
                upd_exe_s = _short_path(upd_exe)

                # Bat written in cp866 — OEM code page that cmd.exe actually uses
                bat = (
                    "@echo off\r\n"
                    "ping 127.0.0.1 -n 4 > nul\r\n"
                    ":retry\r\n"
                    f'del /f /q "{cur_exe_s}" > nul 2>&1\r\n'
                    f'if exist "{cur_exe_s}" goto retry\r\n'
                    f'move /y "{upd_exe_s}" "{cur_exe_s}" > nul\r\n'
                    f'start "" "{cur_exe_s}"\r\n'
                    'del "%~f0"\r\n'
                )
                with open(upd_bat, "w", encoding="cp866") as f:
                    f.write(bat)

                try: winsound.PlaySound(None, winsound.SND_PURGE)
                except: pass

                # ShellExecuteW runas — does NOT depend on .bat file association
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "cmd.exe",
                    f'/c "{upd_bat}"',
                    None, 0  # SW_HIDE
                )
                os._exit(0)

            except Exception as e:
                self.is_updating = False
                self.update_state = "failed"
                log_error(f"perform_update error: {e}")

        threading.Thread(target=_upd, daemon=True).start()

if __name__ == "__main__":
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "ZapretLauncherSingleInstanceMutex")
    if ctypes.windll.kernel32.GetLastError() == 183:
        sys.exit(0)
        
    if is_admin():
        try:
            app_launcher = ZapretLauncher()
            
            # --- ИСПРАВЛЕННОЕ ЗАКРЫТИЕ ОКНА ---
            def on_closing():
                # 1. Мгновенно скрываем окно (пользователь думает, что программа закрылась)
                app_launcher.withdraw()
                # 2. Спокойно и до конца удаляем все службы (без фоновых потоков, чтобы Python дождался конца)
                app_launcher.stop_process_logic()
                # 3. Уничтожаем окно и завершаем процесс
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
