#!/usr/bin/env python3
"""
SOCKS5 Proxy Manager - Stop Proxy (Optimized)
Stop all proxy-related background processes and reset system proxy.
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
    if "✓" in sym:
        return GREEN + sym + RESET
    if "✗" in sym:
        return RED + sym + RESET
    if "⚠" in sym:
        return YELLOW + sym + RESET
    return sym

def kill_process(name_or_pid):
    """Kill process by name or PID."""
    try:
        if isinstance(name_or_pid, int) or name_or_pid.isdigit():
            subprocess.run(['taskkill', '/PID', str(name_or_pid), '/F'], capture_output=True, shell=True)
        else:
            subprocess.run(['taskkill', '/F', '/IM', name_or_pid], capture_output=True, shell=True)
    except Exception:
        pass

def kill_on_ports(ports):
    """Find and kill all processes listening on given ports."""
    for port in ports:
        result = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, shell=True)
        for line in result.stdout.splitlines():
            line = line.strip()
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    kill_process(pid)
                    print(f"Killed process PID {pid} on port {port}")
        time.sleep(2)
    # Kill pythonw.exe (PAC http server), ssh.exe if still alive
    kill_process('pythonw.exe')
    kill_process('ssh.exe')

def stop_http_server():
    server_file = "pac_http_server.json"
    if os.path.exists(server_file):
        try:
            with open(server_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            pid = data.get("pid")
            if pid:
                print(f"Stopping HTTP PAC server (PID: {pid})...")
                kill_process(pid)
            os.remove(server_file)
            print(color("✓") + " HTTP server process stopped")
        except Exception as e:
            print(color("✗") + f" Failed to stop HTTP server: {e}")
    else:
        print(color("⚠") + " No HTTP server PID file found.")

def disable_system_proxy():
    """Disable system proxy and PAC settings (Windows registry)."""
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, "")
        print(color("✓") + " System proxy disabled (PAC removed)")
    except Exception as e:
        print(color("✗") + f" Failed to disable system proxy: {e}")

def cleanup_ssh_agent_files():
    agent_dir = os.path.expanduser(r"~\.ssh\agent")
    if os.path.exists(agent_dir):
        try:
            shutil.rmtree(agent_dir)
            print(color("✓") + f" SSH agent directory cleaned: {agent_dir}")
        except Exception as e:
            print(color("⚠") + f" Failed to remove SSH agent dir: {e}")
    else:
        print(color("⚠") + " No SSH agent temp directory found.")

def main():
    print("SOCKS5 Proxy Manager - Stop Proxy (Optimized)")
    print("=" * 50)
    print("Stopping all background processes and removing proxy settings...")

    kill_on_ports([1080, 1081, 1082, 1083, 1084])
    stop_http_server()
    disable_system_proxy()
    cleanup_ssh_agent_files()

    print("\n" + "=" * 50)
    print(color("✓") + " All proxy processes stopped, system settings reset, agent files cleaned.")
    print("=" * 50)

if __name__ == "__main__":
    main()
