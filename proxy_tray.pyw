import pystray
from PIL import Image, ImageDraw
import time
import threading
import socket
from pystray import MenuItem as item
import subprocess
import sys
import os # <-- Добавлен импорт os

# --- Configuration ---
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 1080
CHECK_INTERVAL = 2
STOP_SCRIPT_PATH = 'stop_proxy.bat'
TRAY_PID_FILE = 'x_tray_monitor.pid' # PID file

# --- Global State ---
icon = None
last_status_online = False 

# ---------------- НОВАЯ ФУНКЦИЯ ----------------
def save_tray_pid():
    """Saves the current process PID to a file."""
    try:
        with open(TRAY_PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
# ------------------------------------------------

def create_circle_icon(color):
    # ... (оставлено без изменений)
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((1, 1, 62, 62), fill=color, outline="#00000000")
    return image

def check_tcp_connection(host, port, timeout=1):
    # ... (оставлено без изменений)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def trigger_cleanup_script():
    # ... (оставлено без изменений)
    try:
        subprocess.Popen(['start', STOP_SCRIPT_PATH], shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED | subprocess.NO_WINDOW)
    except Exception: pass

def update_icon_status(is_online):
    # ... (оставлено без изменений)
    global icon
    if icon is None: return
    
    if is_online:
        icon.icon = create_circle_icon("#0FFF0F")
        icon.title = "SOCKS5: OK (127.0.0.1:1080)"
    else:
        icon.icon = create_circle_icon("#FF0F0F")
        icon.title = "SOCKS5: OFFLINE"

def monitor_proxy_status():
    # ... (оставлено без изменений)
    global last_status_online
    time.sleep(5) 
    while True:
        is_online = check_tcp_connection(PROXY_HOST, PROXY_PORT)
        update_icon_status(is_online)

        if not is_online and last_status_online:
            trigger_cleanup_script()
            
        last_status_online = is_online
        time.sleep(CHECK_INTERVAL)

def quit_action(icon, item):
    icon.stop()

def setup(icon_obj):
    global icon
    icon = icon_obj
    save_tray_pid() # <-- Вызов сохранения PID
    icon.visible = True
    threading.Thread(target=monitor_proxy_status, daemon=True).start()

if __name__ == '__main__':
    menu = (item('Quit Monitor', quit_action),)
    initial_image = create_circle_icon('yellow')
    icon_object = pystray.Icon("proxy_monitor", initial_image, "Initializing...", menu)
    icon_object.run(setup)