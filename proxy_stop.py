#!/usr/bin/env python3
"""
SOCKS5 Proxy Manager - Stop Proxy (SAFE VERSION)
Stop specific proxy processes by PID and reset system settings, including the tray monitor.
"""

import os
import subprocess
import time
import json
import sys
import shutil

try:
    import winreg
except ImportError:
    print("Required module winreg not available.")
    sys.exit(1)

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

def color(sym):
    if "✓" in sym: return GREEN + sym + RESET
    if "✗" in sym: return RED + sym + RESET
    if "⚠" in sym: return YELLOW + sym + RESET
    return sym

def kill_process(pid):
    """Kill process by PID."""
    try:
        # Using creationflags=0x08000000 (CREATE_NO_WINDOW) to hide the taskkill console
        subprocess.run(['taskkill', '/PID', str(pid), '/F'], 
                       capture_output=True, creationflags=0x08000000)
        return True
    except Exception:
        return False

def get_pid_from_file(filename):
    """Read PID from a file."""
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, 'r') as f:
            content = f.read().strip()
            # Handle JSON (for http server) or simple text (for ssh and tray)
            if content.startswith('{'):
                data = json.loads(content)
                return data.get('pid')
            return int(content)
    except Exception:
        return None

def kill_on_ports_fallback(ports):
    """Fallback: Kill processes on specific ports if PIDs are missing."""
    for port in ports:
        result = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, shell=True, errors='ignore')
        for line in result.stdout.splitlines():
            # Check for specific port and LISTENING state
            if f':{port}' in line and 'LISTENING' in line:
                try:
                    parts = line.strip().split()
                    pid = parts[-1]
                    if pid.isdigit():
                        print(color("⚠") + f" Fallback: Killing PID {pid} on port {port}")
                        kill_process(int(pid))
                except IndexError:
                    continue

def disable_system_proxy():
    """Disable system proxy and PAC settings (Windows registry)."""
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
            # Set ProxyEnable to 0 (Disabled)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            # Clear AutoConfigURL
            winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, "")
        print(color("✓") + " System proxy disabled (PAC removed)")
    except Exception as e:
        print(color("✗") + f" Failed to disable system proxy: {e}")

def cleanup_files():
    """Removes generated PID and state files."""
    # Added 'x_tray_monitor.pid' to the list
    files = ["proxy.pac", "x_proxy_state.json", "x_http_pac.pid", "x_ssh_tunnel.pid", "x_tray_monitor.pid"]
    for file in files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except Exception: pass
    print(color("✓") + " Temporary files cleaned")

def main():
    print("Stopping SOCKS5 Proxy...")

    # 1. Kill SSH Tunnel by PID
    ssh_pid = get_pid_from_file("x_ssh_tunnel.pid")
    if ssh_pid:
        kill_process(ssh_pid)
        print(color("✓") + f" SSH Tunnel stopped (PID {ssh_pid})")
    else:
        print(color("⚠") + " SSH PID file not found, checking port 1080...")
        kill_on_ports_fallback([1080])

    # 2. Kill HTTP Server by PID
    http_pid = get_pid_from_file("x_http_pac.pid")
    if http_pid:
        kill_process(http_pid)
        print(color("✓") + f" HTTP Server stopped (PID {http_pid})")
    else:
        print(color("⚠") + " HTTP PID file not found, checking port 8080...")
        kill_on_ports_fallback([8080])

    # 3. Disable Registry
    disable_system_proxy()
    
    # 4. Kill Tray Monitor by PID
    tray_pid = get_pid_from_file("x_tray_monitor.pid")
    if tray_pid:
        kill_process(tray_pid)
        print(color("✓") + f" Tray Monitor stopped (PID {tray_pid})")
    else:
        print(color("⚠") + " Tray Monitor PID file not found. It may have already closed.")

    # 5. Cleanup Files
    cleanup_files()
    
    print("\n" + "=" * 50)
    print(color("✓") + " Proxy stopped and cleaned.")
    print("=" * 50)

if __name__ == "__main__":
    main()