<div align="center">

# 🚀 ZapretLauncher v17.5

### **Удобный и производительный лаунчер для автоматической настройки и управления обходом блокировок Zapret (YouTube, Discord) и ускорения Telegram в Windows**

[![Версия](https://img.shields.io/github/v/release/Aikiovade/ZapretLauncher?style=for-the-badge&color=7289da&label=Версия)](https://github.com/Aikiovade/ZapretLauncher/releases/latest)
[![Windows](https://img.shields.io/badge/ОС-Windows%2010%2F11-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Aikiovade/ZapretLauncher)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Загрузки](https://img.shields.io/github/downloads/Aikiovade/ZapretLauncher/total?style=for-the-badge&color=brightgreen)](https://github.com/Aikiovade/ZapretLauncher/releases)
[![Лицензия](https://img.shields.io/github/license/Aikiovade/ZapretLauncher?style=for-the-badge)](./LICENSE)

</div>

---

## 🌟 Возможности ZapretLauncher

- ⚡ **Быстрый запуск и смена стратегий:** Включение службы в один клик и мгновенное переключение стратегий обхода без перезапуска.
- ✈️ **Интеграция TgWsProxy:** Встроенный прокси-сервер для убирания задержек и ускорения работы Telegram Desktop.
- 🧩 **Панель задач (Windows):** статус-оверлей на иконке, кнопки «Вкл/Выкл», «Тесты» и «Стратегии» на эскизе, прогресс тестов и загрузки прямо на иконке.
- 🛡️ **Самовосстановление («Иммунитет»):** если обход падает — лаунчер сам перезапускает службу, пересоздаёт её, перепаковывает пакет и ведёт журнал инцидентов.
- 🔧 **Конструктор стратегий:** визуальная правка параметров winws, проверка на реальных пробах, сохранение и обмен своими стратегиями.
- 🔔 **OSD-уведомления:** короткое всплывающее уведомление при включении/выключении обхода.
- 🌐 **Детектор обхода (Bypass Check):** Наглядный статус подключения (`✓ WORK` / `✗ FAIL`) для проверки работы соединения.
- 💻 **Мини-оверлей (Compact Mode):** Компактное окно `220x50` поверх всех окон для быстрой работы.
- 📊 **Мониторинг ресурсов (HUD):** Отображение загрузки процессора, оперативной памяти, пинга, времени работы и статистики запусков.
- 🔄 **Автоматическое обновление:** Быстрая онлайн-проверка версий и установка обновлений с индикатором прогресса загрузки (`%`).
- 🎨 **Темы и Мультиязычность:** Различные варианты оформления интерфейса и поддержка двух языков (RU / EN).
- 🎮 **Discord Rich Presence (опционально):** статус в Discord — стратегия, состояние, аптайм и кнопка установки.
- ✨ **Живой интерфейс:** анимация запуска (кольца + логотип, пропуск кликом), частицы фона, пульсация главного круга.
- 📁 **Экспорт / Импорт:** Сохранение и загрузка настроек лаунчера в один клик.

---

## 🚀 Быстрый старт

1. Перейдите в раздел **[Релизы](https://github.com/Aikiovade/ZapretLauncher/releases/latest)**.
2. Скачайте файл **`Zapret.exe`**.
3. Запустите файл от имени Администратора.
4. Включите обход нажатием на центральную кнопку и выберите рабочую стратегию.

---

## ⌨️ Горячие клавиши

- `Ctrl + Shift + Z` — Включение / Выключение обхода.
- `Ctrl + Shift + C` — Мини-оверлей (Compact Mode) поверх всех окон.
- `Клик на v17.5` — История изменений («Что нового»).
- `Колёсико мыши` — Прокрутка списка доступных стратегий.

---

## 🛠️ Сборка из исходного кода

```bash
git clone https://github.com/Aikiovade/ZapretLauncher.git
cd ZapretLauncher
pip install -r requirements.txt
pip install pyinstaller
python tools/rebuild_zip.py                          # если менялись данные пакета
python -m PyInstaller --noconfirm Zapret.spec        # legacy Tk    -> dist/Zapret.exe
python -m PyInstaller --noconfirm ZapretWeb.spec     # WebView2     -> dist/ZapretWeb.exe
```

Хэш для `update_info.json`: `python tools/get_hash.py`. Проверка: `python tools/smoke.py` (60 тестов) и `python -m pytest -q` (12 тестов). Линт: `python -m ruff check .` (конфиг `ruff.toml`). Аудит зависимостей: `pip install pip-audit && pip-audit -r requirements.txt`. SBOM: `pip install cyclonedx-bom && cyclonedx-py requirements requirements.txt -o sbom.json`.

Changelog ведётся в `CHANGELOG.md`; после правки выполните `python tools/sync_changelog.py` (обновит блок в коде и `update_info.json`; `--check` — только проверка).

**Установщик** (нужен Inno Setup 6): `iscc /DExeName=Zapret.exe installer\zapret_launcher.iss` → `dist\ZapretLauncher-<версия>-setup.exe`. При удалении автоматически чистит службы, автозапуск и каталог данных.

Установщик — полностью кастомный: статичный баннер (кольца + логотип), список возможностей, свой прогресс-бар, брендированный финальный экран с авто-закрытием через 5 секунд. Ставится классическая (Tk) версия. Ярлык на рабочем столе, меню Пуск и служба обхода создаются автоматически; файлы обновляются поверх старой установки. Файлы при повторной установке заменяются (upgrade), старый exe удаляется при смене компонента.

Обновление: установленная версия обновляется через `Setup.exe /SILENT /NORESTART /CLOSEAPPLICATIONS` с проверкой SSL + sha256 + Ed25519-подписи манифеста; portable-сборка при обновлении мигрирует на установленную версию. Данные установленной версии лежат в `%ProgramData%\ZapretLauncher` (Administrators: Full, Users: Read) с автоматической миграцией из `C:\ZapretLauncher` и `%LOCALAPPDATA%`.

**Discord RPC**: Application ID вшит в сборку (автор задаёт его один раз через `python tools/set_discord_id.py <ID>`) — пользователю вводить ничего не нужно. Включите тумблер «Discord статус» (нужен запущенный десктопный Discord; браузерная версия не подходит), под ним видно состояние: «ожидание Discord» / «подключено».

**Portable-сборка**: `python tools/make_portable.py Zapret.exe` → `dist\Zapret-<версия>-portable.zip`. Альтернатива — положить `portable.txt` рядом с exe: данные будут храниться в `ZapretLauncher_data` рядом с программой.

**Lite-сборка** (без встроенного пакета стратегий, ~25 МБ): `python -m PyInstaller --noconfirm ZapretLite.spec` → `dist\ZapretLite.exe`; пакет Flowseal докачивается при первом запуске.

**Dev-режим** (без прав администратора и реальной службы): `python webapp.py --dev` — используется MockBackend.

**Теги стратегий**: рядом с `.bat` можно положить `<имя>.bat.json` с `{"title": "...", "tags": ["..."], "description": "..."}` — подхватывается на лету, поиск в списке стратегий учитывает теги.

**Подпись манифеста обновлений** (Ed25519): `python tools/sign_manifest.py --gen-keys keys.json`, затем публичный ключ из `keys.json` впишите в `zapret_new_win.py` → `UPDATE_PUBKEY_HEX`, а сам манифест подпишите: `python tools/sign_manifest.py update_info.json --key keys.json`. Файл `keys.json` не коммитить.

---

## 🖥️ CLI (zapret-cli)

```bash
python zapret_cli.py status          # состояние службы/пакета (JSON)
python zapret_cli.py list            # список стратегий
python zapret_cli.py probe           # пробы YouTube/Discord/Telegram/Google
python zapret_cli.py interfaces      # активные сетевые интерфейсы
python zapret_cli.py start --bat "general (ALT).bat"   # (нужен админ)
python zapret_cli.py stop                              # (нужен админ)
python zapret_cli.py test                              # (нужен админ)
```

CI (GitHub Actions, `.github/workflows/ci.yml`): ruff + smoke на каждый push/PR, отчёты pip-audit/SBOM артефактами; на теги `v*` собирает обе версии, пересчитывает хэш в `update_info.json`, коммитит манифест в `main` и создаёт релиз.

---

## 🗑️ Удаление

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\uninstall.ps1
```

Останавливает и удаляет службы `zapret`/`WinDivert`, завершает `winws`/`TgWsProxy`, убирает автозапуск (ярлык Startup и запись `TgWsProxy` в HKCU Run) и каталоги данных. Флаги: `-KeepData` (сохранить конфиг и логи), `-PurgeTgProxy` (удалить также конфиг TgWsProxy), `-DryRun` (показать действия без выполнения). Сам файл `Zapret.exe` удаляется вручную.

---

## ❤️ Благодарности и Авторство

- **[bol-van/zapret](https://github.com/bol-van/zapret)** — создатель оригинальной утилиты `zapret` и компонента `winws`.
- **[Flowseal/zapret-discord-youtube](https://github.com/Flowseal/zapret-discord-youtube)** — автор набора стратегий для Windows и проекта `tg-ws-proxy`.
- **[Aikiovade/ZapretLauncher](https://github.com/Aikiovade/ZapretLauncher)** — автор GUI-лаунчера.
