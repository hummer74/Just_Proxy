"""
SOCKS5 System Proxy Creator with SSH Tunneling
OPTIMIZED VERSION - Automatic passphrase, PAC from template, no windows, daemon mode
"""

import os
import os.path
import subprocess
import msvcrt
import re
import json
import time
import shutil
import sys
import threading
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
import logging

# ============ LOGGING SETUP ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ DECORATION COLORS ============
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def color(sym: str) -> str:
    """Apply color formatting to symbols."""
    if "✓" in sym:
        return GREEN + sym + RESET
    if "✗" in sym:
        return RED + sym + RESET
    if "⚠" in sym:
        return YELLOW + sym + RESET
    return sym


# ============ CONFIGURATION ============
@dataclass
class Config:
    """Configuration class for application settings."""
    ssh_config_path: str = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), '.ssh/config')
    ssh_path: str = "ssh.exe"
    proxy_port: int = 1080
    state_file: str = "proxy_state.json"
    pac_http_pid_file: str = "pac_http_server.json"
    pac_http_port: int = 8088
    work_dir: str = os.getcwd()
    key_pass_file: str = os.path.join(os.getcwd(), "key_pass")
    pac_template_file: str = os.path.join(os.getcwd(), "proxy_back.pac")
    ssh_agent_dir: str = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), '.ssh/agent')
    
    def validate(self) -> bool:
        """Validate configuration."""
        if not 1024 <= self.proxy_port <= 65535:
            logger.error(f"Invalid proxy port: {self.proxy_port}")
            return False
        if not 1024 <= self.pac_http_port <= 65535:
            logger.error(f"Invalid PAC HTTP port: {self.pac_http_port}")
            return False
        return True


config = Config()


# ==================== PASSPHRASE MANAGEMENT ====================
def load_passphrase_from_file() -> Optional[str]:
    """
    Load SSH key passphrase from key_pass file.
    
    Returns:
        Passphrase string or None if not found
    """
    try:
        if not os.path.exists(config.key_pass_file):
            logger.warning(f"Passphrase file not found: {config.key_pass_file}")
            return None
        
        with open(config.key_pass_file, 'r', encoding='utf-8') as f:
            passphrase = f.read().strip()
        
        if not passphrase:
            logger.warning("Passphrase file is empty")
            return None
        
        logger.info("Passphrase loaded from file")
        return passphrase
    
    except Exception as e:
        logger.error(f"Failed to load passphrase: {e}")
        return None


# ==================== SSH AGENT DIRECTORY ====================
def ensure_ssh_agent_dir() -> bool:
    """
    Create SSH agent directory if it doesn't exist.
    
    Returns:
        True if directory exists or was created
    """
    try:
        os.makedirs(config.ssh_agent_dir, exist_ok=True)
        logger.info(f"SSH agent directory ready: {config.ssh_agent_dir}")
        return True
    except Exception as e:
        logger.error(f"Failed to create SSH agent directory: {e}")
        return False


# ==================== VALIDATE SSH KEY ====================
def validate_key_file(key_path: str) -> Optional[str]:
    """
    Validate and normalize SSH key file path.
    
    Args:
        key_path: Path to SSH key (may contain ~)
        
    Returns:
        Expanded key path if valid, None otherwise
    """
    try:
        if not key_path:
            logger.error("Key path is empty")
            return None
        
        expanded_path = os.path.expanduser(key_path)
        
        if not os.path.exists(expanded_path):
            logger.error(f"SSH key not found: {key_path} (expanded: {expanded_path})")
            return None
        
        if not os.path.isfile(expanded_path):
            logger.error(f"SSH key is not a file: {expanded_path}")
            return None
        
        if not os.access(expanded_path, os.R_OK):
            logger.error(f"SSH key not readable: {expanded_path}")
            return None
        
        logger.info(f"SSH key validated: {expanded_path}")
        return expanded_path
    
    except Exception as e:
        logger.error(f"Error validating SSH key: {e}")
        return None


# ==================== PARSING SSH CONFIG ====================
def parse_ssh_config(config_path: str) -> List[Dict[str, str]]:
    """
    Parse SSH config file and extract host information.
    
    Args:
        config_path: Path to SSH config file
        
    Returns:
        List of host dictionaries
    """
    try:
        if not os.path.exists(config_path):
            logger.error(f"SSH config not found: {config_path}")
            return []
        
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        
        hosts = []
        current_host = {}
        skip_block = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('#START_HEAD'):
                skip_block = True
                continue
            if line.startswith('#END_HEAD'):
                skip_block = False
                continue
            
            if skip_block or line.startswith('#') or not line:
                continue
            
            if line.startswith('Host '):
                if current_host and 'name' in current_host:
                    hosts.append(current_host)
                current_host = {'name': line[5:].strip()}
            elif current_host:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    key, value = parts
                    if key == 'IdentityFile':
                        value = os.path.expanduser(value.strip())
                    else:
                        value = value.strip()
                    current_host[key] = value
        
        if current_host and 'name' in current_host:
            hosts.append(current_host)
        
        hosts = [h for h in hosts if h['name'] != '*']
        
        logger.info(f"Parsed {len(hosts)} hosts from SSH config")
        return hosts
        
    except Exception as e:
        logger.error(f"Error reading SSH config: {e}")
        return []


# ==================== SAVE STATE ====================
def save_proxy_state(host_info: Dict, key_path: str, has_password: bool) -> bool:
    """
    Save proxy state to file.
    
    Args:
        host_info: Host information dictionary
        key_path: Path to SSH key
        has_password: Whether key has password protection
        
    Returns:
        True if successful
    """
    try:
        state = {
            'host': host_info.get('name'),
            'proxy_port': config.proxy_port,
            'key_path': key_path,
            'has_password': has_password,
            'ssh_command': build_ssh_command(host_info, key_path)
        }
        
        with open(config.state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Proxy state saved to {config.state_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save proxy state: {e}")
        return False


# ==================== PAC FILE FROM TEMPLATE ====================
def generate_pac_file_from_template(pac_path: str, port: int) -> bool:
    """
    Generate PAC file from proxy_back.pac template.
    
    Args:
        pac_path: Path where PAC file will be saved
        port: SOCKS5 proxy port
        
    Returns:
        True if successful
    """
    try:
        if not 1024 <= port <= 65535:
            logger.error(f"Invalid port for PAC: {port}")
            return False
        
        # Try to load template
        if os.path.exists(config.pac_template_file):
            try:
                with open(config.pac_template_file, 'r', encoding='utf-8') as f:
                    pac_content = f.read()
                
                # Replace port placeholder in template if it exists
                pac_content = pac_content.replace('__PORT__', str(port))
                pac_content = pac_content.replace('${PORT}', str(port))
                pac_content = pac_content.replace(':1080', f':{port}')
                
                logger.info(f"Loaded PAC template from {config.pac_template_file}")
            except Exception as e:
                logger.warning(f"Failed to load PAC template, using default: {e}")
                pac_content = generate_default_pac(port)
        else:
            logger.info(f"PAC template not found, using default PAC")
            pac_content = generate_default_pac(port)
        
        with open(pac_path, "w", encoding="utf-8") as f:
            f.write(pac_content)
        
        logger.info(f"PAC file generated: {pac_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to generate PAC file: {e}")
        return False


def generate_default_pac(port: int) -> str:
    """
    Generate default PAC content.
    
    Args:
        port: SOCKS5 proxy port
        
    Returns:
        PAC file content
    """
    return f'''function FindProxyForURL(url, host) {{
    // Local networks - no proxy
    if (isPlainHostName(host) ||
        shExpMatch(host, "127.*") ||
        shExpMatch(host, "10.*") ||
        shExpMatch(host, "192.168.*")) {{
        return "DIRECT";
    }}
    
    // Russian domains and services - no proxy
    if (shExpMatch(host, "*.local") || shExpMatch(host, "*.LOCAL") ||
        shExpMatch(host, "*.ru") || shExpMatch(host, "*.RU") ||
        shExpMatch(host, "*.рф") || shExpMatch(host, "*.РФ") ||
        shExpMatch(host, "vk.*") || shExpMatch(host, "VK.*") ||
        shExpMatch(host, "*yandex*") || shExpMatch(host, "*YANDEX*") ||
        shExpMatch(host, "deepseek.*") || shExpMatch(host, "DEEPSEEK.*")) {{
        return "DIRECT";
    }}
    
    // All other traffic through SOCKS5 proxy
    return "SOCKS5 127.0.0.1:{port}";
}}'''


# ==================== SYSTEM PROXY ====================
def set_system_proxy_with_pac_http(pac_url: str) -> bool:
    """
    Set system proxy using PAC URL.
    
    Args:
        pac_url: URL to PAC file
        
    Returns:
        True if successful
    """
    try:
        ps_script = f'''
$regPath = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings"
Set-ItemProperty -Path $regPath -Name "AutoConfigURL" -Value "{pac_url}"
Set-ItemProperty -Path $regPath -Name "ProxyEnable" -Value 0
Get-Item -Path $regPath | Select-Object AutoConfigURL
'''
        
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(color("✓") + f" PAC proxy enabled: {pac_url}")
            logger.info(f"System proxy configured with PAC: {pac_url}")
            return True
        else:
            logger.error(f"PowerShell error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("PowerShell command timeout")
        return False
    except Exception as e:
        logger.error(f"Failed to enable PAC proxy: {e}")
        return False


# ==================== LOCAL HTTP SERVER ====================
def start_local_http_server(pac_path: str) -> Optional[int]:
    """
    Start local HTTP server for PAC file in background.
    
    Args:
        pac_path: Path to PAC file
        
    Returns:
        Process ID if successful, None otherwise
    """
    try:
        if not os.path.exists(pac_path):
            logger.error(f"PAC file not found: {pac_path}")
            return None
        
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        
        if not shutil.which(pythonw) and not os.path.exists(pythonw):
            pythonw = sys.executable
        
        cmd = [
            pythonw,
            "-m", "http.server",
            str(config.pac_http_port),
            "--bind", "127.0.0.1",
            "--directory", config.work_dir
        ]
        
        DETACHED = 0x00000008
        NO_WINDOW = 0x08000000
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=DETACHED | NO_WINDOW
        )
        
        try:
            with open(config.pac_http_pid_file, "w", encoding="utf-8") as f:
                json.dump({"pid": proc.pid, "port": config.pac_http_port}, f)
        except Exception as e:
            logger.warning(f"Failed to save PAC HTTP PID: {e}")
        
        time.sleep(1)
        
        print(color("✓") + f" Local HTTP server started on 127.0.0.1:{config.pac_http_port} (PID {proc.pid})")
        logger.info(f"HTTP server started with PID {proc.pid}")
        return proc.pid
        
    except Exception as e:
        logger.error(f"Failed to start local HTTP server: {e}")
        return None


# ==================== BUILD SSH COMMAND ====================
def build_ssh_command(host_info: Dict[str, str], key_path: str) -> List[str]:
    """
    Build SSH tunnel command.
    
    Args:
        host_info: Host information dictionary
        key_path: Path to SSH key
        
    Returns:
        List of command arguments
    """
    cmd = [
        config.ssh_path,
        '-D', f'127.0.0.1:{config.proxy_port}',
        '-N',
        '-T',
        '-o', 'ConnectTimeout=10',
        '-o', 'ServerAliveInterval=60',
        '-o', 'ServerAliveCountMax=3'
    ]
    
    if key_path and os.path.exists(key_path):
        cmd.extend(['-i', key_path])
    
    if 'Port' in host_info:
        try:
            port = int(host_info['Port'])
            if 1 <= port <= 65535:
                cmd.extend(['-p', str(port)])
        except ValueError:
            logger.warning(f"Invalid port in SSH config: {host_info['Port']}")
    
    if 'User' in host_info:
        cmd.extend(['-l', host_info['User']])
    
    if host_info.get('IdentitiesOnly', '').lower() == 'yes':
        cmd.append('-oIdentitiesOnly=yes')
    
    if 'HostName' in host_info:
        cmd.append(host_info['HostName'])
    else:
        cmd.append(host_info.get('name', ''))
    
    return cmd


# ==================== START SSH TUNNEL ====================
def start_ssh_tunnel(host_info: Dict[str, str], key_path: str, passphrase: Optional[str] = None) -> Optional[subprocess.Popen]:
    """
    Start SSH tunnel process.
    
    Args:
        host_info: Host information dictionary
        key_path: Path to SSH key
        passphrase: Optional passphrase for key
        
    Returns:
        Process object if successful, None otherwise
    """
    cmd = build_ssh_command(host_info, key_path)
    
    print("\033[1;33m" + f"\nStarting SSH tunnel to {host_info.get('name', 'unknown')}...\n" + "\033[0m")
    
    NO_WINDOW = 0x08000000
    
    try:
        if passphrase:
            # Use passphrase if provided
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                creationflags=NO_WINDOW
            )
            
            try:
                # Send passphrase to stdin
                proc.communicate(input=passphrase + "\n", timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Passphrase input timeout, continuing...")
        else:
            # Start without passphrase (will prompt if needed)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                creationflags=NO_WINDOW
            )
        
        # Give SSH time to establish connection
        time.sleep(1.5)
        
        if proc.poll() is None:
            print(color("✓") + " SSH tunnel started (hidden mode)")
            logger.info(f"SSH tunnel established to {host_info.get('name')}")
            return proc
        else:
            err = proc.stderr.read().strip().decode(errors="ignore") if proc.stderr else "Unknown error"
            logger.error(f"SSH tunnel failed: {err}")
            print(color("✗") + f" SSH tunnel failed: {err}")
            return None
    
    except FileNotFoundError:
        logger.error("ssh.exe not found")
        print(color("✗") + " ssh.exe not found! Install OpenSSH Client.")
        return None
    except Exception as e:
        logger.error(f"Failed to start SSH tunnel: {e}")
        print(color("✗") + f" Failed to start SSH tunnel: {e}")
        return None


# ==================== SELECT HOST MENU ====================
def select_host_menu(hosts: List[Dict], auto_select_tag: str = "_PRIME", timeout: int = 30) -> Optional[Dict]:
    """
    Display interactive host selection menu.
    
    Args:
        hosts: List of available hosts
        auto_select_tag: Tag for automatic selection
        timeout: Timeout for automatic selection in seconds
        
    Returns:
        Selected host dictionary or None
    """
    if not hosts:
        logger.error("No hosts available for selection")
        print(color("✗") + " No hosts found in SSH config!")
        return None
    
    selected = 0
    start_time = time.time()
    prime_index = next((i for i, h in enumerate(hosts) if auto_select_tag in h.get('name', '')), None)
    
    def draw_menu():
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Select SSH host (↑↓ Arrow keys, Enter to select, Q to quit):")
        print("=" * 70)
        
        for i, host in enumerate(hosts):
            marker = "►" if i == selected else " "
            hostname = host.get('HostName', 'N/A')
            port = host.get('Port', '22')
            user = host.get('User', 'root')
            keyfile = host.get('IdentityFile', 'N/A')
            status_icon = color("✓") if os.path.exists(keyfile) else color("✗")
            
            print(f"{marker} {host['name']} -> {user}@{hostname}:{port} [{status_icon} {os.path.basename(keyfile)}]")
        
        print("=" * 70)
        remaining = max(0, int(timeout - (time.time() - start_time)))
        print(f"↑↓: Navigate | Enter: Select | Q: Quit | Auto-select in {remaining}s")
    
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
            
            elif key.lower() in (b'q', b'\x1b'):
                logger.info("User cancelled host selection")
                return None
            
            if moved:
                draw_menu()
                start_time = time.time()
        
        else:
            if prime_index is not None and (time.time() - start_time) >= timeout:
                print(color("⚠") + f" No input detected. Auto-selecting: {hosts[prime_index]['name']}")
                logger.info(f"Auto-selected host: {hosts[prime_index]['name']}")
                return hosts[prime_index]
            
            time.sleep(0.05)


# ==================== SSH-AGENT ====================
def ensure_ssh_agent(key_path: str, passphrase: Optional[str] = None) -> bool:
    """
    Load SSH key into ssh-agent.
    
    Args:
        key_path: Path to SSH key
        passphrase: Optional passphrase for key
        
    Returns:
        True if successful
    """
    if not os.path.exists(key_path):
        logger.error(f"SSH key not found: {key_path}")
        return False
    
    try:
        result = subprocess.run(["ssh-agent", "-s"], capture_output=True, text=True, timeout=5)
        output = result.stdout
        
        sock_match = re.search(r'SSH_AUTH_SOCK=([^;]+);', output)
        if not sock_match:
            logger.warning("Could not detect SSH_AUTH_SOCK")
            return False
        
        os.environ["SSH_AUTH_SOCK"] = sock_match.group(1)
        
        if passphrase:
            proc = subprocess.Popen(
                ["ssh-add", key_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            try:
                out, err = proc.communicate(passphrase + "\n", timeout=10)
                if proc.returncode == 0:
                    print(color("✓") + " Key loaded into ssh-agent")
                    logger.info("SSH key loaded successfully with passphrase")
                    return True
                else:
                    logger.error(f"ssh-add failed: {err.strip()}")
                    print(color("✗") + f" ssh-add error: {err.strip()}")
            except subprocess.TimeoutExpired:
                proc.kill()
                logger.error("ssh-add timeout")
        else:
            result = subprocess.run(["ssh-add", key_path], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(color("✓") + " Key loaded into ssh-agent")
                logger.info("SSH key loaded successfully")
                return True
            else:
                logger.warning(f"ssh-add error: {result.stderr.strip()}")
                print(color("✗") + f" ssh-add error: {result.stderr.strip()}")
                return False
    
    except subprocess.TimeoutExpired:
        logger.error("ssh-agent command timeout")
        return False
    except Exception as e:
        logger.error(f"Failed to run ssh-agent: {e}")
        return False


# ==================== ERROR HANDLER ====================
def handle_error(msg: str, cleanup: bool = True) -> None:
    """
    Handle errors and cleanup.
    
    Args:
        msg: Error message
        cleanup: Whether to attempt cleanup
    """
    print(color("✗") + " " + msg)
    logger.error(msg)
    
    if cleanup:
        stop_script = os.path.join(config.work_dir, "stop_proxy.bat")
        if os.path.exists(stop_script):
            try:
                subprocess.run([stop_script], check=True, timeout=10)
                print(color("✓") + " Proxy state restored via stop_proxy.bat")
                logger.info("Cleanup executed successfully")
            except Exception as e:
                logger.warning(f"Failed to run cleanup script: {e}")
                print(color("⚠") + f" Failed to run stop_proxy.bat: {e}")
        else:
            logger.warning("stop_proxy.bat not found")
            print(color("⚠") + " stop_proxy.bat not found!")
    
    input("\nPress Enter to exit...")
    sys.exit(1)


# ==================== MAIN ====================
def main() -> None:
    """Main application entry point."""
    try:
        print("=" * 60)
        print("SOCKS5 System Proxy Creator (OpenSSH - Optimized)")
        print("=" * 60)
        
        # Validate configuration
        if not config.validate():
            handle_error("Configuration validation failed")
        
        # Ensure SSH agent directory exists
        if not ensure_ssh_agent_dir():
            logger.warning("Failed to create SSH agent directory")
        
        # Check if SSH is available
        if not shutil.which(config.ssh_path):
            handle_error("OpenSSH not found! Please install OpenSSH Client.")
        
        logger.info("Application started")
        
        # Parse SSH config
        hosts = parse_ssh_config(config.ssh_config_path)
        if not hosts:
            handle_error(f"No hosts found in {config.ssh_config_path}")
        
        print(color("✓") + f" Found {len(hosts)} host(s)")
        
        # Select host
        selected_host = select_host_menu(hosts)
        if not selected_host:
            handle_error("No host selected.", cleanup=False)
        
        # Validate SSH key
        key_path = selected_host.get('IdentityFile', '')
        if not key_path:
            handle_error("IdentityFile not specified in SSH config for this host")
        
        key_path = validate_key_file(key_path)
        if not key_path:
            handle_error("SSH key file not found or not readable. Check ~/.ssh/config IdentityFile path")
        
        # Display selected host info
        print(f"\n{color('✓')} Selected: {selected_host['name']}")
        print(f" Host: {selected_host.get('HostName', 'N/A')}")
        print(f" User: {selected_host.get('User', 'root')}")
        print(f" Port: {selected_host.get('Port', '22')}")
        print(f" Key: {key_path}")
        
        # Load passphrase from file
        passphrase = load_passphrase_from_file()
        has_passphrase = passphrase is not None
        
        # Save proxy state
        if not save_proxy_state(selected_host, key_path, has_passphrase):
            handle_error("Failed to save proxy state")
        
        # Load SSH key into agent (with passphrase if available)
        if not ensure_ssh_agent(key_path, passphrase):
            logger.warning("Failed to load key into ssh-agent, continuing...")
        
        # Generate PAC file from template
        pac_path = os.path.join(config.work_dir, "proxy.pac")
        if not generate_pac_file_from_template(pac_path, config.proxy_port):
            handle_error("Failed to generate PAC file")
        
        # Start local HTTP server
        http_pid = start_local_http_server(pac_path)
        if not http_pid:
            handle_error("Failed to start local HTTP server")
        
        # Configure system proxy
        pac_http_url = f"http://127.0.0.1:{config.pac_http_port}/proxy.pac"
        if not set_system_proxy_with_pac_http(pac_http_url):
            handle_error("Failed to configure system PAC proxy")
        
        # Start SSH tunnel (pass passphrase if available)
        tunnel_proc = start_ssh_tunnel(selected_host, key_path, passphrase)
        if not tunnel_proc:
            handle_error("Failed to start SSH tunnel")
        
        # Success message
        print(f"\n{'='*60}")
        print(color("✓") + f" SOCKS5 proxy ACTIVE: 127.0.0.1:{config.proxy_port}")
        print(color("✓") + f" System proxy CONFIGURED (PAC via HTTP)")
        print(color("✓") + f" Tunnel to: {selected_host['name']}")
        print(f"{'='*60}\n")
        
        logger.info("Proxy setup complete - running in background")

        # Готово: окно сразу закроется!
        return

    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
        handle_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
