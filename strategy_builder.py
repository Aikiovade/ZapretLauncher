"""Конструктор стратегий (17.5): разбор winws-аргументов, правка, валидация, сборка .bat.

Модуль не зависит от UI и ядра: только строки и файлы, чтобы им пользовались
Tk-версия, web-версия и тесты. Все значения проверяются по вайтлисту флагов;
неизвестные флаги сохраняются как есть, но проходят общие ограничения.
"""
from __future__ import annotations

import json
import os
import re
import zipfile
from dataclasses import dataclass, field

CUSTOM_PREFIX = "custom_"
CUSTOM_TAG = "custom"
MAX_NAME_LEN = 40
MAX_VALUE_LEN = 512
MAX_BUNDLE_BYTES = 524288

_FLAG_NAME_RE = re.compile(r"^--[a-z0-9][a-z0-9\-_]*$")
_NAME_RE = re.compile(r"^[\w \-().]+$", re.UNICODE)
_FORBIDDEN_RE = re.compile(r"[&|<>^\"'\x00-\x1f\x7f]")
_PLACEHOLDER_RE = re.compile(r"%(?:~dp0|BIN|LISTS|GameFilterTCP|GameFilterUDP|GameFilter)%", re.IGNORECASE)
_PORTS_RE = re.compile(r"^[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*$")
_DOMAINS_RE = re.compile(r"^[0-9a-zA-Z\-\.,_\*]+$")


def _spec(kind, **kw):
    spec = {"kind": kind}
    spec.update(kw)
    return spec


KNOWN_FLAGS = {
    "--wf-tcp": _spec("ports"),
    "--wf-udp": _spec("ports"),
    "--filter-tcp": _spec("ports"),
    "--filter-udp": _spec("ports"),
    "--filter-l3": _spec("enum_csv", choices=("ip4", "ip6"), max_items=4),
    "--filter-l7": _spec("enum_csv", choices=("http", "tls", "quic", "discord", "stun", "dht", "unknown"), max_items=5),
    "--hostlist": _spec("path", multi=True),
    "--hostlist-domains": _spec("domains", multi=True),
    "--hostlist-exclude": _spec("path", multi=True),
    "--hostlist-auto": _spec("path"),
    "--hostlist-auto-retrans-threshold": _spec("int", minimum=1, maximum=100),
    "--hostlist-auto-retrans-time": _spec("int", minimum=1, maximum=3600),
    "--hostlist-auto-fail-threshold": _spec("int", minimum=1, maximum=100),
    "--hostlist-auto-fail-time": _spec("int", minimum=1, maximum=3600),
    "--ipset": _spec("path", multi=True),
    "--ipset-exclude": _spec("path", multi=True),
    "--ip-id": _spec("enum", choices=("zero", "seq", "rnd")),
    "--dpi-desync": _spec("enum_csv", max_items=3,
                         choices=("none", "split", "disorder", "fake", "fakedsplit",
                                  "hostfakesplit", "multisplit", "syndata")),
    "--dpi-desync-repeats": _spec("int", minimum=1, maximum=100),
    "--dpi-desync-ttl": _spec("int", minimum=0, maximum=255),
    "--dpi-desync-ttl6": _spec("int", minimum=0, maximum=255),
    "--dpi-desync-autottl": _spec("tokens", pattern=r"^[0-9,\-:]+$"),
    "--dpi-desync-autottl6": _spec("tokens", pattern=r"^[0-9,\-:]+$"),
    "--dpi-desync-fooling": _spec("enum_csv", max_items=3,
                                  choices=("ts", "md5sig", "badsum", "hopbyhop", "hopbyhop2", "datanoack")),
    "--dpi-desync-split-pos": _spec("tokens", pattern=r"^[0-9a-zA-Z+_\-]+(?:,[0-9a-zA-Z+_\-]+)*$"),
    "--dpi-desync-split-seqovl": _spec("int", minimum=0, maximum=1500),
    "--dpi-desync-split-seqovl-pattern": _spec("path"),
    "--dpi-desync-fakedsplit-pattern": _spec("tokens", pattern=r"^0[xX][0-9a-fA-F]{1,32}$"),
    "--dpi-desync-hostfakesplit-mod": _spec("tokens", pattern=r"^[0-9a-zA-Z=,._\-]+$"),
    "--dpi-desync-cutoff": _spec("tokens", pattern=r"^(?:n|d)?[0-9]+$"),
    "--dpi-desync-any-protocol": _spec("enum", choices=("0", "1")),
    "--dpi-desync-fake-tls": _spec("path", multi=True),
    "--dpi-desync-fake-tls-mod": _spec("tokens", pattern=r"^[0-9a-zA-Z=,._\-]+$"),
    "--dpi-desync-fake-http": _spec("path", multi=True),
    "--dpi-desync-fake-quic": _spec("path", multi=True),
    "--dpi-desync-fake-unknown": _spec("path", multi=True),
    "--dpi-desync-fake-unknown-udp": _spec("path", multi=True),
    "--dpi-desync-fake-discord": _spec("path", multi=True),
    "--dpi-desync-fake-stun": _spec("path", multi=True),
    "--dpi-desync-fake-dht": _spec("path", multi=True),
    "--dpi-desync-fake-syndata": _spec("path", multi=True),
}

EDITABLE_ORDER = tuple(KNOWN_FLAGS.keys())


@dataclass
class Option:
    flag: str
    value: str | None = None
    known: bool = False

    def render(self):
        if self.value is None:
            return self.flag
        value = self.value
        if re.search(r"\s", value):
            value = f'"{value}"'
        return f"{self.flag}={value}"

    def copy(self):
        return Option(self.flag, self.value, self.known)


@dataclass
class Segment:
    options: list = field(default_factory=list)
    stray: list = field(default_factory=list)

    def copy(self):
        return Segment([o.copy() for o in self.options], list(self.stray))

    def summary(self):
        parts = []
        for opt in self.options:
            if opt.flag.lower() in ("--filter-tcp", "--filter-udp", "--filter-l3", "--filter-l7"):
                name = opt.flag.lower().replace("--filter-", "")
                parts.append(f"{name}={opt.value or ''}")
        return " ".join(parts) or "profile"


def _strip_quotes(value):
    if value and len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def split_args(args_str):
    """Разбивает строку аргументов на токены (кавычки как в CommandLineToArgvW)."""
    tokens, buf, quote = [], [], None
    for ch in args_str or "":
        if quote:
            if ch == quote:
                quote = None
            else:
                buf.append(ch)
        elif ch in ("'", '"'):
            quote = ch
        elif ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


def parse_args(args_str):
    """Токены winws → список сегментов (--new разделяет профили)."""
    if not (args_str or "").strip():
        return []
    segments = [Segment()]
    for token in split_args(args_str):
        if token.lower() == "--new":
            segments.append(Segment())
            continue
        if token.startswith("--"):
            if "=" in token:
                flag, value = token.split("=", 1)
                value = _strip_quotes(value)
            else:
                flag, value = token, None
            segments[-1].options.append(Option(flag, value, flag.lower() in KNOWN_FLAGS))
        elif segments[-1].options and segments[-1].options[-1].value is None:
            segments[-1].options[-1].value = _strip_quotes(token)
        else:
            segments[-1].stray.append(token)
    return segments


def serialize_args(segments):
    """Сегменты → строка аргументов для winws.exe (--new между профилями)."""
    chunks = []
    for index, seg in enumerate(segments or []):
        chunks.extend(opt.render() for opt in seg.options)
        chunks.extend(str(token) for token in seg.stray)
        if index < len(segments) - 1:
            chunks.append("--new")
    return " ".join(chunks)


def _check_placeholders(value):
    stripped = _PLACEHOLDER_RE.sub("", value)
    return "%" not in stripped


def _check_ports(value):
    if not _PORTS_RE.match(value):
        return "bad_ports"
    for part in value.split(","):
        if "-" in part:
            low, high = part.split("-", 1)
            low_i, high_i = int(low), int(high)
            if not (1 <= low_i <= 65535 and 1 <= high_i <= 65535 and low_i <= high_i):
                return "bad_ports"
        elif not 1 <= int(part) <= 65535:
            return "bad_ports"
    return None


def _check_int(value, spec):
    if not re.match(r"^[0-9]+$", value):
        return "not_number"
    number = int(value)
    if spec.get("minimum") is not None and number < spec["minimum"]:
        return "out_of_range"
    if spec.get("maximum") is not None and number > spec["maximum"]:
        return "out_of_range"
    return None


def _check_int_csv(value, spec):
    parts = value.split(",")
    if len(parts) > spec.get("max_items", 3):
        return "too_many_values"
    for part in parts:
        error = _check_int(part, spec)
        if error:
            return error
    return None


def _check_enum(value, spec):
    choices = {str(c).lower() for c in spec.get("choices", ())}
    if value.lower() not in choices:
        return "bad_choice"
    return None


def _check_enum_csv(value, spec):
    parts = value.split(",")
    if len(parts) > spec.get("max_items", 5):
        return "too_many_values"
    for part in parts:
        if _check_enum(part, spec):
            return "bad_choice"
    return None


def validate_value(flag, value, spec=None):
    """Проверка значения флага; возвращает ключ ошибки или None."""
    spec = spec if spec is not None else KNOWN_FLAGS.get(flag.lower())
    if spec is None:
        return None
    if value is None or value == "":
        return "value_required"
    if len(value) > MAX_VALUE_LEN:
        return "too_long"
    if _FORBIDDEN_RE.search(value):
        return "forbidden_chars"
    if not _check_placeholders(value):
        return "bad_placeholder"
    kind = spec.get("kind", "str")
    if kind == "int":
        return _check_int(value, spec)
    if kind == "int_csv":
        return _check_int_csv(value, spec)
    if kind == "ports":
        return _check_ports(value)
    if kind == "enum":
        return _check_enum(value, spec)
    if kind == "enum_csv":
        return _check_enum_csv(value, spec)
    if kind == "domains":
        return None if _DOMAINS_RE.match(value) else "bad_domains"
    if kind == "tokens":
        return None if re.match(spec.get("pattern", r".*"), value) else "bad_format"
    return None


def validate_args(args_str):
    """Проверка всех опций; возвращает список {segment, flag, value, error}."""
    errors = []
    for seg_index, segment in enumerate(parse_args(args_str)):
        for token in segment.stray:
            errors.append({"segment": seg_index, "flag": token, "value": None, "error": "stray_token"})
        for opt in segment.options:
            flag = opt.flag.lower()
            if not _FLAG_NAME_RE.match(flag):
                errors.append({"segment": seg_index, "flag": opt.flag, "value": opt.value, "error": "bad_flag"})
                continue
            if not opt.known:
                if opt.value and (_FORBIDDEN_RE.search(opt.value) or not _check_placeholders(opt.value)):
                    errors.append({"segment": seg_index, "flag": opt.flag, "value": opt.value,
                                   "error": "forbidden_chars"})
                continue
            error = validate_value(opt.flag, opt.value)
            if error:
                errors.append({"segment": seg_index, "flag": opt.flag, "value": opt.value, "error": error})
    return errors


def validate_name(name):
    """Проверка имени пользовательской стратегии; возвращает ключ ошибки или None."""
    name = (name or "").strip()
    if not name:
        return "empty"
    if len(name) > MAX_NAME_LEN:
        return "too_long"
    if not _NAME_RE.match(name):
        return "bad_chars"
    if name.lower().startswith(CUSTOM_PREFIX):
        return "reserved_prefix"
    if name.lower().strip(". ") == "":
        return "bad_chars"
    return None


def normalize_name(name):
    """Имя → безопасный slug без префикса custom_."""
    name = (name or "").strip()
    if name.lower().startswith(CUSTOM_PREFIX):
        name = name[len(CUSTOM_PREFIX):].strip()
    name = re.sub(r"\s+", " ", name)
    return name[:MAX_NAME_LEN]


def to_bat_paths(args_str, zapret_dir):
    """Абсолютные пути пакета → плейсхолдеры %BIN%/%LISTS%/%~dp0 (для переносимости)."""
    if not args_str:
        return ""
    base = (zapret_dir or "").rstrip("\\/")
    if not base:
        return args_str
    replacements = [
        (base + "\\bin\\", "%BIN%"),
        (base + "\\lists\\", "%LISTS%"),
        (base + "\\", "%~dp0"),
    ]
    result = args_str
    for src, dst in replacements:
        result = re.sub(re.escape(src), lambda _m, d=dst: d, result, flags=re.IGNORECASE)
    return result


def resolve_bat_paths(args_str, zapret_dir, game_filter="12"):
    """Плейсхолдеры .bat → конкретные пути/значения пакета."""
    if not args_str:
        return ""
    base = (zapret_dir or "").rstrip("\\/")
    result = args_str
    for token, value in (("%BIN%", base + "\\bin\\"), ("%LISTS%", base + "\\lists\\")):
        result = re.sub(re.escape(token), lambda _m, v=value: v, result, flags=re.IGNORECASE)
    result = re.sub(r"%~dp0", lambda _m: base + "\\", result, flags=re.IGNORECASE)
    for token in ("%GameFilterTCP%", "%GameFilterUDP%", "%GameFilter%"):
        result = re.sub(re.escape(token), lambda _m, v=str(game_filter): v, result, flags=re.IGNORECASE)
    return result


BAT_HEADER = (
    "@echo off\n"
    "chcp 65001 > nul\n"
    "\n"
    'cd /d "%~dp0"\n'
    "call service.bat status_zapret\n"
    "call service.bat load_game_filter\n"
    "call service.bat load_user_lists\n"
    "echo:\n"
    "\n"
    'set "BIN=%~dp0bin\\"\n'
    'set "LISTS=%~dp0lists\\"\n'
    "cd /d %BIN%\n"
    "\n"
)


def build_bat_content(args_str, zapret_dir):
    """Собрать текст .bat с плейсхолдерами (стиль пакета Flowseal)."""
    args = to_bat_paths(args_str, zapret_dir)
    return BAT_HEADER + 'start "zapret: %~n0" /min "%BIN%winws.exe" ' + args + "\n"


def extract_winws_args(content):
    """Вытащить аргументы winws.exe из текста .bat (склейка ^, первый запуск)."""
    content = (content or "").replace("\r\n", "\n")
    content = re.sub(r"\^\s*\n", " ", content)
    for line in content.split("\n"):
        if "winws.exe" in line.lower() and not line.strip().lower().startswith(("rem", "::")):
            match = re.search(r"winws\.exe[\"']?\s+(.*)", line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return ""


def load_strategy_args(bat_path, zapret_dir, game_filter="12"):
    """Прочитать .bat стратегии и вернуть аргументы с подставленными путями."""
    try:
        try:
            with open(bat_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(bat_path, encoding="cp1251", errors="replace") as f:
                content = f.read()
        return resolve_bat_paths(extract_winws_args(content), zapret_dir, game_filter)
    except Exception:
        return ""


def strategy_meta(zapret_dir, bat_name):
    """Метаданные <bat>.json (title/description/tags) или {}."""
    path = os.path.join(zapret_dir, os.path.basename(bat_name) + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_custom_strategy(zapret_dir, bat_name):
    base = os.path.basename(bat_name)
    if base.lower().startswith(CUSTOM_PREFIX):
        return True
    tags = strategy_meta(zapret_dir, base).get("tags") or []
    return CUSTOM_TAG in [str(tag).lower() for tag in tags if isinstance(tag, str)]


def list_custom_strategies(zapret_dir):
    items = []
    try:
        names = sorted(f for f in os.listdir(zapret_dir) if f.lower().endswith(".bat"))
    except Exception:
        return items
    for name in names:
        if not is_custom_strategy(zapret_dir, name):
            continue
        meta = strategy_meta(zapret_dir, name)
        items.append({"bat": name, "title": str(meta.get("title") or name),
                      "description": str(meta.get("description") or "")})
    return items


def save_custom_strategy(zapret_dir, name, args_str, title=None, description=None, overwrite=False):
    """Сохранить пользовательскую стратегию: .bat + .bat.json."""
    name = normalize_name(name)
    error = validate_name(name)
    if error:
        return {"ok": False, "error": error}
    errors = validate_args(args_str)
    if errors:
        return {"ok": False, "error": "invalid_args", "details": errors}
    bat_name = CUSTOM_PREFIX + name + ".bat"
    bat_path = os.path.join(zapret_dir, bat_name)
    if os.path.exists(bat_path) and not overwrite:
        return {"ok": False, "error": "exists", "bat": bat_name}
    try:
        with open(bat_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(build_bat_content(args_str, zapret_dir))
        meta = {"title": str(title or name), "tags": [CUSTOM_TAG],
                "description": str(description or "")}
        with open(bat_path + ".json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return {"ok": True, "bat": bat_name, "path": bat_path}
    except Exception as exc:
        return {"ok": False, "error": "io_error", "details": str(exc)}


def delete_custom_strategy(zapret_dir, bat_name):
    base = os.path.basename(bat_name)
    if not is_custom_strategy(zapret_dir, base):
        return {"ok": False, "error": "not_custom"}
    removed = []
    for path in (os.path.join(zapret_dir, base), os.path.join(zapret_dir, base + ".json")):
        try:
            if os.path.exists(path):
                os.remove(path)
                removed.append(os.path.basename(path))
        except Exception:
            return {"ok": False, "error": "io_error"}
    return {"ok": True, "removed": removed}


def export_custom_strategy(zapret_dir, bat_name, zip_path):
    """Экспорт .bat + метаданных в zip для обмена."""
    base = os.path.basename(bat_name)
    bat_path = os.path.join(zapret_dir, base)
    if not os.path.exists(bat_path):
        return {"ok": False, "error": "not_found"}
    if not is_custom_strategy(zapret_dir, base):
        return {"ok": False, "error": "not_custom"}
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(bat_path, base)
            json_path = bat_path + ".json"
            if os.path.exists(json_path):
                zf.write(json_path, base + ".json")
        return {"ok": True, "path": zip_path}
    except Exception as exc:
        return {"ok": False, "error": "io_error", "details": str(exc)}


def _unique_name(zapret_dir, name):
    if not os.path.exists(os.path.join(zapret_dir, CUSTOM_PREFIX + name + ".bat")):
        return name
    for i in range(2, 20):
        candidate = f"{name} {i}"
        if not os.path.exists(os.path.join(zapret_dir, CUSTOM_PREFIX + candidate + ".bat")):
            return candidate
    return None


def import_custom_strategy(zapret_dir, zip_path, overwrite=False):
    """Импорт бандла: .bat пересобирается из аргументов (чужой текст не исполняется)."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]
            if not names or len(names) > 4:
                return {"ok": False, "error": "bad_bundle"}
            for name in names:
                if os.path.basename(name) != name or ".." in name:
                    return {"ok": False, "error": "bad_bundle"}
                if not (name.lower().endswith(".bat") or name.lower().endswith(".json")):
                    return {"ok": False, "error": "bad_bundle"}
            bat_names = [n for n in names if n.lower().endswith(".bat") and not n.lower().endswith(".bat.json")]
            if len(bat_names) != 1:
                return {"ok": False, "error": "bad_bundle"}
            for name in names:
                if zf.getinfo(name).file_size > MAX_BUNDLE_BYTES:
                    return {"ok": False, "error": "too_big"}
            content = zf.read(bat_names[0]).decode("utf-8", errors="replace")
            meta = {}
            json_names = [n for n in names if n.lower().endswith(".bat.json")]
            if json_names:
                try:
                    loaded = json.loads(zf.read(json_names[0]).decode("utf-8", errors="replace"))
                    if isinstance(loaded, dict):
                        meta = loaded
                except Exception:
                    meta = {}
    except Exception:
        return {"ok": False, "error": "bad_zip"}

    args = resolve_bat_paths(extract_winws_args(content), zapret_dir)
    if not args:
        return {"ok": False, "error": "no_args"}
    stem = os.path.splitext(os.path.basename(bat_names[0]))[0]
    stem = normalize_name(stem)
    if validate_name(stem):
        stem = re.sub(r"[^\w \-().]", "_", stem).strip() or "imported"
        stem = stem[:MAX_NAME_LEN]
    title = meta.get("title") if isinstance(meta.get("title"), str) else stem
    description = meta.get("description") if isinstance(meta.get("description"), str) else ""
    if not overwrite:
        unique = _unique_name(zapret_dir, stem)
        if unique is None:
            return {"ok": False, "error": "exists"}
        stem = unique
    result = save_custom_strategy(zapret_dir, stem, args, title=title,
                                  description=description, overwrite=overwrite)
    return result
