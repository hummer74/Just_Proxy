#!/usr/bin/env python3
"""
SOCKS5 Proxy Manager - Stop Proxy
Stops SSH tunnel, HTTP PAC server, and restores original system proxy settings.
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

class ProxyStopper:
    """Stop proxy, PAC server, and restore system settings."""

    def __init__(self):
        self.registry_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        self.backup_file = "proxy_settings.json"
        self.http_server_file = "pac_http_server.json"

    def kill_ssh_processes(self):
        """Kill SSH and plink processes."""
        try:
            print("Stopping SSH tunnel processes...")
            subprocess.run(['taskkill', '/F', '/IM', 'plink.exe'], capture_output=True, text=True, shell=True)
            subprocess.run(['taskkill', '/F', '/IM', 'ssh.exe'], capture_output=True, text=True, shell=True)
            time.sleep(1)
            return True
        except Exception as e:
            print(color("✗") + f" Error killing SSH processes: {e}")
            return False

    def kill_processes_on_ports(self, ports):
        """Kill processes listening on specified ports."""
        try:
            for port in ports:
                print(f"Looking for processes using port {port}...")
                result = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, shell=True)
                pids_found = []
                for line in result.stdout.splitlines():
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            if pid not in pids_found:
                                pids_found.append(pid)
                for pid in pids_found:
                    subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True, shell=True, timeout=10)
            return True
        except Exception as e:
            print(color("✗") + f" Error finding/killing processes on ports: {e}")
            return False

    def stop_http_server(self):
        """Stop the local PAC HTTP server."""
        if not os.path.exists(self.http_server_file):
            print(color("⚠") + " No HTTP server PID file found.")
            return False
        try:
            with open(self.http_server_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            pid = data.get("pid")
            if pid:
                print(f"Stopping local HTTP server (PID: {pid})...")
                subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True, shell=True)
            os.remove(self.http_server_file)
            return True
        except Exception as e:
            print(color("✗") + f" Failed to stop HTTP server: {e}")
            return False

    def restore_proxy_settings(self):
        """Restore original proxy settings from backup JSON."""
        try:
            if os.path.exists(self.backup_file):
                with open(self.backup_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                proxy_enable = settings.get("ProxyEnable", 0)
                proxy_server = settings.get("ProxyServer", "")
                auto_config_url = settings.get("AutoConfigURL", "")

                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_WRITE) as key:
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, proxy_enable)
                    winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
                    winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, auto_config_url)

                os.remove(self.backup_file)
                print(color("✓") + " System proxy settings restored from backup")
                return True
            else:
                print("Disabling proxy and PAC")
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_WRITE) as key:
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                    winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, "")
                return True
        except Exception as e:
            print(color("✗") + f" Error restoring proxy settings: {e}")
            return False

    def disable_pac_proxy(self):
        """Rewrite existing PAC file to force all connections DIRECT."""
        pac_path = os.path.join(os.getcwd(), "proxy.pac")
        if not os.path.exists(pac_path):
            print(color("⚠") + " No PAC file found to rewrite.")
            return False
        try:
            with open(pac_path, "w", encoding="utf-8") as f:
                f.write('function FindProxyForURL(url, host) { return "DIRECT"; }')
            print(color("✓") + f" PAC file rewritten to DIRECT: {pac_path}")
            return True
        except Exception as e:
            print(color("✗") + f" Failed to rewrite PAC: {e}")
            return False

    def cleanup_ssh_agent_files(self):
        """Remove temporary SSH agent files."""
        agent_dir = r"C:\Users\Dan\.ssh\agent"
        if os.path.exists(agent_dir):
            try:
                shutil.rmtree(agent_dir)
                print(color("✓") + f" SSH agent temporary files removed: {agent_dir}")
                return True
            except Exception as e:
                print(color("✗") + f" Failed to remove SSH agent files: {e}")
                return False
        else:
            print(color("⚠") + f"No SSH agent folder found at {agent_dir}")
            return False

def main():
    print("SOCKS5 Proxy Manager - Stop Proxy")
    print("=" * 50)

    stopper = ProxyStopper()

    # Kill SSH processes
    stopper.kill_ssh_processes()

    # Kill processes on common SOCKS5 ports
    stopper.kill_processes_on_ports([1080, 1081, 1082, 1083, 1084])

    # Stop local HTTP PAC server
    stopper.stop_http_server()

    # Restore system proxy settings
    stopper.restore_proxy_settings()

    # Disable PAC
    stopper.disable_pac_proxy()

    # Cleanup SSH agent temporary files
    stopper.cleanup_ssh_agent_files()

    print("\n" + "=" * 50)
    print(color("✓") + " Proxy successfully stopped, HTTP server terminated, system settings restored, and SSH agent files cleaned up")
    print("=" * 50)

if __name__ == "__main__":
    main()
