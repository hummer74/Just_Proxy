# SOCKS5 Proxy Manager / Менеджер SOCKS5 Прокси

![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenSSH](https://img.shields.io/badge/OpenSSH-Required-000000?style=for-the-badge&logo=openssh&logoColor=white)

## 📖 Table of Contents / Содержание
- [English Documentation](#-english-documentation)
  - [Overview](#overview)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Configuration](#configuration)
  - [Troubleshooting](#troubleshooting)
  - [Project Structure](#project-structure)
  - [Security Notes](#security-notes)
- [Русская документация](#-русская-документация)
  - [Обзор](#обзор)
  - [Возможности](#возможности)
  - [Требования](#требования)
  - [Установка](#установка)
  - [Использование](#использование)
  - [Конфигурация](#конфигурация)
  - [Устранение проблем](#устранение-проблем)
  - [Структура проекта](#структура-проекта)
  - [Примечания по безопасности](#примечания-по-безопасности)
- [📄 License / Лицензия](#-license--лицензия)
- [🤝 Contributing / Участие в разработке](#-contributing--участие-в-разработке)

---

## 🇺🇸 English Documentation

### Overview
**SOCKS5 Proxy Manager** is a Windows-based tool that creates a secure SOCKS5 proxy tunnel via SSH connections. It features an automatic system proxy configuration, tray icon monitoring, and a user-friendly interface for managing proxy connections.

### Features
- **SSH Tunnel Management**: Automatically establishes SOCKS5 proxy through SSH connections
- **Smart PAC Configuration**: Generates and serves Proxy Auto-Configuration (PAC) files via local HTTP server
- **System Tray Integration**: Real-time monitoring with visual status indicators (green=online, red=offline)
- **Auto-Recovery**: Automatic cleanup when proxy connection drops
- **Host Selection Menu**: Interactive CLI menu with arrow-key navigation and auto-selection
- **SSH Key Management**: Supports passphrase-protected keys with automatic loading
- **Clean State Management**: Proper cleanup of processes and system settings on exit

### Requirements
- **Windows 10/11** (64-bit)
- **Python 3.8+** with pip
- **OpenSSH Client** (Windows feature)
- **SSH Configuration** (`~/.ssh/config` with host definitions)
- **SSH Private Keys** (RSA/ED25519) in `~/.ssh/`

### Installation

#### 1. Enable OpenSSH Client (Windows)
```powershell
# Run as Administrator in PowerShell
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

#### 2. Clone Repository
```bash
git clone https://github.com/yourusername/socks5-proxy-manager.git
cd socks5-proxy-manager
```

#### 3. Configure SSH
Edit `~/.ssh/config` (create if doesn't exist):
```ssh-config
# Example configuration
Host my-server
    HostName server.example.com
    User username
    Port 22
    IdentityFile ~/.ssh/id_rsa
    IdentitiesOnly yes

# Auto-selected host (add _PRIME suffix)
Host production_PRIME
    HostName prod.example.com
    User admin
    IdentityFile ~/.ssh/prod_key
```

#### 4. Set Passphrase (Optional)
Create `key_pass` file in project root with your SSH key passphrase:
```
your-passphrase-here
```

### Usage

#### Starting Proxy
Double-click `start_proxy.bat` or run:
```bash
start_proxy.bat
```

**Process Flow:**
1. Creates/activates Python virtual environment
2. Installs required packages (first run only)
3. Launches tray monitor in background
4. Displays host selection menu
5. Establishes SSH tunnel and configures system proxy

#### Stopping Proxy
Double-click `stop_proxy.bat` or run:
```bash
stop_proxy.bat
```

**Cleanup Actions:**
- Terminates SSH tunnel and HTTP server
- Removes system proxy settings
- Closes tray monitor
- Deletes temporary files and shortcuts

#### Manual Control via Tray
- **Right-click** tray icon → "Quit Monitor" to stop monitoring
- **Left-click** to see connection status
- Automatic restart attempted if connection drops

### Configuration

#### Customizing PAC Rules
Edit `proxy_pac.back` to modify proxy rules:
```javascript
function FindProxyForURL(url, host) {
    // Add your custom rules here
    if (shExpMatch(host, "*.example.com")) {
        return "DIRECT";
    }
    return "SOCKS5 127.0.0.1:${PORT}";
}
```

#### Port Configuration
Modify in `proxy_start_v25.py`:
```python
config.proxy_port = 1080       # SOCKS5 port
config.pac_http_port = 8080    # PAC HTTP server port
```

#### Auto-Select Host
Add `_PRIME` suffix to host name in SSH config for auto-selection:
```
Host my-server_PRIME
    HostName example.com
    User admin
```

### Troubleshooting

#### Common Issues

**1. "ssh.exe not found"**
```powershell
# Enable OpenSSH Client
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*'
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

**2. Connection Timeouts**
- Verify SSH server is accessible
- Check firewall rules for ports 22 (SSH) and 1080 (SOCKS5)
- Validate SSH key permissions: `icacls keyfile /reset`

**3. Proxy Not Working in Browser**
- Check system proxy settings: `Win + R` → `inetcpl.cpl` → Connections → LAN settings
- Verify PAC URL: `http://127.0.0.1:8080/proxy.pac`
- Test PAC file access in browser

**4. Tray Icon Not Appearing**
- Check if `pythonw.exe` is running in Task Manager
- Restart script as administrator
- Ensure no antivirus is blocking Python scripts

#### Logs and Debugging
- Check Python console output when starting
- Review Windows Event Viewer for system proxy changes
- Monitor with `netstat -ano | findstr :1080` for active connections

### Project Structure
```
socks5-proxy-manager/
├── start_proxy.bat          # Launcher
├── stop_proxy.bat           # Cleanup script
├── proxy_start_v25.py       # Main logic
├── proxy_stop.py            # Termination logic
├── proxy_tray.pyw           # Tray monitor
├── proxy_pac.back           # PAC template
├── key_pass                 # Passphrase file (optional)
├── venv/                    # Virtual environment
├── x_proxy_state.json       # Runtime state (auto-generated)
├── x_ssh_tunnel.pid         # SSH PID (auto-generated)
├── x_http_pac.pid           # HTTP PID (auto-generated)
└── x_tray_monitor.pid       # Tray PID (auto-generated)
```

### Security Notes
- **`key_pass` file**: Store SSH passphrase in plaintext (use only on secure systems)
- **Firewall**: Ensure only localhost can access proxy ports
- **SSH Keys**: Use strong passphrases and key-based authentication
- **Cleanup**: Always use `stop_proxy.bat` to remove system settings
- **Permissions**: Run with user-level privileges (not administrator)

---

## 🇷🇺 Русская документация

### Обзор
**SOCKS5 Proxy Manager** — инструмент для Windows, создающий безопасный SOCKS5 прокси-туннель через SSH соединения. Включает автоматическую настройку системного прокси, мониторинг через иконку в системном трее и удобный интерфейс для управления подключениями.

### Возможности
- **Управление SSH туннелями**: Автоматическое создание SOCKS5 прокси через SSH соединения
- **Умная PAC конфигурация**: Генерация и раздача Proxy Auto-Configuration (PAC) файлов через локальный HTTP сервер
- **Интеграция с системным треем**: Мониторинг в реальном времени с визуальными индикаторами (зелёный=работает, красный=отключён)
- **Авто-восстановление**: Автоматическая очистка при разрыве соединения
- **Меню выбора хоста**: Интерактивное меню с навигацией стрелками и авто-выбором
- **Управление SSH ключами**: Поддержка ключей с парольной фразой, автоматическая загрузка
- **Чистое управление состоянием**: Корректная очистка процессов и системных настроек при завершении

### Требования
- **Windows 10/11** (64-бит)
- **Python 3.8+** с pip
- **Клиент OpenSSH** (компонент Windows)
- **SSH конфигурация** (`~/.ssh/config` с определением хостов)
- **Приватные SSH ключи** (RSA/ED25519) в `~/.ssh/`

### Установка

#### 1. Включение OpenSSH Client (Windows)
```powershell
# Запустить от имени Администратора в PowerShell
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

#### 2. Клонирование репозитория
```bash
git clone https://github.com/yourusername/socks5-proxy-manager.git
cd socks5-proxy-manager
```

#### 3. Настройка SSH
Отредактируйте `~/.ssh/config` (создайте если отсутствует):
```ssh-config
# Пример конфигурации
Host my-server
    HostName server.example.com
    User username
    Port 22
    IdentityFile ~/.ssh/id_rsa
    IdentitiesOnly yes

# Авто-выбираемый хост (добавьте суффикс _PRIME)
Host production_PRIME
    HostName prod.example.com
    User admin
    IdentityFile ~/.ssh/prod_key
```

#### 4. Установка парольной фразы (Опционально)
Создайте файл `key_pass` в корне проекта с вашей парольной фразой:
```
ваша-парольная-фраза
```

### Использование

#### Запуск прокси
Двойной клик по `start_proxy.bat` или выполните:
```bash
start_proxy.bat
```

**Процесс работы:**
1. Создаёт/активирует виртуальное окружение Python
2. Устанавливает необходимые пакеты (только при первом запуске)
3. Запускает монитор в трее в фоне
4. Показывает меню выбора хоста
5. Устанавливает SSH туннель и настраивает системный прокси

#### Остановка прокси
Двойной клик по `stop_proxy.bat` или выполните:
```bash
stop_proxy.bat
```

**Действия при очистке:**
- Завершает SSH туннель и HTTP сервер
- Удаляет настройки системного прокси
- Закрывает монитор в трее
- Удаляет временные файлы и ярлыки

#### Ручное управление через трей
- **Правый клик** по иконке в трее → "Quit Monitor" для остановки мониторинга
- **Левый клик** для просмотра статуса соединения
- Автоматическая попытка перезапуска при разрыве соединения

### Конфигурация

#### Настройка правил PAC
Отредактируйте `proxy_pac.back` для изменения правил прокси:
```javascript
function FindProxyForURL(url, host) {
    // Добавьте ваши пользовательские правила здесь
    if (shExpMatch(host, "*.example.com")) {
        return "DIRECT";
    }
    return "SOCKS5 127.0.0.1:${PORT}";
}
```

#### Настройка портов
Измените в `proxy_start_v25.py`:
```python
config.proxy_port = 1080       # Порт SOCKS5
config.pac_http_port = 8080    # Порт HTTP сервера PAC
```

#### Авто-выбор хоста
Добавьте суффикс `_PRIME` к имени хоста в SSH конфиге для авто-выбора:
```
Host my-server_PRIME
    HostName example.com
    User admin
```

### Устранение проблем

#### Частые проблемы

**1. "ssh.exe не найден"**
```powershell
# Включите OpenSSH Client
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH*'
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

**2. Таймауты соединения**
- Убедитесь, что SSH сервер доступен
- Проверьте правила фаервола для портов 22 (SSH) и 1080 (SOCKS5)
- Проверьте права на SSH ключ: `icacls keyfile /reset`

**3. Прокси не работает в браузере**
- Проверьте настройки системного прокси: `Win + R` → `inetcpl.cpl` → Подключения → Настройка LAN
- Проверьте PAC URL: `http://127.0.0.1:8080/proxy.pac`
- Протестируйте доступ к PAC файлу в браузере

**4. Иконка в трее не появляется**
- Проверьте, запущен ли `pythonw.exe` в Диспетчере задач
- Перезапустите скрипт от имени администратора
- Убедитесь, что антивирус не блокирует Python скрипты

#### Логи и отладка
- Проверьте вывод Python консоли при запуске
- Проверьте Просмотр событий Windows для изменений системного прокси
- Мониторинг с `netstat -ano | findstr :1080` для активных соединений

### Структура проекта
```
socks5-proxy-manager/
├── start_proxy.bat          # Скрипт запуска
├── stop_proxy.bat           # Скрипт очистки
├── proxy_start_v25.py       # Основная логика
├── proxy_stop.py            # Логика завершения
├── proxy_tray.pyw           # Монитор в трее
├── proxy_pac.back           # Шаблон PAC
├── key_pass                 # Файл с парольной фразой (опц.)
├── venv/                    # Виртуальное окружение
├── x_proxy_state.json       # Состояние runtime (авто)
├── x_ssh_tunnel.pid         # PID SSH (авто)
├── x_http_pac.pid           # PID HTTP (авто)
└── x_tray_monitor.pid       # PID трея (авто)
```

### Примечания по безопасности
- **Файл `key_pass`**: Хранит парольную фразу в открытом виде (используйте только на защищённых системах)
- **Фаервол**: Убедитесь, что только localhost может обращаться к портам прокси
- **SSH ключи**: Используйте сложные парольные фразы и аутентификацию по ключам
- **Очистка**: Всегда используйте `stop_proxy.bat` для удаления системных настроек
- **Права**: Запускайте с правами пользователя (не администратора)

---

## 📄 License / Лицензия
MIT License - see LICENSE file for details / MIT Лицензия - подробности в файле LICENSE.

## 🤝 Contributing / Участие в разработке
1. Fork the repository / Сделайте форк репозитория
2. Create a feature branch / Создайте ветку для функциональности
3. Commit changes / Зафиксируйте изменения
4. Push to the branch / Запушьте в ветку
5. Open a Pull Request / Откройте Pull Request

---

**⭐ If this project is useful to you, give it a star on GitHub! / ⭐ Если этот проект полезен для вас, поставьте звезду на GitHub!**