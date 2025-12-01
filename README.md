```markdown
# Just Proxy

🚀 **Windows SOCKS5 Proxy System via SSH Tunnel with PAC Auto-Configuration**

A lightweight, automated proxy solution for Windows that creates a SOCKS5 proxy through an SSH tunnel and automatically configures system-wide proxy settings using a PAC (Proxy Auto-Configuration) file.

## ✨ Features

- **Automatic SSH Tunnel Setup**: Connect to any SSH server from your SSH config file
- **System Proxy Integration**: Automatically configures Windows proxy settings via PAC
- **Intelligent Traffic Routing**: 
  - Direct access for local/Russian/trusted domains
  - Proxy routing for international traffic
- **Secure Passphrase Management**: Optionally store SSH key passphrase in a local file
- **Easy Host Selection**: Interactive menu with auto-selection capability
- **Clean Background Operation**: Runs without visible windows
- **One-Click Start/Stop**: Simple batch files for management

## 📋 Requirements

- **Windows 10/11** (tested on Windows 10)
- **Python 3.7+** (comes with Windows 11, install for Windows 10)
- **OpenSSH Client** (available in Windows Features)
- **SSH Config File** (`~/.ssh/config` with at least one host)
- **SSH Private Key** (RSA/Ed25519 with or without passphrase)

## 🚀 Quick Start

### 1. Clone & Navigate
```bash
git clone https://github.com/yourusername/Just_Proxy.git
cd Just_Proxy
```

### 2. Configure SSH (One-Time Setup)

Ensure you have a valid SSH configuration:

1. **Enable OpenSSH Client**:
   - Windows Settings → Apps → Optional Features → Add Feature → "OpenSSH Client"

2. **Configure SSH Host**:
   Edit `~/.ssh/config` (create if it doesn't exist):
   ```
   Host my-server
       HostName server.example.com
       User yourusername
       Port 22
       IdentityFile ~/.ssh/id_rsa
       IdentitiesOnly yes
   ```

3. **Optional**: For auto-selection, tag your primary host:
   ```
   Host my-server_PRIME  # Will auto-select after 30 seconds
       HostName server.example.com
       User yourusername
       IdentityFile ~/.ssh/id_rsa
   ```

### 3. Configure Proxy Settings (Optional)

1. **Passphrase Storage** (if key has passphrase):
   Create `key_pass` file in project root with your passphrase

2. **Custom PAC Rules**:
   Edit `proxy_back.pac` to modify proxy rules

### 4. Start Proxy
```bash
start_proxy.bat
```

### 5. Stop Proxy
```bash
stop_proxy.bat
```

## 🎯 How It Works

### Architecture
```
┌─────────────┐    SSH Tunnel    ┌─────────────┐
│  Your PC    │ ───────────────► │  SSH Server │
│  (Client)   │   SOCKS5 1080    │  (Gateway)  │
└─────────────┘                  └─────────────┘
       │                                │
       │ PAC: http://localhost:8088     │
       │                                │
┌─────────────┐                  ┌─────────────┐
│  Windows    │                  │  Internet   │
│ System Proxy│                  │             │
└─────────────┘                  └─────────────┘
```

### Traffic Flow
1. **Local/Direct Traffic**: `*.local`, `127.*`, `192.168.*`, Russian domains (`*.ru`, `*.рф`), VK, Yandex, DeepSeek
2. **Proxied Traffic**: All other international traffic through SOCKS5

## ⚙️ Configuration Files

### `proxy_back.pac` - PAC Template
```javascript
function FindProxyForURL(url, host) {
    // Local networks - no proxy
    if (isPlainHostName(host) ||
        shExpMatch(host, "127.*") ||
        shExpMatch(host, "10.*") ||
        shExpMatch(host, "192.168.*")) {
        return "DIRECT";
    }
    
    // Russian domains and services - no proxy
    if (shExpMatch(host, "*.local") || shExpMatch(host, "*.LOCAL") ||
        shExpMatch(host, "*.ru") || shExpMatch(host, "*.RU") ||
        shExpMatch(host, "*.рф") || shExpMatch(host, "*.РФ") ||
        shExpMatch(host, "vk.*") || shExpMatch(host, "VK.*") ||
        shExpMatch(host, "*yandex*") || shExpMatch(host, "*YANDEX*") ||
        shExpMatch(host, "deepseek.*") || shExpMatch(host, "DEEPSEEK.*")) {
        return "DIRECT";
    }
    
    // All other traffic through SOCKS5 proxy
    return "SOCKS5 127.0.0.1:{port}";
}
```

### File Structure
```
Just_Proxy/
├── start_proxy.bat          # Launch script
├── stop_proxy.bat           # Stop/cleanup script
├── proxy_start_v2.py        # Main Python script
├── proxy_stop.py           # Stop proxy Python script
├── proxy_back.pac          # PAC template
├── key_pass                # SSH passphrase (optional, create manually)
├── proxy_state.json        # Generated: Current proxy state
├── pac_http_server.json    # Generated: HTTP server PID
└── proxy.pac               # Generated: Final PAC file
```

## 🔧 Advanced Usage

### Multiple SSH Configurations
Add multiple hosts to `~/.ssh/config`:
```ssh
Host work-server
    HostName work.example.com
    User employee
    IdentityFile ~/.ssh/work_key

Home home-server
    HostName home.example.com
    User admin
    IdentityFile ~/.ssh/home_key
    Port 2222
```

### Custom Port Configuration
Edit `proxy_start_v2.py`:
```python
config.proxy_port = 1080        # SOCKS5 proxy port
config.pac_http_port = 8088     # Local HTTP server port
```

### Manual System Proxy Settings
If automatic configuration fails:
1. Open Windows Settings → Network & Internet → Proxy
2. Set: "Use setup script"
3. Address: `http://127.0.0.1:8088/proxy.pac`
4. Save

## 🐛 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| "ssh.exe not found" | Install OpenSSH Client via Windows Features |
| "No hosts found" | Check `~/.ssh/config` file exists and has valid hosts |
| "Permission denied" | Ensure SSH key has correct permissions (`chmod 600` in WSL) |
| Connection timeout | Verify SSH server is accessible and credentials are correct |
| PAC not working | Check if port 8088 is available, disable other proxy software |

### Debug Mode
For detailed logging, edit `proxy_start_v2.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## 🔒 Security Notes

- **`key_pass` file**: Contains plaintext passphrase. Store securely or use SSH agent
- **SSH Config**: Use `IdentitiesOnly yes` to prevent key scanning
- **Local HTTP Server**: Runs only on `127.0.0.1:8088`, not exposed to network
- **Cleanup**: `stop_proxy.bat` removes all temporary files and resets proxy settings

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## ⭐ Support

If this project helped you, please give it a star! ⭐

---

**Disclaimer**: Use responsibly and in compliance with all applicable laws and regulations.
```