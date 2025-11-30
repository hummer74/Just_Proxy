import os
import subprocess
import msvcrt
import re
import json
import time
import shutil
import sys
import threading

# ============ DECORATION COLORS ============
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

def color(sym):
    if "✓" in sym:
        return GREEN + sym + RESET
    if "✗" in sym:
        return RED + sym + RESET
    if "⚠" in sym:
        return YELLOW + sym + RESET
    return sym
# ==========================================

SSH_CONFIG_PATH = r"config.ini"
SSH_PATH = "ssh.exe"  # Windows 10 built-in OpenSSH
PROXY_PORT = 1080
STATE_FILE = "proxy_state.json"
PAC_HTTP_PID_FILE = "pac_http_server.json"
PAC_HTTP_PORT = 8088

# ==================== PARSING SSH CONFIG ====================
def parse_ssh_config(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        hosts = []
        current_host = {}
        skip_block = False
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#START_HEAD'):
                skip_block = True
                i += 1
                continue
            if line.startswith('#END_HEAD'):
                skip_block = False
                i += 1
                continue
            if skip_block:
                i += 1
                continue
            if line.startswith('Host '):
                if current_host:
                    hosts.append(current_host)
                current_host = {'name': line[5:].strip()}
                i += 1
                continue
            if line and not line.startswith('#') and current_host:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0]
                    value = ' '.join(parts[1:])
                    current_host[key] = value.strip()
            i += 1
        if current_host:
            hosts.append(current_host)
        return [h for h in hosts if 'name' in h and h['name'] != '*']
    except Exception as e:
        print(color("✗") + f" Error reading SSH config: {e}")
        return []

# ==================== SAVE STATE ====================
def save_proxy_state(host_info, key_path, has_password):
    state = {
        'host': host_info['name'],
        'proxy_port': PROXY_PORT,
        'key_path': key_path,
        'has_password': has_password,
        'ssh_command': build_ssh_command(host_info, key_path)
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

# ==================== PAC FILE ====================
def generate_pac_file(pac_path, port):
    pac_content = f'''
function FindProxyForURL(url, host) {{

    if (isPlainHostName(host) ||
        shExpMatch(host, "127.*") ||
        shExpMatch(host, "10.*") ||
        shExpMatch(host, "192.168.*")) {{
        return "DIRECT";
    }}

    if (shExpMatch(host, "*.ru") || shExpMatch(host, "*.RU") ||
        shExpMatch(host, "*yandex*") || shExpMatch(host, "*YANDEX*")) {{
        return "DIRECT";
    }}

    return "SOCKS5 127.0.0.1:{port}";
}}
'''.strip()

    with open(pac_path, "w", encoding="utf-8") as f:
        f.write(pac_content)

# ==================== SYSTEM PROXY ====================
def set_system_proxy_with_pac_http(pac_url):
    try:
        ps_script = f'''
$regPath = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings"
Set-ItemProperty -Path $regPath -Name "AutoConfigURL" -Value "{pac_url}"
Set-ItemProperty -Path $regPath -Name "ProxyEnable" -Value 0
'''
        subprocess.run(['powershell', '-Command', ps_script],
                       capture_output=True, text=True, check=True)
        print(color("✓") + f" PAC proxy enabled via HTTP: {pac_url}")
        tray_notify("SOCKS5 Proxy", f"PAC proxy enabled via HTTP")
        return True
    except Exception as e:
        print(color("✗") + f" Failed to enable PAC: {e}")
        return False

# ==================== LOCAL HTTP SERVER ====================
def start_local_http_server(pac_path):
    try:
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        cmd = [
            pythonw, "-m", "http.server", str(PAC_HTTP_PORT),
            "--bind", "127.0.0.1"
        ]
        DETACHED = 0x00000008
        NO_WINDOW = 0x08000000
        proc = subprocess.Popen(
            cmd,
            cwd=os.getcwd(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=DETACHED | NO_WINDOW
        )
        with open(PAC_HTTP_PID_FILE, "w", encoding="utf-8") as f:
            json.dump({"pid": proc.pid}, f)
        time.sleep(1)
        print(color("✓") + f" Local HTTP server started on 127.0.0.1:{PAC_HTTP_PORT} (PID {proc.pid})")
        return proc.pid
    except Exception as e:
        print(color("✗") + f" Failed to start local HTTP server: {e}")
        return None

# ==================== BUILD SSH COMMAND ====================
def build_ssh_command(host_info, key_path):
    cmd = [SSH_PATH, '-D', f'127.0.0.1:{PROXY_PORT}', '-N', '-T']
    if key_path and os.path.exists(key_path):
        cmd.extend(['-i', key_path])
    if 'Port' in host_info:
        cmd.extend(['-p', host_info['Port']])
    if 'User' in host_info:
        cmd.extend(['-l', host_info['User']])
    if 'IdentitiesOnly' in host_info and host_info['IdentitiesOnly'].lower() == 'yes':
        cmd.append('-oIdentitiesOnly=yes')
    if 'ServerAliveInterval' in host_info:
        cmd.extend(['-oServerAliveInterval=' + host_info['ServerAliveInterval']])
    cmd.append(host_info['HostName'])
    return cmd

# ==================== START SSH TUNNEL ====================
def start_ssh_tunnel(host_info, key_path):
    cmd = build_ssh_command(host_info, key_path)
    print("\033[1;33m" + f"\n Starting SSH tunnel to {host_info['name']}...\n" + "\033[0m")
    NO_WINDOW = 0x08000000
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            creationflags=NO_WINDOW
        )
        time.sleep(1.5)
        if proc.poll() is None:
            print(color("✓") + " SSH tunnel started (hidden mode)")
            tray_notify("SOCKS5 Proxy", f"Tunnel to {host_info['name']} is ACTIVE")
            return proc
        else:
            err = proc.stderr.read().strip().decode(errors="ignore")
            print(color("✗") + f" SSH tunnel failed: {err}")
            return None
    except FileNotFoundError:
        print(color("✗") + " ssh.exe not found! Install OpenSSH Client.")
        return None
    except Exception as e:
        print(color("✗") + f" Failed to start SSH tunnel: {e}")
        return None

# ==================== SELECT HOST MENU ====================
def select_host_menu(hosts, auto_select_tag="_PRIME", timeout=5):
    if not hosts:
        print(color("✗") + " No hosts found in SSH config!")
        return None
    selected = 0
    start_time = time.time()
    prime_index = next((i for i, h in enumerate(hosts) if auto_select_tag in h['name']), None)
    def draw_menu():
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Select SSH host (↑↓ Arrow keys, Enter to select, Q to quit):")
        print("=" * 60)
        for i, host in enumerate(hosts):
            marker = "►" if i == selected else "  "
            hostname = host.get('HostName', 'N/A')
            port = host.get('Port', '22')
            user = host.get('User', 'root')
            keyfile = host.get('IdentityFile', 'N/A')
            status_icon = color("✓") if os.path.exists(keyfile) else color("✗")
            print(f"{marker} {host['name']} -> {user}@{hostname}:{port} [{status_icon} {os.path.basename(keyfile)}]")
        print("=" * 60)
        print(f"↑↓: Navigate | Enter: Select | Q: Quit | Auto-select in {max(0, int(timeout - (time.time()-start_time)))}s")
    draw_menu()
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            moved = False
            if key == b'\xe0':
                arrow_key = msvcrt.getch()
                if arrow_key == b'H':
                    selected = max(0, selected - 1)
                    moved = True
                elif arrow_key == b'P':
                    selected = min(len(hosts) - 1, selected + 1)
                    moved = True
            elif key == b'\r':
                return hosts[selected]
            elif key.lower() == b'q' or key.lower() == b'\x1b':
                return None
            if moved:
                draw_menu()
                start_time = time.time()
        else:
            if prime_index is not None and (time.time() - start_time) >= timeout:
                print(color("⚠") + f" No input detected. Auto-selecting host: {hosts[prime_index]['name']}")
                return hosts[prime_index]
        time.sleep(0.05)

# ==================== SSH-AGENT ====================
def ensure_ssh_agent(key_path):
    passfile = os.path.join(os.getcwd(), "key_pass.txt")
    passphrase = None
    if os.path.exists(passfile):
        try:
            with open(passfile, "r", encoding="utf-8") as f:
                passphrase = f.read().strip()
        except Exception as e:
            print(color("✗") + f" Failed to read key_pass.txt: {e}")
    try:
        result = subprocess.run(["ssh-agent", "-s"], capture_output=True, text=True)
        output = result.stdout
        sock_match = re.search(r'SSH_AUTH_SOCK=([^;]+);', output)
        if not sock_match:
            print(color("✗") + " Could not detect SSH_AUTH_SOCK")
            return
        os.environ["SSH_AUTH_SOCK"] = sock_match.group(1)
        if passphrase:
            proc = subprocess.Popen(
                ["ssh-add", key_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            out, err = proc.communicate(passphrase + "\n")
            if proc.returncode == 0:
                print(color("✓") + " Key loaded into ssh-agent (via key_pass.txt)")
            else:
                print(color("✗") + " ssh-add error: " + err.strip())
        else:
            add = subprocess.run(["ssh-add", key_path], text=True, capture_output=True)
            if add.returncode == 0:
                print(color("✓") + " Key loaded into ssh-agent")
            else:
                print(color("✗") + " ssh-add error: " + add.stderr.strip())
    except Exception as e:
        print(color("✗") + f" Failed to run ssh-agent: {e}")

# ==================== ERROR HANDLER ====================
def handle_error(msg):
    print(color("✗") + " " + msg)
    stop_script = os.path.join(os.getcwd(), "stop_proxy.bat")
    if os.path.exists(stop_script):
        try:
            subprocess.run([stop_script], check=True)
            print(color("✓") + " Proxy state restored via stop_proxy.bat")
        except Exception as e:
            print(color("⚠") + f" Failed to run stop_proxy.bat: {e}")
    else:
        print(color("⚠") + " stop_proxy.bat not found!")
    input("\nPress Enter to exit...")
    sys.exit(1)

# ==================== SYSTEM TRAY NOTIFICATIONS ====================
def tray_notify(title, message):
    ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$template.GetElementsByTagName("text")[0].AppendChild($template.CreateTextNode("{title}")) > $null
$template.GetElementsByTagName("text")[1].AppendChild($template.CreateTextNode("{message}")) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("SOCKS5 Proxy").Show($toast)
'''
    subprocess.run(["powershell", "-Command", ps_script], capture_output=True)

# ==================== MONITOR SSH TUNNEL ====================
def monitor_ssh_tunnel(host_info, key_path, check_interval=5):
    tunnel_proc = start_ssh_tunnel(host_info, key_path)
    if not tunnel_proc:
        handle_error("Failed to start SSH tunnel initially.")
    try:
        while True:
            time.sleep(check_interval)
            if tunnel_proc.poll() is not None:
                print(color("⚠") + " SSH tunnel lost. Restarting...")
                tray_notify("SOCKS5 Proxy", f"Tunnel lost. Restarting...")
                tunnel_proc = start_ssh_tunnel(host_info, key_path)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    except Exception as e:
        print(color("✗") + f"Tunnel monitoring failed: {e}")
        stop_script = os.path.join(os.getcwd(), "stop_proxy.bat")
        if os.path.exists(stop_script):
            subprocess.run([stop_script], check=False)
        sys.exit(1)

# ==================== MAIN ====================
def main():
    print("SOCKS5 System Proxy Creator (OpenSSH)")
    print("=" * 50)

    if not os.path.exists(SSH_PATH) and not shutil.which(SSH_PATH):
        handle_error("OpenSSH not found!")

    hosts = parse_ssh_config(SSH_CONFIG_PATH)
    if not hosts:
        handle_error(f"No hosts found in {SSH_CONFIG_PATH}")

    print(color("✓") + f" Found {len(hosts)} hosts")

    selected_host = select_host_menu(hosts)
    if not selected_host:
        handle_error("No host selected.")

    key_path = selected_host.get('IdentityFile', '')
    if not key_path or not os.path.exists(key_path):
        handle_error(f"Key file not found: {key_path}")

    print(f"\n{color('✓')} Selected: {selected_host['name']}")
    print(f"  Host: {selected_host.get('HostName', 'N/A')}")
    print(f"  User: {selected_host.get('User', 'root')}")
    print(f"  Port: {selected_host.get('Port', '22')}")
    print(f"  Key:  {key_path}")

    try:
        save_proxy_state(selected_host, key_path, False)
    except Exception as e:
        handle_error(f"Failed to save proxy state: {e}")

    try:
        ensure_ssh_agent(key_path)
    except Exception as e:
        handle_error(f"Failed to load SSH key: {e}")

    pac_path = os.path.join(os.getcwd(), "proxy.pac")
    try:
        generate_pac_file(pac_path, PROXY_PORT)
    except Exception as e:
        handle_error(f"Failed to generate PAC file: {e}")

    try:
        start_local_http_server(pac_path)
    except Exception as e:
        handle_error(f"Failed to start local HTTP server: {e}")

    pac_http_url = f"http://127.0.0.1:{PAC_HTTP_PORT}/proxy.pac"
    if not set_system_proxy_with_pac_http(pac_http_url):
        handle_error("Failed to configure system PAC proxy.")

    # Запускаем мониторинг SSH-туннеля в отдельном потоке
    threading.Thread(target=monitor_ssh_tunnel, args=(selected_host, key_path), daemon=True).start()

    print(f"\n{'='*50}")
    print(color("✓") + f" SOCKS5 proxy ACTIVE: 127.0.0.1:{PROXY_PORT}")
    print(color("✓") + f" System proxy CONFIGURED (PAC via HTTP)")
    print(color("✓") + f" Tunnel to: {selected_host['name']}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
