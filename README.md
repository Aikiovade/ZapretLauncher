<div align="center">

# 🚀 ZapretLauncher v17.1

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
- 🛡️ **Авто-рестарт (Watchdog):** Фоновый мониторинг работы — если служба обхода закроется, лаунчер сам перезапустит её.
- 🌐 **Детектор обхода (Bypass Check):** Наглядный статус подключения (`✓ WORK` / `✗ FAIL`) для проверки работы соединения.
- 💻 **Мини-оверлей (Compact Mode):** Компактное окно `220x50` поверх всех окон для быстрой работы.
- 📊 **Мониторинг ресурсов (HUD):** Отображение загрузки процессора, оперативной памяти, пинга, времени работы и статистики запусков.
- 🔄 **Автоматическое обновление:** Быстрая онлайн-проверка версий и установка обновлений с индикатором прогресса загрузки (`%`).
- 🎨 **Темы и Мультиязычность:** Различные варианты оформления интерфейса и поддержка двух языков (RU / EN).
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
- `Клик на v17.0` — История изменений («Что нового»).
- `Колёсико мыши` — Прокрутка списка доступных стратегий.

---

## 🛠️ Сборка из исходного кода

```bash
git clone https://github.com/Aikiovade/ZapretLauncher.git
cd ZapretLauncher
pip install customtkinter psutil pystray pillow keyboard
python -m PyInstaller --noconfirm --onefile --windowed --uac-admin --name "Zapret" --icon "icon.ico" --add-data "zapret_data.zip;." --add-data "icon.ico;." --hidden-import "customtkinter" --hidden-import "psutil" --hidden-import "keyboard" --hidden-import "pystray" --hidden-import "PIL" --collect-all "customtkinter" --collect-all "psutil" --collect-all "keyboard" --collect-all "pystray" --collect-all "PIL" --distpath "dist" zapret_new.py
```

---

## ❤️ Благодарности и Авторство

- **[bol-van/zapret](https://github.com/bol-van/zapret)** — создатель оригинальной утилиты `zapret` и компонента `winws`.
- **[Flowseal/zapret-discord-youtube](https://github.com/Flowseal/zapret-discord-youtube)** — автор набора стратегий для Windows и проекта `tg-ws-proxy`.
- **[Aikiovade/ZapretLauncher](https://github.com/Aikiovade/ZapretLauncher)** — автор GUI-лаунчера.
