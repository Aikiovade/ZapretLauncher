# HANDOFF — ZapretLauncher (сессии 2026-09-27/28, продолжение 09-28)

Документ для продолжения работы в новой сессии. Ничего не упущено: состояние, все изменения, артефакты, хэши, решения, полный остаток скоупа.

**Сессия 4 (17.5, работа БЕЗ релиза — по решению пользователя; версия в коде/манифестах всё ещё 17.4)**: сделаны три фичи «17.5» (ядро + Tk; web — отдельной волной позже):
- **🧩 Windows-интеграция 2.0**: `win_taskbar.py` — ITaskbarList3 через ctypes (оверлей-точка статуса ON/OFF/BUSY/TESTING/ERROR, кнопки на эскизе панели задач «Вкл/Выкл»/«Тесты»/«Стратегии» через SetWindowSubclass + WM_COMMAND/THBN_CLICKED, прогресс тестов и загрузки обновления на иконке, FlashWindowEx при сбое). Живая проверка на окне Tk пройдена (COM, оверлей, кнопки, subclass, прогресс, flash — все True). Настройка `taskbar_ui` (по умолчанию вкл).
- **🛡 Иммунитет**: ядро — `pick_rotation_target`, `next_recovery_step` (лестница service_down: restart→recreate→repack→notify; degraded: rotate→…; кулдауны+лимит), `log_incident`/`read_incidents` (`incidents.jsonl`), `repack_payload()`. Tk-watchdog использует лестницу (настройка `self_heal`, вкл), авто-ротация при деградации (`auto_rotate`, выкл) через `_degrade_check`; окно «Журнал инцидентов»; webapp `_auto_rotate_now` переведён на общий `pick_rotation_target`.
- **🔧 Конструктор стратегий**: `strategy_builder.py` (чистые функции: parse/serialize аргументов winws с сегментами `--new`, вайтлист ~40 флагов, валидация, сборка .bat с `%BIN%`/`%LISTS%`, save/list/delete/export/import с санитайзом чужого .bat, stray-токены отклоняются). Ядро: `run_custom_strategy_probe` (стоп службы → прямой winws → пробы → восстановление). Tk-окно «Конструктор» (выбор базы, правка значений, добавить/удалить флаг, Проверить/Сохранить/Экспорт/Импорт). Интеграция проверена: generated .bat корректно парсится `parse_strategy_bat` и появляется в `list_strategies` (hot-reload).
- **UI**: кнопка «Ещё…» в настройках (Y=708..736) → окно с тумблерами taskbar/OSD/self_heal/auto_rotate + кнопки окон журнала и конструктора; OSD-уведомление при вкл/выкл; новые ключи i18n RU/EN (parity проверена smoke).
- **Проверки**: smoke **103/103**, pytest **48/48** (новые файлы `tests/test_strategy_builder.py` — 15, `tests/test_win_taskbar.py` — 4, +4 recovery в `test_core.py`), ruff чисто. ВАЖНО: версия/CHANGELOG/манифесты/.iss/сборки НЕ трогались — перед релизом 17.5 нужно: CHANGELOG.md → `sync_changelog.py`, бамп `CURRENT_VERSION`/манифестов/`.iss`, пересборка exe, живой прогон приложения пользователем (taskbar/OSD/лечение/конструктор на реальной службе).
- **Совет четырёх голосов (Skeptic/Pragmatist/Critic) и решение**: вердикт — заморозка скоупа (пользователь выбрал позицию Прагматика). Отклонены: расписание, bandwidth-тест, редактор тем, аналитика, уменьшение exe (риск CI), QR и «сеть безопасности» стратегий (авто-откат last-known-good — идея Критика, отложена в 17.6 вместе с QR; для QR телефону нужен host=0.0.0.0 + файрвол — сеть, совет был против). Закалка вместо новых фич.
- **Закалка Immunity (по вердикту)**: (1) конфликт «тест конструктора × watchdog» — на время `run_custom_strategy_probe` статус через `_set_probe_status` = TESTING + флаг `_builder_probe_active` (watchdog/авто-ротация не вмешиваются), после — восстановление прежнего статуса; (2) `_ensure_active_bat()` — перед каждым шагом лечения и после repack активная стратегия проверяется в актуальном пакете (иначе тупик: install с несуществующим .bat); (3) тесты: `read_incidents` устойчив к битым строкам, граница окна лимита в `next_recovery_step`. Итог: smoke **103/103**, pytest **50/50**, ruff чисто.
- **Установщик — вёрстка (по скриншоту пользователя)**: исправлено: (1) **контент кастомных страниц теперь на всю ширину** (`ComputeLayout`: CreateCustomPage большую картинку не показывает — раньше под неё резервировалось место и текст прижимался вправо и обрезался); финальная страница резервирует большую картинку (FinishLeft/FinishWidth); (2) `AddLabel` → `AutoSize := True` (высота при AutoSize=False оставалась дефолтной — заголовки 15–16pt обрезались сверху); (3) `AddBanner` — баннер по центру с сохранением пропорций (раньше `Stretch` искажал); (4) кадры баннера/финиш перегенерированы под широкий формат **900×150** (`make_installer_art.py`: BANNER_W 640→900) — при полной ширине высота ~94px; (5) InfoLine/FinishText укорочены под доступную ширину (больше нет обрезки); (6) `RunList.Height` ограничен `FinishedPage.Height`; (7) фокус на кнопке (user32 `SetFocus` через Handle) — убрана пунктирная рамка на чекбоксах. Проверено скриншотами страниц; **`tools/installer_visual_test.py`** — новый инструмент (песочная сборка без службы/ярлыков, `/LANG=russian`, безвредный [Run] для RunList, скриншоты в `%TEMP%\zapret_visual\`). Песочный silent-тест PASS; реальный `dist\ZapretLauncher-17.4-setup.exe` пересобран (39.7 МБ). ВАЖНО: хэш Setup в манифестах — от старой сборки; пересчёт — в релизной волне.
- **🔧 Хотфикс установщика v17.5 (перевыложен, 06.10)**: баг «DeleteFile: сбой, код 32» при обновлении поверх **запущенного** приложения (файл `C:\Program Files\ZapretLauncher\Zapret.exe` занят процессом). Причина: Inno `CloseApplications`/RM не закрывает запущенный exe (в т.ч. в silent-режиме апдейтера). Фикс в `installer/zapret_launcher.iss`: `CurStepChanged(ssInstall)` → `taskkill /F /IM Zapret.exe /T` (+ZapretWeb.exe) и пауза перед заменой файлов. **Проверено end-to-end**: песочная установка + процесс-блокировщик с именем `Zapret.exe` (delete падает с winerror 32) → установка с фиксом: rc=0, блокировщик убит, файл заменён. Перевыложено в Release v17.5 (Setup `AF21068E…9E751` + update_info.json, `--clobber`), скачанный ассет сверен по sha256 = манифест; манифесты stable/beta в main обновлены (`503556b`), notes релиза дополнены. **Автозапуск проверен**: ярлык `%APPDATA%\...\Startup\Zapret.lnk` → `C:\Program Files\ZapretLauncher\Zapret.exe`, конфиг `autorun: true` — работает; нюанс: при входе в систему Windows показывает UAC (exe требует админа), полностью тихий автозапуск = задача Планировщика (17.6).
- **🎉 РЕЛИЗ v17.5 ВЫПУЩЕН (06.10.2026)**: main `19caa08` (коммит всей волны) → CI smoke на main зелёный → тег `v17.5` запушен → CI собрал Zapret.exe/ZapretWeb.exe/Setup, обновил манифест CI-хэшем, закоммитил его в main (`a8d5837`) и создал **GitHub Release v17.5** (4 ассета: Zapret.exe, ZapretWeb.exe, ZapretLauncher-17.5-setup.exe, update_info.json). Скачанный из релиза Setup сверен по sha256 = `15E0FA32…F087` — совпадает с манифестом. **Подписи нет** (секрет `MANIFEST_SIGNING_KEY` не задан; Ed25519-seed утерян — жил только в удалённом `%TEMP%\opencode\test_keys.json`, в истории сессий найден лишь публичный ключ `1605087e…3dd8`). **Фикс CI**: golden-тест был непереносим (абсолютные пути `C:\Users\PC1…` против `D:\a\…` на CI) — `gen_golden.py`/`test_core.py` теперь нормализуют пути в `<PKG>` (именно это уронило CI на 17.4). GH-токен из чата использован для push/тега/проверок — пользователь отзовёт после. Локальный main синхронизирован с origin.
- **Волна 17.5 (версии/сборки, выполнена)**: `CURRENT_VERSION`/`pyproject`/`.iss AppVersion`/README/оба манифеста → **17.5**; CHANGELOG.md получил раздел v17.5 (14 пунктов) → `sync_changelog.py` (код + stable-манифест; beta-changelog синхронизирован копией). Бейдж в `wizard_image.bmp` теперь берётся из `update_info.json` (`app_version()` в `make_installer_art.py`) — арт перегенерирован (v17.5). **Пересобраны все exe**: `Zapret.exe` 39.9 МБ (новый код + звук alert-03 + 17.5), `ZapretWeb.exe` 49 МБ, `ZapretLite.exe` 26.5 МБ; установщик — **`dist\ZapretLauncher-17.5-setup.exe`** 39.3 МБ (старый 17.4 удалён). Манифесты обновлены `tools/ci_update_manifest.py --tag v17.5` (URLs v17.5, hash = Setup = `41BC1F05…`, подписи нет — локально `MANIFEST_SIGNING_KEY` не задан; CI подпишет при наличии секрета и пересчитает хэш своей сборки). Проверено: smoke 103/103, pytest 52/52, ruff чисто, визуальный тест — заголовок «Установка — ZapretLauncher 17.5», бейдж v17.5, авто-закрытие «ЗАКРЫТЬ (4…)». **Осталось пользователю**: закоммитить и поставить тег `v17.5` (CI соберёт релиз/перепишет хэш) либо вручную залить Setup в Release.
- **Установщик — итерация 2 (по фидбеку: «убери анимации и звук с первых двух, текст расположи лучше, финал — сам закрывается через 5 с»)**: (1) анимация баннера удалена — вместо 16 кадров статичный `banner.bmp` (900×150, `make_banner` в `tools/make_installer_art.py`; `make_anim_frames` и `installer/frames/` удалены); (2) **все звуки установщика удалены** (intro/done, чекбокс «Звуковое сопровождение» и mciSendString) — `sound_intro.wav`/`sound_done.wav` удалены, `PlaySoundFile`/`SoundCheckClick` вырезаны; (3) раскладка текста на вступлении переработана (увеличены отступы, чекбокс убран — блок дышит); (4) финал: **авто-закрытие через 5 секунд** — `CloseTick` по `SetTimer`, на кнопке отсчёт «ЗАКРЫТЬ (5..1)», по нулю `SendMessage(..., BM_CLICK)` = нажатие кнопки; проверено вживую: закрывается сам за 5.4 с без нажатий. Smoke-проверки установщика обновлены (banner.bmp, CLOSE_SECONDS/CloseTick/BM_CLICK, нет frames/звуков). `tools/installer_visual_test.py` — детект финала по префиксу «ЗАКРЫТЬ/CLOSE» (с отсчётом). Реальный `dist\ZapretLauncher-17.4-setup.exe` пересобран (39.3 МБ, было 39.7). Sandbox PASS, smoke 103/103, pytest 52/52, ruff чисто.
- **Звук (по запросу пользователя)**: основной звук всех действий заменён на **alert-03** из opencode (`@opencode-aidesktop/resources/app.asar` → `out/renderer/assets/alert-03-*.js`, звук вшит base64 data-URI — в этой сборке отдельного `.aac` нет). Извлечение/конвертация: `%TEMP%\opencode\extract_alert03.py` (парсер asar: `header_size` в байтах 4-7, JSON с offset 16, данные с `8+header_size`; PyAV → PCM WAV 44.1k mono). Заменены `sounds/start.wav` и `sounds/stop.wav` (0.325 c, peak 11300 — громче старых; бэкап старых в `%TEMP%\opencode\oc_sounds\*.bak`). Все `play_sound("ON"/"OFF")` играют alert-03. Пересборка exe не делалась (релиз позже; spec кладёт `sounds/` в бандл).
- **Минимальные фиксы по итогам перепроверки (применены, 52 pytest / 103 smoke / ruff — зелёные)**: (1) `repack`: порядок stop → repack → install; (2) лимит `MAX_BUNDLE_BYTES` проверяется для ВСЕХ членов zip при импорте (закрыта zip-бомба через `.bat.json`); (3) `_attempt_recovery`: check-then-act под `self._repair_lock` (TOCTOU watchdog × `_degrade_check`), откат флага при сбое старта потока; (4) `_set_probe_status(False, prev, restored)`: статус по факту восстановления службы, при сбое — `log_incident("probe_restore")` + запуск лестницы; (5) `_builder_testing`/`_degrade_running` сбрасываются и при исключениях; (6) `_builder_test` блокируется при TESTING/BUSY/recovery/`test_is_running` (ключ `sb_busy` RU/EN); `toggle_system` не стартует при BUSY/recovery/probe; (7) `_FORBIDDEN_RE` запрещает `"`/`'`; (8) фильтр стратегий — `is_strategy_bat()` (исключается ровно `service.bat`, не подстрока) — в ядре/Tk/webapp; тесты: `is_strategy_bat`, кавычки, oversized-json.
- **Тотальная перепроверка 17.5 (команда 5 агентов, read-only)**: 4× PASS WITH ISSUES, 1× FAIL (silent-failure). Подтверждено мной и агентами (не исправлено — решение о минимальных правках за пользователем): **(а)** zip-бомба в `import_custom_strategy` — лимит `MAX_BUNDLE_BYTES` только для .bat, .bat.json читается без лимита (3 агента); **(б)** фантомный статус ON: `_run_recovery_action` finally ставит ON при desired_bypass без health-проверки, и `_set_probe_status(False, previous_status)` вернёт ON даже если служба после пробы не восстановилась (2 агента; правильный фикс — не OFF, а recovering-состояние/надзор по desired_bypass); **(в)** TOCTOU `_repair_active`/`_builder_probe_active` — check-then-set без lock из watchdog и `_degrade_check` (2 агента); **(г)** `repack` в лестнице выполняется ДО stop — при живой службе (degraded) перераспаковка падает на залоченном winws.exe (порядок: stop → repack → install); **(д)** `self.scores` в Tk не существует → ветка «лучшая по тестам» в ротации мертва (getattr default {}); **(е)** `list_strategies`/`_refresh_bat_files` фильтруют подстроку «service» — кастомная стратегия с «service» в имени не появится в UI (фильтровать по stem == "service"); **(ж)** `_builder_testing`/`_degrade_running` не сбрасываются в finally при исключении; **(з)** тестовые дыры: happy-path `run_custom_strategy_probe`, `_ensure_active_bat`, `repack_payload`, Tk-recovery-ветки, `_set_probe_status`. **Поправки к агентам**: `manifest_signature_ok` ВЫЗЫВАЕТСЯ (webapp.py:574,597) — не enforced лишь из-за пустого `UPDATE_PUBKEY_HEX` (релиз-инжиниринг, не регрессия 17.5); `ensure_data_dir_acl` мёртв в рантайме (только smoke) — пре-существующее. Смоук/pytest/ruff перепроверены: 103/103, 50/50, чисто.

**Обновление сессии 2 (09-28)**: сделаны C9 (полная RU/EN web-UI), A2 (single-writer state в Api), C4-web (compact-оверлей), C5-scores (сортировка по тестам), B3-полный (общий PS-раннер в core), B11-полный (порт/секрет/ссылка/health TgProxy), фикс потери чужих ключей конфига, F1 (CI), **фикс повреждённого рабочего пакета (payload self-heal)**, H4 (ruff+mypy в CI, зелёные), E7 (pip-audit + CycloneDX SBOM в CI, report-only), F7 (tools/uninstall.ps1 с -DryRun), A3 (CLI zapret-cli), F6 (единый CHANGELOG.md + генератор), G10 («Сообщить о проблеме»), H1 (17 pytest-тестов), H6 (ротация логов + events.jsonl), E5 (sc failure), C11 (импорт .bat через диалог), **I7 (portable)**, **F2 (каналы stable/beta + откат)**, **F5 (зеркала)**, **E1 (Ed25519-подпись манифеста)**, **D3/D6 (качество/батарея)**, **G14 (idle-hide)**, **C6/C8 (тосты/трей)**, **C7-lite (светлая тема)**, **C3 (настраиваемый хоткей)**, **C1 (ping-график)**, **G4/G6 (гейминг/speedtest)**, **A9/I3 (Inno + portable-zip)**, **H8 (golden)**, **I6 (режимы UI)**. Smoke: **66/66**, pytest: **17/17**, mypy: чисто. Обе exe **пересобраны**, changelog 38 пунктов, хэш синхронизирован с обоими манифестами. Далее в этой же сессии: **A4** (метаданные/теги стратегий + hot-reload), **A5** (BypassBackend + MockBackend), **H5** (dev-режим `--dev`), **B4** (авто-ротация при деградации), **C2** (мастер первого запуска), **D7** (ZapretLite.exe 25.2 МБ без zip + догрузка), **E6** (локальные крашрепорты), **F3** (`package` в манифесте), **H3-lite** (скрипт+job интеграционного теста службы), **pre-commit** (H4), **C10** (тултипы), CI: сборка Inno-установщика на теге. Smoke: **72/72**, pytest: **20/20**. Сессия 3 (G12 + установочный апдейт): **G12 Discord Rich Presence** (discord_rpc.py, pypresence, тумблер в web/Tk, off by default, client_id нужно вписать), **A9/I3-апдейт через установщик** (installer_url/installer_sha256 в манифестах, verify SSL+sha256+Ed25519, `Setup.exe /SILENT /NORESTART /CLOSEAPPLICATIONS`, режимы installed/portable, `--install-service`), **E2 ProgramData+DACL+миграция** (%ProgramData%\ZapretLauncher, icacls Administrators/Users), CI: сборка Inno-установщика + `tools/ci_update_manifest.py` (hash/installer/подпись по секрету MANIFEST_SIGNING_KEY). Smoke: **81/81**, pytest: **24/24**.

---

## 0. Как продолжить в новой сессии

Скажи агенту: «продолжай по плану, проект MyLauncher, читай HANDOFF.md». Порядок работ — раздел 9.

**Жёсткие правила безопасности при работе:**
- НЕ запускать `zapret_new_win.py`/`Zapret.exe`/`webapp.py`/`ZapretWeb.exe` в сессии анализа: приложение требует UAC, ставит службу «zapret», убивает winws и меняет сеть на машине пользователя.
- Безопасно: `python tools/smoke.py`, `python -m py_compile`, чтение файлов, `git status`.
- Всё, что делалось — read-only анализ + правки кода; приложение ни разу не запускалось.
- Коммиты НЕ делались (пользователь не просил). Рабочее дерево содержит изменения.

---

## 1. Проект

- Путь: `C:\Users\PC1\Desktop\MyLauncher` (git-репозиторий, origin: https://github.com/Aikiovade/ZapretLauncher.git).
- Продукт: **ZapretLauncher v17.4** — Windows-лаунчер (Python 3.11) для DPI-обхода:
  - ставит `winws.exe` из пакета Flowseal `zapret-discord-youtube` как службу Windows «zapret» (от SYSTEM),
  - управляет TgWsProxy (Flowseal `tg-ws-proxy`) для Telegram,
  - самообновление с GitHub (`update_info.json` + `Zapret.exe`),
  - два UI: legacy Tk (customtkinter, `zapret_new_win.py`) и новый WebView2 (`webapp.py` + `webui/`),
  - трей (pystray), автозапуск (ярлык в Startup через PowerShell WScript.Shell), watchdog, автотесты стратегий, пробы сервисов, авто-подбор стратегии, профили сети.

- Окружение: Windows 10/11, Python 3.11.9 (`C:\Users\PC1\AppData\Local\Programs\Python\Python311`), PowerShell 5.1.
- Зависимости установлены: customtkinter 6.0.0, psutil 7.0.0, pystray 0.19.5, Pillow, keyboard, PyInstaller, pywebview 6.2.1 (+pythonnet 3.1.0, clr_loader 0.3.1, bottle 0.13.4), в системе есть numpy (в сборки исключён).
- Edge WebView2 Runtime: 154.0.4258.37 (установлен).

---

## 2. Текущие артефакты и хэши

| Артефакт | Значение |
|---|---|
| `dist/Zapret.exe` (legacy Tk) | ~37.8 МБ, SHA-256 `2891F27BD0EBD4242AB284763007A36D7D2816456975A8D77550697AB500BB76` (сборка 09-28, сессия 3h) — **этот хэш прописан в `update_info.json` и `update_info_beta.json` и сверен** |
| `dist/ZapretWeb.exe` (WebView2) | ~46.9 МБ, SHA-256 `E03798D7976C1E66DC818BF01A923F0197BA35FE5A3971FF17DA68DDC970782E` (сборка 09-28, сессия 3h; в манифесте отсутствует) |
| `dist/ZapretLite.exe` (WebView2, без встроенного zip) | ~25.3 МБ, SHA-256 `F42461D888D3BA93F486C329B444F635EB6155CED1E1A0C8CD764949468C2DCF` (D7: payload докачивается при первом старте) |
| `dist/ZapretLauncher-17.4-setup.exe` | 37.8 МБ, SHA-256 `1368370B747085298AD08580B27ED81E9E8DD1B1270EB8220053EFA52FF4EE40` — Inno Setup 6.7.3: тёмный стиль + фон мастера + звуки, компоненты web/tk; проверен innounp и песочным тестом (`tools/installer_sandbox_test.py`) |
| `zapret_data.zip` | 53 записи, корень `zapret-discord-youtube-1.10.3/`, ~21.52 МБ, `testzip()` ok |
| `winws.exe` (1.10.3) | sha256 `affb4f69d2ea302a7abccd5325d81826e140ddae014f1e070bc4a6c0dd555188` (зашит в `KNOWN_WINWS_SHA256`) |
| Пакет Flowseal 1.10.3 | zip sha256 `244314ae1c24538a0d751601da8e0c925c843371eec4456eb15f14c4fd6b7058` |
| TgWsProxy v1.10.4 | sha256 `b51436e8960307316135e64ac14753b1f3b0e7a46afe1bd6081353b82de20f09`, FileVersion 1.10.4.0 |
| `update_info.json` | version 17.4, hash = хэш Zapret.exe выше, `download_url` (exe) + `installer_url`/`installer_sha256` (установщик; sha пуст до сборки Inno в CI), `mirrors` (опц.), changelog (49 пунктов) |

Сборки актуальны (09-28): собраны обе exe из текущих исходников, бандлы проверены (webui/sounds/zip/webview.platforms.winforms на месте), хэш манифеста == хэш exe.

**Пользователь должен сам**: залить `dist/Zapret.exe` в GitHub Release `v17.4` (иначе обновление не сработает/хэш не совпадёт; при пересборке — обновить хэш через `python tools/get_hash.py`, заменить значение в `update_info.json`).

---

## 3. Структура проекта (текущая)

```
MyLauncher/
├─ zapret_new_win.py            # legacy Tk-приложение + ОБЩЕЕ ЯДРО (модульные функции, константы)
├─ webapp.py                # A7: WebView2-приложение (pywebview), Api-мост к ядру
├─ webui/index.html         # A7/C*: весь web-UI (HTML+CSS+JS в одном файле)
├─ sounds/start.wav, stop.wav  # звуки вкл/выкл (из opencode, сконвертированы PyAV)
├─ zapret_cli.py            # A3: CLI (status/list/probe/interfaces/start/stop/test)
├─ ed25519.py               # E1: Ed25519 sign/verify (RFC 8032, без зависимостей)
├─ discord_rpc.py           # G12: Discord Rich Presence (pypresence, тихий no-op)
├─ CHANGELOG.md             # F6: единый источник changelog (app + манифест)
├─ update_info_beta.json    # F2: beta-канал
├─ installer/zapret_launcher.iss  # A9/I3: Inno Setup (iscc /DExeName=Zapret.exe ...)
├─ tests/test_core.py       # H1: 17 pytest-тестов чистых функций
├─ tests/golden/<пакет>.json# H8: golden разбора стратегий
├─ tools/smoke.py           # 66 смоук-проверок (stdlib, headless)
├─ tools/rebuild_zip.py     # пересборка zapret_data.zip из папки пакета
├─ tools/get_hash.py        # sha256 exe (аргумент или dist/Zapret.exe)
├─ tools/uninstall.ps1      # деинсталлятор (UAC, -KeepData/-PurgeTgProxy/-DryRun)
├─ tools/sync_changelog.py  # F6: CHANGELOG.md -> zapret_new_win.py + update_info.json (--check)
├─ tools/sign_manifest.py   # E1: ключи/подпись/проверка манифеста (Ed25519)
├─ tools/gen_golden.py      # H8: генерация golden-набора парсера
├─ tools/make_portable.py   # I7: portable-zip (exe + portable.txt)
├─ tools/ci_update_manifest.py # CI: hash + installer_url/sha + Ed25519-подпись манифеста
├─ .github/workflows/ci.yml # CI: ruff+smoke+pip-audit+SBOM; сборка+релиз на теги v*
├─ ruff.toml                # конфиг линтера (E/F/W605/I001/UP020/UP031/SIM/D2/E722)
├─ Zapret.spec              # сборка legacy Tk exe
├─ ZapretWeb.spec           # сборка WebView2 exe (webapp.py)
├─ zapret_data/zapret-discord-youtube-1.10.3/   # данные (53 файла, без mp3)
├─ zapret_data.zip          # упакованные данные для распаковки в рантайме
├─ update_info.json         # манифест обновления 17.4
├─ requirements.txt, LICENSE (MIT, правообладатель «Aikiovade» — проверить), .gitignore
├─ README.md                # v17.4, сборка через spec, хоткеи (Ctrl+Shift+Z, Ctrl+Shift+C)
├─ icon.ico
├─ dist/ (Zapret.exe, ZapretWeb.exe), build/ (артефакты PyInstaller)
└─ HANDOFF.md (этот файл)
```

Изменения относительно исходного состояния:
- УДАЛЕНО: `test_me.py`, `dist/get_hash.py` (перенесён в tools), `yarusskiy.mp3`, `americanets.mp3`, папка `zapret_data/zapret-discord-youtube-1.10.0/`.
- `flowseal_readme.txt` был удалён из worktree ещё до этой сессии (не закоммичено).
- Новые untracked: `.gitignore`, `LICENSE`, `requirements.txt`, `tools/`, `webui/`, `sounds/`, `webapp.py`, `ZapretWeb.spec`, `zapret_data/...1.10.3/`.
- `.gitignore` добавлен, но `build/`, `dist/`, `zapret_data.zip` остаются **трекаемыми** (чтобы убрать: `git rm -r --cached build dist zapret_data.zip`; история `.git` ~205 МБ — отдельная задача).

---

## 4. Что сделано (по волнам) — ДЕТАЛЬНО

### Волна 1 (готово)
**Безопасность:**
- Апдейтер: обязательные SSL и SHA-256; allowlist хостов (`UPDATE_ALLOWED_HOSTS`: github.com, objects.githubusercontent.com, raw.githubusercontent.com) + `UPDATE_REPO_PATH=/Aikiovade/ZapretLauncher/`; лимит 200 МБ; убраны `CERT_NONE` и bat/TEMP-подмена. Замена exe в процессе: download → hash → копия в `cur_exe.new` (хэш считается по записанным байтам) → `os.replace(cur, .old)` → `os.replace(.new, cur)` → перезапуск; `.old` чистится при следующем старте.
- Все `shell=True` убраны: `sc/net/taskkill/reg/netsh/ipconfig` — списками аргументов; запуск winws напрямую — через `CommandLineToArgvW` (`split_windows_args`).
- Удалены `SeDebugPrivilege`, скрытие файлов, `make_hidden`; zip-slip защита (`_safe_extractall`); mutex с `SetLastError(0)`.
- Автозапуск: сохраняется в конфиг (`autorun`), ярлык через PowerShell `WScript.Shell` (без pywin32), указывает на текущий exe. `copy_exe_to_appdata` удалён.

**Производительность:**
- Рендер Tk: пауза при `not winfo_viewable()` (250 мс тик), 30 FPS (`RENDER_FRAME_MS=33`), сетка ограничена viewport, частицы 600→200, кэш `interpolate_color`, throttle логов рендера, лёгкий compact-рендер.
- `stats.json` — не чаще 60 с + при выходе (`_maybe_save_stats`); аптайм только при ON; TCP-пинг (`tcp_connect_ms`) вместо ICMP; bypass-чек = TCP до discord.com:443.
- старт: `run_startup_tasks` больше не вызывает `self.after` из потока — очередь `ui_call`/`_pump_ui_queue`; `start_process_logic` в отдельном потоке; единая `_ensure_payload()` с локом (гонка двойной распаковки устранена).

**Баги:** починена кнопка «Экспорт» (перекрывалась хитбоксом уведомлений), удалён недостижимый клик-блок, счётчик аптайма, миграция user-файлов при смене версии пакета, папка не удаляется, если из неё запущен exe.

**Мёртвый код:** удалены гимны (все функции + mp3), `get_ping_ms`, `MEMORYSTATUSEX`, `get_real_ram_usage`, `set_volume_max`, `get_exe_path`, `get_autorun_exe_path`, `enable_debug_privilege`, `_locate_zapret_dir`, `on_right_click`, `seen_configs`, `update_msg_timer/update_msg_text`, `switch_notifications_pos/switch_repair_pos`, импорты winreg/webbrowser/urllib.error/traceback(глобальный). i18n: удалены неиспользуемые ключи, исправлен `ONs`→`ON`.

**Инфраструктура:** `C:\ZapretLauncher` (fallback `%LOCALAPPDATA%\ZapretLauncher`), миграция `migrate_from_legacy_dir()`; конфиг schema v2 + атомарная запись; `desired_bypass` (последнее состояние ON/OFF); watchdog: SCM-проверка (`service_state`) + грейс 2 проверки + авто-рестарт (по умолчанию ВКЛ, до 3 попыток за 5 мин) + уведомление; `detect_foreign_dpi_tools()` (GoodbyeDPI) при старте; профайлер F12 (FPS+CPU) в Tk; compact-режим: Ctrl+Shift+C, выход по клику, deiconify; звуки `sounds/start.wav|stop.wav` (fallback — синтез).

### Волна 2 (готово)
- **Модульное ядро (A1/A3-срез)**: `install_zapret_service(zapret_dir, bat_path)`, `launch_winws_direct(zapret_dir, bat_path)`, `stop_services_and_processes()`, `list_strategies(zapret_dir)`, флаг `_tcp_timestamps_done`; класс Tk — тонкие обёртки.
- **B1**: паритет preamble — GameFilter-порты из `utils/game_filter.enabled` (`read_game_filter`, валидация как в service.bat), user-списки (`ensure_user_lists`), `netsh timestamps=enabled` (`enable_tcp_timestamps`), реестровая запись `HKLM\...\Services\zapret\zapret-discord-youtube`.
- **B8**: `is_trusted_github_url`, `fetch_zapret_latest_release` (GitHub API + digest), `update_zapret_data()` (скачивание, sha256, safe-extract, миграция user-данных); динамический выбор папки пакета: `_find_installed_package_roots()` + `_package_version_key()` + `locate_zapret_dir()` выбирает новейшую установленную версию; очистка сохраняет активную папку.
- **B3/B6**: `SERVICE_PROBES` (YouTube/Discord/Telegram/Google), `probe_services()`, `score_probe_results()`; в web-UI чип SRV, кнопка «Проверить», мониторинг раз в 20 с.
- **B4**: авто-подбор стратегии (`auto_test_strategies` в webapp: перебор 22 стратегий, пробы, выбор лучшей, стоп при 100%, сохранение активной+избранной).
- **B5**: `get_current_network()` (SSID Wi-Fi / `ethernet`), профили в конфиге, авто-применение при старте, кнопка «Профиль сети».
- **B7**: детект чужих DPI-утилит.
- **B9**: редактор 4 пользовательских списков (web-UI, guard по именам).
- **B11 (частично)**: TgWsProxy auto-start при `proxy_enabled`, сохранение состояния; порт/секрет/QR — нет.
- **B12**: `KNOWN_WINWS_SHA256` (1.10.3), `check_winws_hash()` — предупреждение, не блокирует.
- **B13 (частично)**: `list_active_interfaces()` — диагностика (в лог/state), без `--wf-iface`.

### Волна 3 (частично)
- **A7-спайк**: `webapp.py` (Api: state/toggle/strategies/settings/proxy/logs/tests/update check+apply/changelog/export/import/листы/пакеты/авто-подбор/трей) + `webui/index.html`.
- **Собрано**: `ZapretWeb.spec` → `dist/ZapretWeb.exe` (46.5 МБ, UAC-admin, datas: zapret_data.zip, icon, sounds, webui; hiddenimports: `webview.platforms.edgechromium`, `clr_loader`, `pythonnet`; ВАЖНО: customtkinter/pystray/keyboard НЕ исключать — webapp импортирует `zapret_new_win`).
- **C-порт (сделано)**: C1-lite (спарклайн CPU/RAM 90 c), C2-lite (тост+авто-открытие стратегий при первом запуске), C3 (Ctrl+Shift+Z, F12), C5 (поиск по стратегиям), C6 (тосты вместо alert; `window.alert` переопределён), C7-lite (свой акцентный цвет `theme_custom`), C8 (трей у web-версии), C10 (частично, title-подсказки), C12 (модалки скроллятся).

### Волна 3 — сессия 2 (сделано)
- **C9 (полная RU/EN web-UI)**: словарь переводов теперь один — `TRANSLATIONS_DATA` в `zapret_new_win.py` (было 25 ключей → 80, parity RU/EN проверяется smoke); `Api.get_state()` отдаёт `texts` для текущего языка; в `webui/index.html` статичные строки помечены `data-i18n`/`data-i18n-title`, динамические идут через `T(key, vars)`, статус — через `status_key` (`ready/on/busy/error/no_file/fail`); переключатель — существующий тумблер «Язык» (мгновенно, на следующем poll ≤1 с); `<html lang>` обновляется. Changelog-КОНТЕНТ остаётся русским (ключи — локализованы).
- **A2 (single-writer state)**: в `webapp.Api` добавлены `queue.Queue` + поток `_command_loop`; статус пишет ТОЛЬКО воркер через `_transition(status, key)` (добавлены `status_key`, `STATUS_TEXT`); API-методы (`toggle`, `toggle_proxy`) только кладут команды; watchdog издаёт `restart`/`fail` командами (с защитой от дублей через `_cmd_queue.empty()`); авто-подбор использует `_submit("start"/"stop", wait=True)`; `quit_app` — `stop` через очередь. Гонки двойного старта закрыты проверкой очереди в `toggle`.
- **C4-web (compact)**: `Api.set_compact(enabled)` — уменьшает окно до 300×140, снимает MinimumSize через `window.native` (WinForms Form) + `System.Drawing.Size` из `webview.platforms.winforms`, ставит `on_top`; сохраняет/восстанавливает геометрию; JS: класс `body.compact`, клик в оверлее — выход, хоткей `Ctrl+Shift+C` (как в Tk), кнопка «Мини-оверлей». `ZapretWeb.spec`: добавлен hiddenimport `webview.platforms.winforms`.
- **C5-scores**: результат авто-подбора сохраняется по стратегиям в конфиг (`scores`, 0..1, округление до 3 знаков); `run_tests` ставит лучшей 1.0; в web-UI — проценты у стратегий и сортировка «A-Z / По тестам» (кнопки в модалке стратегий).
- **B3-полный**: PS-раннер вынесен в ядро — `run_strategy_tests(zapret_dir, on_line, should_continue)` (ANSI-strip, `NO_UPDATE_CHECK=1`, cp866, CREATE_NO_WINDOW, авто-terminate при `Best config:`); **оба UI** используют его (webapp `_tests_worker`; Tk `run_service_tests` — колбэк `on_test_line` с ETA-логикой сохранён).
- **B11-полный**: ядро знает формат TgWsProxy (config.json: `%APPDATA%\TgWsProxy` или portable `TgWsProxy_data` рядом с пакетом; поля host/port/secret; ссылка `tg://proxy?server=..&port=..&secret=dd<hex>`; дефолты port=1443, host=127.0.0.1): `read_proxy_config`, `write_proxy_config` (атомарно), `proxy_link`, `proxy_health_ok`. Web-UI: модалка TgProxy (статус+health, порт, секрет, ссылка, копирование, сохранение с перезапуском, старт/стоп). QR не делали — ссылка копируется (в TgWsProxy fallback тоже копирование).
- **Фикс общего конфига**: `save_config` в Tk и `_save_config` в webapp теперь MERGE с существующим JSON (раньше каждый UI затирал чужие ключи: profiles/scores/repair/theme_custom).
- **Фикс повреждённого пакета (payload self-heal, найдено пользователем)**: рабочая папка `C:\ZapretLauncher\zapret-discord-youtube-1.10.3` содержала только `bin` (4 файла: winws.exe/WinDivert/cygwin — «ручное обновление» по инструкции Flowseal) → старый код считал пакет установленным (проверял только `bin/winws.exe`), zip не распаковывал, а `cleanup_old_zapret_folders` удалил полную папку 1.10.0 — стратегии/TgWsProxy исчезли. Исправления: `payload_complete()` (winws + .bat + TgWsProxy + lists), `locate_zapret_dir` предпочитает полные папки, `core.ensure_payload()` (при неполном/старом пакете распаковывает bundled zip и мигрирует user-файлы; вызывается из Tk `_ensure_payload` и `webapp.main`), cleanup пропускается, если активный пакет неполный, `update_zapret_data` тоже использует `payload_complete`. Рабочий каталог пользователя восстановлен из `zapret_data.zip` (53 файла).

### Волна 4 (начато)
- **F1 (CI/CD)**: `.github/workflows/ci.yml` — job `smoke` на push/PR, job `build` на теги `v*`/ручной запуск: проверка version↔tag, сборка Zapret+ZapretWeb, пересчёт хэша CI-сборки в манифесте, artifacts; на теге — sparse-клон main, коммит манифеста (continue-on-error), GitHub Release с exe+манифестом (softprops/action-gh-release@v2). Локально проверены: YAML, sparse-клон реального репо. На GitHub ещё не запускался.
- **H4 (ruff)**: `ruff.toml` (E4/E722/E9/F/W605/I001/UP020/UP031/SIM102/SIM115/PLR1730; E501 и защитный стиль `except Exception` намеренно вне набора), 14 автофиксов + 34 bare-except → `except Exception:` + ручные SIM/UP-фиксы; шаг `ruff check .` в CI (блокирующий). mypy пока нет — H4 «частично».
- **E7 (аудит/SBOM)**: в CI шаги pip-audit (JSON-отчёт + вывод, `continue-on-error`, локально: 15 зависимостей, 0 уязвимостей) и CycloneDX (`cyclonedx-py requirements requirements.txt -o sbom.json`, `continue-on-error`); артефакты `audit-reports`. Report-only, не блокирует релиз.
- **F7 (uninstaller)**: `tools/uninstall.ps1` — UAC-самовозвышение, остановка/удаление служб zapret/WinDivert/WinDivert14, taskkill winws/TgWsProxy/Zapret/ZapretWeb, удаление ярлыка Startup `Zapret.lnk` и записи HKCU Run `TgWsProxy`, удаление данных (`-KeepData` — сохранить, `-PurgeTgProxy` — дочистить TgWsProxy, `-DryRun` — безопасная проверка). Файл в UTF-8 **с BOM** (иначе PS 5.1 ломает кириллицу); проверен парсером и dry-run.
- **A3 (CLI)**: `zapret_cli.py` — status (JSON), list, probe, interfaces (без админа) + start/stop/test (проверка прав, коды возврата). Использует ядро; smoke гоняет `list`/`status`.
- **F6 (единый CHANGELOG)**: `CHANGELOG.md` — источник; `tools/sync_changelog.py` генерирует блок `CHANGELOG` в zapret_new_win.py (между маркерами `# CHANGELOG:BEGIN/END`) и `changelog` в update_info.json; режим `--check` (в smoke и CI). Внимание: в замене re.sub используется lambda — иначе `\\` в строках схлопывается (уже наступали).
- **G10 («Сообщить о проблеме»)**: `core.build_issue_url()` (тело с версией/ОС/стратегией/хвостом лога, ФИО пользователя из путей заменяется на `<user>`), webapp `report_problem()` открывает issue в браузере; кнопка в настройках.
- **H1 (pytest)**: `tests/test_core.py` (12 тестов: парсер, порты, URL-trust, payload_complete, ротация, issue-URL и т.д.); шаг `python -m pytest -q` в CI.
- **H6 (логи)**: ротация по размеру `_rotate_log_file` (2 МБ, `.1`) для launcher_debug.txt и events.jsonl; структурированные события `log_event()` (JSONL) — webapp логирует transition/import_bat.
- **E5 (SCM recovery)**: при создании службы zapret прописывается `sc failure zapret reset= 86400 actions= restart/5000/restart/10000/restart/30000`.
- **C11 (частично)**: кнопка «Импорт .bat» в модалке стратегий — выбор файла через диалог pywebview, копирование в пакет и авто-выбор; настоящий drag&drop в WebView2 не поддерживается pywebview.
- **I7 (portable)**: `portable.txt` рядом с exe (или `--portable`) → данные в `<exe_dir>\ZapretLauncher_data`; `is_portable_mode()`, `tools/make_portable.py` собирает portable-zip.
- **F2 (каналы/откат)**: `UPDATE_CHANNELS` stable/beta (`update_info_beta.json`), настройка канала в UI, `rollback_update()` меняет exe с резервной `.old`-копией и перезапускает.
- **F5 (зеркала)**: манифест может содержать `mirrors: [...]`; `update_download_candidates()` фильтрует по allowlist и качает по очереди.
- **E1 (подпись)**: `ed25519.py` (RFC 8032, проверен тест-векторами), `manifest_signing_payload/ok`, `UPDATE_PUBKEY_HEX` (пусто = проверка отключена), `tools/sign_manifest.py` (--gen-keys/подпись/--pub).
- **D3/D6**: `detect_quality_preset()` (по ядрам/RAM), настройки quality (auto/low/medium/high) и battery_saver; при батарее — low + реже пинг; web-UI режет историю спарклайна и анимации (`.lowq`).
- **G14**: `seconds_since_last_input()`; idle-hide в web (minimize) и Tk (iconify) по настройке `idle_hide_min`.
- **C6/C8 (web)**: трей с цветной иконкой по статусу, меню стратегий (radio, 12 шт.), Windows-уведомления через pystray.on notify при вкл/выкл.
- **C7-lite/C3/C1**: светлая тема (CSS-переменные), настраиваемый хоткей toggle (захват комбинации), линия ping в спарклайне.
- **G4/G6**: `fullscreen_game_active()` + приоритет winws и пауза проб при игре; `speedtest()` — замер проб с историей и сравнением с предыдущим другим состоянием.
- **A9/I3**: `installer/zapret_launcher.iss` (admin-установщик, ярлыки, запуск uninstall.ps1 при удалении); `tools/make_portable.py`. Inno-компиляция локально НЕ проверялась (Inno Setup не установлен).
- **H8**: `tools/gen_golden.py` + `tests/golden/zapret-discord-youtube-1.10.3.json` (регрессия парсера).
- **H4-mypy**: `mypy --ignore-missing-imports zapret_cli.py ed25519.py tools/ tests/` — чисто, шаг в CI.

### Сессия 3 (G12 + установочный апдейт + ProgramData)
- **G12 (Discord Rich Presence)**: `discord_rpc.py` — класс `DiscordPresence` (pypresence IPC, отдельный daemon-поток, троттлинг 15 c, реконнект с бэкоффом 120 c, все ошибки глушатся, лог не спамится). `core.discord_payload()` строит details/state/start (стратегия, ВКЛ/ВЫКЛ/тест, аптайм), кнопка «Установить ZapretLauncher» → репозиторий. Конфиг `discord_rpc` (дефолт **False**) + опциональный `discord_client_id`; тумблеры: web-drawer и Tk-настройки (кнопка Y=676..706). `DISCORD_CLIENT_ID` в ядре пуст → presence спит, пока не впишете Client ID приложения Discord (Developer Portal). Обновления: на переходах статуса/смене стратегии + из monitor/render loop (не чаще 15 c).
- **A9/I3 (обновление через установщик)**: манифесты получили `installer_url` + `installer_sha256`; `core.update_mode()` (portable по `portable.txt`/`is_portable_mode()`, иначе installed), `core.installer_update_available()`, `core.launch_installer_and_restart()` (detached `cmd /c start /wait Setup.exe /SILENT /NORESTART /CLOSEAPPLICATIONS && start installed exe`). webapp `perform_update()`: подпись манифеста (Ed25519) → installed+installer → скачать Setup (SSL, лимит 200 МБ, sha256), запустить, выйти; иначе фолбэк на self-update exe (portable). `_download_update_file()` общий для exe/установщика.
- **Установщик (.iss)**: `[Dirs] {commonappdata}\ZapretLauncher Permissions: admins-full users-read` (E2 DACL), `[Run] … --install-service` (ставит службу один раз, silent-friendly), ярлык рабочего стола (tasks desktopicon) и меню Пуск, uninstall.ps1 в {app}. `core.cli_install_service()` — no-op если служба уже есть; поддержан в Tk main и webapp main.
- **E2 (ProgramData + DACL + миграция)**: `_pick_data_dir()` теперь portable → `%ProgramData%\ZapretLauncher` → `C:\ZapretLauncher` → `%LOCALAPPDATA%`; `_dir_writable()`, `_programdata_dir()`, `data_dir_mode()`. `migrate_from_legacy_dir()` переносит данные из **всех** старых каталогов (C:\ZapretLauncher и %LOCALAPPDATA%) в активный; `_legacy_zapret_dirs`/`_find_installed_package_roots` учитывают legacy-корни. `ensure_data_dir_acl()` (icacls, Administrators Full / Users Read, best-effort). **UI по-прежнему требует админа** — winws/WinDivert работают от SYSTEM, пересоздание службы при смене стратегии требует прав; снятие админа требует service SDDL + отдельного хелпера (см. риски).
- **CI**: установщик собирается на теге (choco innosetup) **до** обновления манифеста; `tools/ci_update_manifest.py` пишет hash exe, installer_url/installer_sha256 (из собранного Setup), подписывает манифест при `secrets.MANIFEST_SIGNING_KEY` (hex seed; сверяется с `UPDATE_PUBKEY_HEX`). Setup.exe попадает в Release.
- **uninstall.ps1**: добавлены `%ProgramData%\ZapretLauncher`, ярлык рабочего стола и папка в меню Пуск; BOM/парсер/dry-run проверены.
- **Тесты/смоук**: pytest 24 (+4: presence no-op, payload, installer helpers, ci_update_manifest), smoke 81 (+9: rpc off by default, упаковка pypresence, поля манифеста, helpers, .iss-контент, ci-инструмент, webapp state discord/update_mode/data_dir_mode/installer_update).
- **Установщик 2.0 (сессия 3b)**: выбор интерфейса компонентами (`web` = ZapretWeb.exe по умолчанию, `tk` = Zapret.exe, `exclusive`, валидация «хотя бы один» в [Code]); оба exe внутри Setup; `[InstallDelete]` чистит старый exe при смене компонента; ярлык на рабочем столе на выбранный exe (`{code:GetMainExe}`), меню Пуск — по компоненту; стилизация мастера (`wizard_image.bmp`/`wizard_small.bmp` через `tools/make_installer_art.py`, приветствие RU/EN, modern-стиль).
- **Фикс ошибки установки 740** («CreateProcess: сбой, код 740»): по докам Inno запись с флагом `postinstall` по умолчанию запускается как **исходный (неэлевированный) пользователь** (`runasoriginaluser`), а `Zapret.exe` имеет манифест requireAdministrator → 740. Исправление: `runascurrentuser` на обеих [Run]-записях (служба + запуск после установки).
- **Апдейтер и установщик**: при старте приложение пишет `install_mode.json` (`exe`, `components`), `installed_exe_path()`/`installed_components()` учитывают его; silent-апдейт передаёт `/COMPONENTS="web|tk"` — выбор интерфейса сохраняется при обновлении; файлы заменяются (`ignoreversion` + тот же AppId = upgrade).
- **Тесты/смоук (обновлено)**: pytest 25 (+install_mode helpers), smoke 83 (+installer art, install-mode helpers; .iss-чек обновлён под компоненты/runascurrentuser/арт).
- **«osu-style» (сессия 3c)**: установщик — `WizardStyle=modern dark includetitlebar`, `WizardSizePercent=110`, фон картинок под тему (`WizardImageBackColor=#0a0b1e`), страница «Что внутри» (`installer/info_before.txt`, RU/EN). Приложение — стартовая анимация: web-UI сплэш (расходящиеся кольца + логотип + точки, пропуск кликом, авто-скрытие), Tk — `_render_intro` (кольца/логотип, пропуск кликом); настройка `intro` (default True, тумблер в web, конфиг в Tk; при `minimal` выключено). Плюс живой фон web-UI (canvas-частицы по настройке «Эффекты», плотность от качества/батареи) и пульсация главного круга при ON (`@keyframes pulse`).
- **Тесты/смоук (3c)**: pytest 25, smoke **86** (+startup animation assets, installer dark style, webapp intro setting).
- **«Вау»-доработки (сессия 3d)**: Discord — Client ID вводится в UI (web: модалка по клику на подсказке под тумблером; Tk: `simpledialog` при включении), статус подключения («укажите ID / ожидание Discord / подключено») показывается под тумблером; API `set_discord_client_id` (валидация 17–20 цифр). Анимация запуска прокачана: Tk — вращающиеся дуги + орбитальные частицы, 2.4 c; web — glow-логотип, 2 c. Установщик: фоновая графика мастера (`wizard_back.bmp`, opacity 90/255), крупный арт 328×628, **звуки** (whoosh `sound_intro.wav` + финальное арпеджио `sound_done.wav`, MCI из [Code], чекбокс «Звуковое сопровождение» на приветствии, в silent не играют), брендинг приветствия/финала, VersionInfo в свойствах exe. Песочный тест установщика (`tools/installer_sandbox_test.py`) — **PASS**: silent `/COMPONENTS=tk` и `web`, смена компонента чистит старый exe.
- **Тесты/смоук (3d)**: pytest 25, smoke **92** (+wow-ассеты/код, sandbox-инструмент, discord-модалка, client id API, embed-tool).
- **Полностью кастомный установщик (сессия 3h)**: стандартные страницы Inno скрыты (`ShouldSkipPage` для welcome/info/components/dir/tasks/ready; шапка `PageNameLabel/PageDescriptionLabel/Bevel` выключена). Свои страницы: **вступление** (анимированный баннер 16 кадров через `SetTimer`+`CreateCallback`, карточки выбора WebView2/Tk радио-кнопками, инфо-строка, чекбокс звука, большая кнопка «УСТАНОВИТЬ»), **установка** (свой прогресс-бар из картинок + проценты через `CurInstallProgressChanged`, статус-строка), **финал** (баннер с галочкой, «ВСЁ ГОТОВО!», список запуска). Всё локализовано через `[CustomMessages]` RU/EN. Установщик по-прежнему собирает Setup для обоих exe и ставит службу один раз.
  - **Важно**: при пропущенной странице компонентов Inno **игнорирует `/COMPONENTS`** — silent-обновление выбирает интерфейс своим флагом `/UI=web|tk`, который парсится из `GetCmdTail` в [Code]; апдейтер передаёт оба (`/COMPONENTS=... /UI=...`).
  - Песочный тест расширен: проверяет `/UI=tk` → `Zapret.exe`, `/UI=web` → `ZapretWeb.exe` (+ удаление старого exe) — **PASS**.
  - Правка раскладки по фидбеку: кнопки Inno позиционируются по правому краю — **не менять их Width/Height** (иначе наезжают друг на друга); размеры элементов уменьшены (баннер 96px, шрифты 8–16pt), окно `WizardSizePercent=115`, область контента считается с учётом реального положения/видимости большой картинки мастера.
  - **Веб-версия временно убрана из установщика** (по решению пользователя): `[Components]` нет, ставится только `Zapret.exe`; карточки выбора заменены списком возможностей; `InstallDelete` всё ещё чистит старый `ZapretWeb.exe`. Выбор интерфейса вернём, когда будет готов интересный web-функционал. `ZapretWeb.exe`/`ZapretLite.exe` продолжают собираться отдельно (не в установщике). Setup теперь ~37.8 МБ.
  - **Переход 17.3 → установщик (сессия 3i)**: старые 17.3-клиенты читают из манифеста только `download_url` + `hash` и заменяют свой exe скачанным файлом. Поэтому в манифестах `download_url`/`hash` теперь указывают на **Setup.exe** (та же сборка, что `installer_url`/`installer_sha256`): старый клиент скачает установщик, «заменит» им свой exe и запустит его → откроется мастер → приложение установится в Program Files (миграция на установленную версию). Новые 17.4: installed-режим — silent-апдейт (`/SILENT /UI=…`), portable — та же миграция на установленную версию через `download_url`. `tools/ci_update_manifest.py` при наличии Setup пишет и `download_url`/`hash`, и `installer_*` = Setup; без Setup — прежний self-update exe. Smoke-чек `manifest 17.3->installer transition` это фиксирует. **Откат семантики**: вернуть `download_url` на exe и `hash` = sha exe (и снять чек).
- **Discord ID вшит (сессия 3g)**: `DISCORD_CLIENT_ID = "1553946245704192142"` — presence готов у всех пользователей без ввода (только тумблер). Бэкофф реконнекта снижен 120→60 c (быстрее подхватывает запущенный позже Discord). Живая проверка на машине: `DiscordNotFound` — десктопный Discord не запущен, поэтому статуса не видно; RPC требует запущенного Discord-клиента (браузерная версия не подходит).
- **Discord без ввода у пользователя (сессия 3f)**: Client ID приложения вшивается в сборку один раз автором — `python tools/set_discord_id.py <ID>` (валидация 17–20 цифр, `--clear`); приоритет: конфиг → env `ZAPRET_DISCORD_CLIENT_ID` → вшитая константа `DISCORD_CLIENT_ID` (`core.discord_client_id()`). Если ID вшит, пользователь видит только тумблер и статус («ожидание Discord…» / «подключено») — никакого ввода. UI-модалка остаётся лишь fallback-ом, когда ID не вшит.
- **Изоляция тестов (сессия 3e)**: `ZAPRET_DATA_DIR` (env) — приоритетный каталог данных для тестов/dev; smoke и pytest пишут конфиг/логи в свою temp-папку и **не засоряют реальный лог** пользователя. Смоук-проверка каталога данных обновлена («isolated in tests»). Замечено вживую: после установки данные приложения мигрировали в `%ProgramData%\ZapretLauncher` (лог, конфиг, `install_mode.json` — на месте).

---

## 5. Ключевые технические решения

1. **A6/A7/A8** — взаимоисключающие UI-пути. Пользователь выбрал **A7 (WebView2/pywebview)**. A6 (виджеты customtkinter) и A8 (Qt) НЕ делать.
2. **A2 (single-writer state)** перенесён в волну 3: делать в web-ядре (Api = единственный писатель, очередь событий), чтобы не рефакторить дважды. В Tk-версии остаётся как есть.
3. Релизное переключение: legacy `Zapret.exe` остаётся в манифесте до порта C9/A2 и теста web-версии; затем решить: single exe (WebView2) или два exe.
4. Данные и конфиг общие у Tk и web (`C:\ZapretLauncher`, `launcher_config.json`, schema v2).
5. Звуки: `start` = opencode `yup-05-CuuaeyjC.aac`, `stop` = `nope-02-EygnDbCM.aac`; в asar всего 26 (alert-01..10, bip-bop-03..09, nope-02..12, staplebops-03..07, yup-01..05) — можно перевыбрать. Извлечение/конвертация: скрипты были в `%TEMP%\opencode\{find_audio,extract_sounds,convert_sounds}.py` (могут быть удалены; логика: парсинг заголовка asar + PyAV в PCM WAV 44.1k mono).
6. web-UI общается с Python поллингом `get_state()` раз в 1 с (без push). Локализация — из `texts` в state (после poll ≤1 с), словарь — единый в ядре.
7. TgWsProxy (B11): конфиг `%APPDATA%\TgWsProxy\config.json` (или portable `<пакет>/TgWsProxy_data/`), ключи host/port/secret; ссылка Telegram `tg://proxy?server=<host>&port=<port>&secret=dd<secret>` (префикс `dd` — формат Flowseal), при host=0.0.0.0 подставляется локальный IP (fallback 127.0.0.1).
8. A2: статус системы — только воркер `_command_loop` (`_transition`); всё остальное (watchdog, авто-подбор, кнопки) издаёт команды. При добавлении новых действий со статусом — не писать `self.status` напрямую.

---

## 6. Проверки

- `python tools/smoke.py` → **92/92 PASS**; `python -m pytest -q` → **25/25 PASS**; `python -m ruff check .` — чисто; `python -m mypy --ignore-missing-imports zapret_cli.py ed25519.py tools/ tests/` — чисто (12 файлов). Покрытие: py_compile, отсутствие мёртвого кода, наличие helpers, отсутствие `shell=True` в коде, zip↔папка 1:1 + корень + winws/TgWsProxy, парсер всех стратегий (22), `split_windows_args`, `validate_port_range`, `read_game_filter`, `is_trusted_update_url`, zip-slip, `payload_complete`/`ensure_payload` (самолечение пакета), i18n parity, `ensure_user_lists`, звуки (RIFF), волна-1 helpers, каталог данных, schema v2, модульные функции (+`run_strategy_tests`), `_package_version_key`, `is_trusted_github_url`, пробы и скоринг, proxy helpers (`proxy_link` в формате `dd`), шим winws-хэша, интерфейсы, сеть, `webapp.Api` (state/strategies/settings/lists/guard/autotest/interfaces/network/single-writer/texts/compact/scores/proxy), i18n-ключи web-UI (40 статичных + 27 динамических ключей проверяются на наличие в словаре), `webapp` вызывает `core.ensure_payload()`.
- `python -m py_compile zapret_new_win.py webapp.py` — OK. JS в `webui/index.html` проверен `node --check`-эквивалентом (`new Function`).
- Возможные ложные срабатывания smoke: он создаёт `C:\ZapretLauncher`, читает конфиг и **пишет** его (`webapp set_setting("theme", ...)`) — безопасно, но конфиг пользователя перезаписывается (merge сохранён).

---

## 7. Сборка

```powershell
# зависимости
pip install -r requirements.txt
pip install pyinstaller

# данные (если менялись)
python tools/rebuild_zip.py

# legacy Tk exe
python -m PyInstaller --noconfirm Zapret.spec      # -> dist/Zapret.exe

# WebView2 exe
python -m PyInstaller --noconfirm ZapretWeb.spec   # -> dist/ZapretWeb.exe

# хэш для update_info.json
python tools/get_hash.py dist\Zapret.exe
```

**Не забыть**: после сборки релизного exe — обновить `update_info.json` (version/hash/url), залить exe в Release.

### Релиз через CI (F1, рекомендуется)

`.github/workflows/ci.yml`:
- на push в `main` и PR — job `smoke` (установка requirements + `python tools/smoke.py`);
- на теги `v*` и `workflow_dispatch` — job `build` (после smoke): проверка `update_info.json.version == tag`, сборка обоих exe, пересчёт хэша **CI-сборки** в `update_info.json`, upload artifacts; на теге — клон `main` (sparse), коммит манифеста в main (continue-on-error на случай branch protection) и GitHub Release с `Zapret.exe`, `ZapretWeb.exe`, `update_info.json`.

Процедура релиза: обновить version/changelog в `update_info.json` и коде → закоммитить в `main` → поставить тег `vX.Y` и запушить его. CI соберёт, впишет фактический хэш CI-сборки в манифест main и создаст релиз. Важно: локальная сборка и CI-сборка **не совпадают побайтово** (поэтому хэш пересчитывается в CI; не полагаться на локальный хэш для релиза CI). Если push манифеста был заблокирован — взять хэш из лога шага «Update manifest hash for CI build» и поправить `update_info.json` в main вручную. Права: repo → Settings → Actions → Workflow permissions → Read and write.

---

## 8. Известные риски/долги

- `update_info.json`: `hash` и `installer_sha256` = Setup.exe (переходный релиз, сессия 3i). В релизе v17.4 на GitHub лежат Setup (37.8 МБ, Tk-only) и свежий `Zapret.exe` (для ручной загрузки; в авто-обновлении не используется). CI на теге пересоберёт Setup и перезапишет хэши своими.
- Discord RPC: `DISCORD_CLIENT_ID` пуст (нужен Client ID приложения Discord); без него тумблер ничего не делает (тихий no-op).
- E2: UI остаётся admin (uac_admin): winws/WinDivert требуют SYSTEM-прав, служба пересоздаётся при смене стратегии. Для non-admin UI нужен service SDDL (start/stop) + отдельный хелпер для netsh/пересоздания — не делалось (риск/вне объёма).
- Миграция данных в ProgramData: если служба запущена во время первого старта, перемещение папки пакета может не пройти (файлы заняты) — код пропускает занятые элементы и повторяет при следующем запуске.
- `dist/Zapret.exe` / `dist/ZapretWeb.exe` — СТАРЫЕ сборки (до C9/A2/C4/B3/B11). Перед релизом пересобрать оба (раздел 7).
- Compact-режим web (`set_compact`) дёргает WinForms-форму через `window.native` (private API pywebview) — при обновлении pywebview возможны изменения; код в try/except, при ошибке просто вернёт `{"ok": false}` (окно не уменьшится).
- Старые сборки (до фикса self-heal) при неполном пакете могли удалить полную папку версии — у пользователя такое уже произошло (восстановлено вручную из zip). Новые сборки лечат это сами (`ensure_payload`), но при откате на старую версию поведение вернётся.
- QR-код для TgProxy не реализован (есть ссылка + копирование).
- Changelog-контент не локализован (только элементы интерфейса).
- `ZapretWeb.exe` не участвует в автообновлении; решение по релизу отложено.
- webapp импортирует `zapret_new_win` целиком (тяжёлые ctk/pystray/keyboard в бандле web-exe). После A1 (разделение модулей) — уменьшить.
- `KNOWN_WINWS_SHA256` нужно расширять при обновлении пакета (после `update_zapret_data` можно логировать новый хэш и добавлять).
- `LICENSE` — правообладатель указан «Aikiovade», проверить.
- README описывает сборку Tk; после переключения на WebView2 — обновить.
- Git: 205 МБ трекаемых артефактов (build/dist/zip/папка), история не чищена; коммитов нет.
- В `zapret_data\...\lists\ipset-all.txt.backup` (556 КБ) — upstream-файл, не мусор.
- Служба `zapret` при выходе удаляется (`stop_process_logic`), включая WinDivert-службы (как в upstream service.bat).

---

## 9. ПОЛНЫЙ ОСТАТОК СКОУПА (выбор пользователя)

Легенда: ✅ сделано | ◐ частично | ✗ не начато

### A — архитектура
- A1 модульный рефакторинг `core/win32/domain/ui` — ◐ (ядро службы/хелперы вынесены)
- A2 single-writer state + Command/очередь — ✅ (в webapp.Api; Tk-версия по-прежнему как была)
- A3 core как библиотека + CLI — ✅ (zapret_cli.py + console script `zapret-cli` в pyproject.toml)
- A4 плагин-система стратегий — ✅ (метаданные <bat>.json, hot-reload, рейтинг из scores; полноценного plugin-API нет)
- A5 абстракция `BypassBackend` — ✅ (WinwsBackend + MockBackend для dev-режима)
- A6 widgets — НЕ ДЕЛАТЬ (выбран A7)
- A7 WebView2 — ◐ (спайк есть, релиз не переключён, C-порт не завершён)
- A8 Qt — НЕ ДЕЛАТЬ
- A9 установщик Inno/NSIS/onedir — ◐ (installer/zapret_launcher.iss + CI-сборка на теге + установочный апдейт в приложении; локально Inno нет — компиляция не проверена, exe без Authenticode)

### B — ядро обхода
- B1 паритет preamble — ✅
- B2 (исключён пользователем) — не делать
- B3 тест-раннер — ✅ (core.run_strategy_tests; оба UI)
- B4 авто-подбор/ротация — ✅ (авто-подбор + авто-ротация при деградации доступности)
- B5 профили сети — ✅
- B6 мониторинг сервисов — ✅ (пробы + SRV + BYPASS)
- B7 детект чужих DPI — ✅
- B8 авто-обновление пакета Flowseal — ✅
- B9 редактор списков — ✅ (web)
- B10 (исключён) — не делать
- B11 TgProxy-менеджер — ✅ (start/stop/autostart/persist + порт/секрет/ссылка-копирование/health; QR — нет)
- B12 hash-пиннинг winws — ✅ (warn-only)
- B13 выбор адаптера — ◐ (диагностика; iface-флаг winws не внедрён)
- B14 (исключён) — не делать

### C — UI (в web-UI, кроме оговорённых)
- C1 дашборд — ◐ (спарклайн CPU/RAM + линия ping; графиков сессий — нет)
- C2 мастер первого запуска — ✅ (пошаговый визард: приветствие → выбор стратегии/авто-подбор → готово)
- C3 настраиваемые хоткеи — ✅ (web: захват комбинации для toggle; F12/compact фиксированы; Tk — как было)
- C4 compact-оверлей — ✅ (Tk + web: resize/on_top/клик-выход/Ctrl+Shift+C)
- C5 поиск/теги/сортировка — ◐ (поиск + сортировка A-Z/по тестам + %-скоры есть; теги — нет)
- C6 Windows-тосты — ✅ (web: pystray notify на вкл/выкл; внутренние тосты остались)
- C7 редактор тем — ◐ (кастомный акцент + светлая тема; полноценного редактора — нет)
- C8 кастомный трей — ✅ (web: цвет иконки по статусу + меню стратегий)
- C9 полная локализация RU/EN web-UI — ✅
- C10 tooltips — ◐
- C11 drag&drop .bat — ◐ (импорт через диалог файла + копирование в пакет; drag&drop в WebView2 pywebview не даёт)
- C12 скролл changelog — ✅ (модалка скроллится)
- C13 виджет на рабочий стол — ✗
- C14 демо/скриншоты — ✗

### D — производительность
- D1 persistent canvas — ✗ (актуально только для Tk; для web — CSS)
- D2 time-based анимации — ◐ (компенсация скорости; dt-модель — нет)
- D3 авто-качество по железу — ✅ (auto/low/medium/high, влияет на web-эффекты)
- D4 статичный фон — ✗
- D5 профайлер — ✅ (F12 в Tk; спарклайн в web)
- D6 режим батареи — ✅ (battery_saver: low-качество + реже мониторинг)
- D7 снижение веса — ◐ (mp3/excludes + ZapretLite.exe без zip, догрузка пакета при первом старте; отдельной догрузки TgWsProxy нет)

### E — безопасность
- E1 подпись манифеста/exe — ✅ (Ed25519-подпись манифеста + инструмент; Authenticode exe — нет)
- E2 ProgramData + DACL, UI без админа — ◐ (данные в %ProgramData%\ZapretLauncher с DACL Admins/Users + миграция; UI всё ещё требует админа: winws/WinDivert и пересоздание службы — только от админа/SYSTEM)
- E3 служба от ограниченной учётки — ✗
- E4 RegisterHotKey вместо keyboard — ✗
- E5 SCM recovery — ✅ (health/рестарты + `sc failure` при установке службы)
- E6 opt-in крашрепорты — ✅ (локальные dumps в APP_DATA_DIR/crashes + хвост в «Сообщить о проблеме»; сетевой телеметрии нет)
- E7 pip-audit/SBOM — ✅ (pip-audit + CycloneDX в CI, report-only; артефакты audit-reports)

### F — релизы
- F1 CI/CD — ✅ (GitHub Actions: smoke на push/PR; сборка+манифест+release на теги v*; нужен первый прогон на GitHub для проверки прав токена)
- F2 каналы stable/beta + откат — ✅ (update_info_beta.json + rollback_update)
- F3 раздельное версионирование данных/exe — ✅ (`package` в манифесте, версия пакета в state/UI)
- F4 delta-обновления — ✗
- F5 зеркала/fallback — ✅ (поле mirrors в манифесте, allowlist сохранён)
- F6 единый CHANGELOG — ✅ (CHANGELOG.md → генератор → zapret_new_win.py + update_info.json, --check)
- F7 uninstaller — ✅ (tools/uninstall.ps1; интеграция в установщик будет в A9/I3)

### G — продуктовые (исключены пользователем: G1,G2,G3,G7,G8,G9,G11,G13)
- G4 гейминг-режим — ✅ (детект fullscreen + приоритет winws + пауза проб)
- G5 диагностика сети — ◐ (пробы/интерфейсы; DNS/IPv6/MTU — нет)
- G6 speedtest — ✅ (замер проб «до/после» с историей; без bandwidth-теста)
- G10 кнопка «Сообщить о проблеме» — ✅ (issue с предзаполнением, лог без имени пользователя)
- G12 Discord RPC — ✅ (реализовано; чтобы заработало — вписать Client ID в `DISCORD_CLIENT_ID` или конфиг `discord_client_id`)
- G14 авто-скрытие по простою — ✅ (web minimize, Tk iconify)

### H — QA/разработка
- H1 pytest — ✅ (tests/test_core.py, 12 тестов; в CI)
- H2 pywinauto GUI-тесты — ✗
- H3 интеграционные тесты службы — ◐ (tools/ci_service_integration.py + job workflow_dispatch; требует ручного прогона)
- H4 ruff/mypy — ✅ (ruff + mypy в CI; pre-commit: ruff + smoke + changelog-sync)
- H5 dev-режим без админа — ✅ (`--dev`/ZAPRET_DEV=1: MockBackend, без UAC и службы)
- H6 структурированные логи — ✅ (ротация 2 МБ + events.jsonl/log_event; кнопка открытия)
- H7 миграции конфига — ✅ (schema v2)
- H8 golden-тесты парсера по версиям — ✅ (tools/gen_golden.py + tests/golden/<версия>.json + pytest)

### I — радикальные (исключены: I1, I5)
- I2 свой пакет стратегий — ✗ (волна 5)
- I3 установщик — ◐ (Setup.exe из CI + обновление через установщик; осталось: прогнать CI, Authenticode, MSIX не делали)
- I4 кроссплатформенное ядро — ✗ (волна 5)
- I6 режимы Simple/Advanced/Expert — ✅ (web: режим скрывает продвинутые кнопки)
- I7 portable/installed — ✅ (portable.txt/--portable → данные рядом с exe; portable-zip)
- I8 opt-in телеметрия — ✗ (волна 5)

---

## 10. Рекомендованный порядок следующей работы

Сессия 2 закрыла пункты 1–5 прошлого плана (C9, A2, C4-web, C5-частично, B3, B11) и пересобрала exe. Осталось:

1. **Релиз v17.4** (действие пользователя): либо (а) как раньше — залить `dist/Zapret.exe` из локальной сборки в GitHub Release `v17.4` (хэш локальной сборки `7CBF…` уже в манифесте и сверен), либо (б) поставить и запушить тег `v17.4` — CI соберёт релиз и сам обновит хэш в манифесте main (см. раздел 7).
2. **C-остаток**: C7-полный редактор темы, C11-drag&drop (ограничение pywebview), C13 (виджет), C10-tooltips (полное покрытие), C14 (демо/скриншоты), C1-графики сессий.
3. **Release-инжиниринг**: задать `secrets.MANIFEST_SIGNING_KEY` (hex seed) и вписать публичный ключ в `UPDATE_PUBKEY_HEX`; прогнать CI на GitHub (`workflow_dispatch`: build + service-integration) — проверить Inno-шаг и появление `installer_sha256`; Authenticode-подпись exe; F4 (delta-обновления).
4. **Волна 5/остаток**: A1 (модульные пакеты), D1/D2/D4 (Tk-перф), E2/E3/E4 (без админа/учётка службы/RegisterHotKey), H2 (GUI-тесты), I2/I4/I8 (пакет стратегий/кроссплатформа/телеметрия).
5. **Решение по релизу**: переключать `update_info.json`/README на WebView2-сборку (или выпускать оба exe).
6. Долги по мелочи: Client ID для Discord RPC, QR для TgProxy, локализация changelog-контента, `KNOWN_WINWS_SHA256` при обновлении пакета.

---

## 11. Мелочи, которые легко забыть

- `tools/smoke.py` и `tests/` изолированы через `ZAPRET_DATA_DIR` (temp-каталог) — реальный конфиг/лог пользователя больше не затрагиваются. Раньше smoke писал в реальный каталог (в HANDOFF это было помечено как долг).
- `webapp.Api._monitor_loop` дергает все пробы раз в 1 с тиками (ping — 10 тиков, services — 20, bypass — 15).
- Хоткей `Ctrl+Shift+C` (compact) теперь есть и в web (резюмирует окно в мини-оверлей 300×140, клик — выход).
- Переводы: при добавлении строк в web-UI добавляй ключ в ОБА словаря `TRANSLATIONS_DATA` (RU/EN parity — smoke-проверка); `data-i18n` / `T('key')` ключи тоже валидируются smoke'ом.
- `webapp.Api._transition` — единственное место записи `self.status/status_key/status_text`; новые действия оформлять командами в `_dispatch_command`.
- Порт/секрет TgProxy пишутся в `%APPDATA%\TgWsProxy\config.json` (или portable); ссылка — `tg://proxy?...&secret=dd<hex>`; после сохранения запущенный прокси перезапускается.
- E1: `python tools/sign_manifest.py --gen-keys keys.json` → публичный hex в `UPDATE_PUBKEY_HEX` (zapret_new_win.py) → `python tools/sign_manifest.py update_info.json --key keys.json`. Пока ключ пуст, подпись не проверяется (warn в лог); keys.json в .gitignore.
- Portable: `portable.txt` рядом с exe (или ключ `--portable`); данные в `ZapretLauncher_data`. Готовый архив: `python tools/make_portable.py Zapret.exe`.
- Зеркала: в манифесте можно указать `"mirrors": ["https://github.com/.../Zapret.exe", ...]` — качается первое доверенное.
- Установщик: `iscc installer\zapret_launcher.iss` (нужен Inno Setup 6 + оба exe в dist; при удалении вызывается tools/uninstall.ps1 из {app}). Кастомный UI: анимированный баннер, свои страницы/прогресс; silent-выбор интерфейса — флаг `/UI=web|tk` (страница компонентов пропущена, `/COMPONENTS` Inno игнорирует).
- Dev-режим: `python webapp.py --dev` (или ZAPRET_DEV=1) — MockBackend, без UAC и службы (H5); полезно для правки UI.
- G12: Application ID уже вшит (1553946245704192142); для смены — `python tools/set_discord_id.py <ID>` (ссылка для создания: discord.com/developers/applications?new_application=true), затем пересборка. Пользователям вводить ничего не нужно: только тумблер. Для dev — env `ZAPRET_DISCORD_CLIENT_ID`. Пока ID пуст — presence спит (тумблеры безопасны).
- Установочный апдейт: манифест содержит `installer_url`/`installer_sha256`; пустой sha → installed-режим падает в self-update exe. Подпись манифеста в CI включается секретом `MANIFEST_SIGNING_KEY` (hex seed) и требует, чтобы `UPDATE_PUBKEY_HEX` совпадал с этим ключом (иначе CI-шаг упадёт).
- `--install-service` (вызывается установщиком) ставит службу один раз; если служба уже есть — no-op. Полезно и вручную: `Zapret.exe --install-service`.
- ProgramData-миграция выполняется при первом старте; если служба активна, папка пакета может не переместиться (занята) — перенос повторится при следующем запуске; занятые элементы пропускаются поштучно.
- Lite-сборка: `python -m PyInstaller --noconfirm ZapretLite.spec` — exe без zapret_data.zip (~25 МБ), пакет докачивается при первом старте (нужен интернет).
- Теги стратегий: положите рядом с .bat файл `<имя>.bat.json` вида {"title": "...", "tags": ["..."], "description": "..."} — подхватится без перезапуска (A4).
- CI (`.github/workflows/ci.yml`) ещё НЕ коммичен и ни разу не запускался на GitHub. Job `service-integration` (workflow_dispatch) реально ставит/снимает службу — запускать осознанно. Перед первым тегом: включить Actions → Workflow permissions → Read and write (иначе шаг коммита манифеста упадёт, но релиз всё равно создастся — `continue-on-error`). Проверять сначала через `workflow_dispatch`.
- CI-сборка не побайтово равна локальной: хэш в манифесте обновляется в CI; для локального релиза вручную — `python tools/get_hash.py`.
- Полнота рабочего пакета: любые новые проверки «установлено ли» делай через `payload_complete(dir)`, путь к активному пакету — `locate_zapret_dir()` (предпочитает полные), гарантия распаковки — `ensure_payload()`. Не возвращай проверки вида «существует bin/winws.exe» — именно это привело к инциденту с потерей батников/TgWsProxy.
- Перед коммитом гоняй `python -m ruff check .` (правила в `ruff.toml`; E501 и `except Exception`-стиль намеренно не включены). Автофикс: `ruff check . --fix`.
- `tools/uninstall.ps1` обязательно держать в UTF-8 **с BOM** — без BOM PowerShell 5.1 парсит кириллицу как ANSI и скрипт ломается. Проверка: `powershell -NoProfile -ExecutionPolicy Bypass -File tools\uninstall.ps1 -DryRun`.
- CI теперь включает ruff (блокирующий), pip-audit и CycloneDX SBOM (report-only, `continue-on-error` — отчёты в артефакте `audit-reports`). Locally проверено: pip-audit 15 зависимостей / 0 уязвимостей.
- `README.md` бейдж лицензии теперь валиден (LICENSE добавлен).
- `requirements.txt` содержит pywebview; при сборке Tk-exe он не нужен, но не мешает.
- Обновление пакета (B8) тянется с `api.github.com` — при отсутствии сети кнопка «Пакет Flowseal» вернёт ошибку (в логе `fetch_zapret_latest_release error`).
- Для новой версии Flowseal: после `update_zapret_data` обновлять `KNOWN_WINWS_SHA256` (взять хэш из лога/вручную) и, при желании, поднять версию пакета в `FOLDER_NAME` не нужно — работает динамический поиск.
- Все временные скрипты этой сессии лежали в `C:\Users\PC1\AppData\Local\Temp\opencode\` (patch_a/b/c/d/e/f.py, find_audio.py, extract_sounds.py, convert_sounds.py, oc_sounds/) — могут быть удалены, логика воспроизводима.
