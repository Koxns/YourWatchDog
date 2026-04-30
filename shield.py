#!/usr/bin/env python3
# RansomShield - Hybrid Ransomware Defense
# Usage: shield.py [--install|--uninstall|--start|--stop|--status|--daemon]

import os
import sys
import time
import shutil
import tempfile
import psutil
import threading
import queue
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import messagebox

try:
    import setproctitle
    setproctitle.setproctitle("YourWatchDog")
except ImportError:
    pass

# ========== CONFIGURATION ==========
WATCH_FOLDER = None
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".ransomshield_config.json")
PID_FILE = os.path.join(os.path.expanduser("~"), ".ransomshield.pid")
TIME_WINDOW = 2
THRESHOLD = 3
BACKUP_ROOT = os.path.join(tempfile.gettempdir(), "ransomshield_backup")
# ====================================

os.makedirs(BACKUP_ROOT, exist_ok=True)

# Global state
backup_map = {}
event_timeline = []
attack_handling = False
observer = None
process_monitor_running = True
alert_queue = queue.Queue()
asked_pids = set()
allowed_pids = set()

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {msg}")

def load_config():
    global WATCH_FOLDER
    if os.path.exists(CONFIG_FILE):
        import json
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        WATCH_FOLDER = config.get('watch_folder')
        return True
    return False

def save_config(folder):
    import json
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'watch_folder': folder}, f)

def backup_file(file_path):
    if not os.path.isfile(file_path):
        return
    if file_path.endswith('.encrypted'):
        return
    if file_path in backup_map:
        return
    safe_name = file_path.replace(":\\", "_").replace("\\", "_").replace(":", "_") + ".bak"
    backup_path = os.path.join(BACKUP_ROOT, safe_name)
    try:
        shutil.copy2(file_path, backup_path)
        backup_map[file_path] = backup_path
        log(f"Backed up: {file_path}")
    except Exception as e:
        log(f"Backup failed: {e}")

def backup_all_files():
    log("Creating emergency full backup...")
    count = 0
    for root, dirs, files in os.walk(WATCH_FOLDER):
        for file in files:
            full_path = os.path.join(root, file)
            if '.canary_' in file or full_path.endswith('.encrypted'):
                continue
            backup_file(full_path)
            count += 1
    log(f"Emergency backup complete. {count} files protected.")

def restore_all_files():
    restored = 0
    for original, backup in list(backup_map.items()):
        if os.path.exists(backup):
            try:
                shutil.copy2(backup, original)
                log(f"Restored: {original}")
                restored += 1
            except Exception as e:
                log(f"Restore error: {e}")
    log(f"Restored {restored} files.")
    return restored

def kill_process(pid):
    try:
        p = psutil.Process(pid)
        p.kill()
        log(f"Killed process {pid}")
        return True
    except:
        return False

def suspend_process(pid):
    try:
        p = psutil.Process(pid)
        p.suspend()
        log(f"Suspended process {pid}")
        return True
    except:
        return False

def resume_process(pid):
    try:
        p = psutil.Process(pid)
        p.resume()
        log(f"Resumed process {pid}")
        return True
    except:
        return False

def ask_user_to_block(process_name, cmdline):
    root = tk.Tk()
    root.withdraw()
    msg = (f"Suspicious process detected!\n\n"
           f"Process: {process_name}\n"
           f"Command: {' '.join(cmdline)}\n\n"
           f"Do you want to BLOCK this process?")
    answer = messagebox.askyesno("RansomShield - Block Execution?", msg)
    root.destroy()
    return answer

def kill_all_attack_processes():
    killed = False
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline:
                cmd_str = ' '.join(cmdline).lower()
                if any(k in cmd_str for k in ['attack', 'encrypt', 'ransom', 'cryptography', 'fernet']):
                    kill_process(proc.info['pid'])
                    killed = True
        except:
            pass
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'].lower() == 'python.exe' and proc.info['pid'] != current_pid:
                kill_process(proc.info['pid'])
                killed = True
        except:
            pass
    return killed

def monitor_processes():
    global process_monitor_running, asked_pids, allowed_pids, attack_handling
    while process_monitor_running:
        if attack_handling:
            time.sleep(1)
            continue
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    pid = proc.info['pid']
                    if pid in asked_pids or pid in allowed_pids:
                        continue
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmd_str = ' '.join(cmdline).lower()
                        if any(k in cmd_str for k in ['attack', 'encrypt', 'ransom', 'cryptography', 'fernet']):
                            asked_pids.add(pid)
                            suspend_process(pid)
                            proc_name = proc.info['name']
                            block = ask_user_to_block(proc_name, cmdline)
                            if block:
                                kill_process(pid)
                                log(f"User blocked process {pid}")
                            else:
                                log(f"User allowed process {pid}. Taking emergency backup...")
                                backup_all_files()
                                resume_process(pid)
                                allowed_pids.add(pid)
                                log(f"Resumed allowed process {pid}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            log(f"Process monitor error: {e}")
        time.sleep(1)

class FileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.encrypted'):
            backup_file(event.src_path)
            log(f"New file backed up: {event.src_path}")

    def on_modified(self, event):
        global attack_handling, event_timeline, observer
        if event.is_directory:
            return
        if attack_handling:
            return
        if not event.src_path.endswith('.encrypted'):
            backup_file(event.src_path)

        now = time.time()
        event_timeline.append((now, event.src_path))
        while event_timeline and event_timeline[0][0] < now - TIME_WINDOW:
            event_timeline.pop(0)

        if len(event_timeline) >= THRESHOLD:
            attack_handling = True
            log(f"!!! RANSOMWARE BEHAVIOR DETECTED: {len(event_timeline)} events in {TIME_WINDOW}s !!!")
            kill_all_attack_processes()
            restored = restore_all_files()
            alert_queue.put(restored)
            time.sleep(2)
            event_timeline.clear()
            attack_handling = False
            log("Shield reset – continuing to watch for new attacks.")

def start_watching():
    global observer
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    backup_all_files()
    handler = FileHandler()
    observer = Observer()
    observer.schedule(handler, WATCH_FOLDER, recursive=True)
    observer.start()
    log(f"Watching: {WATCH_FOLDER}")

def stop_watching():
    global observer, process_monitor_running
    if observer:
        observer.stop()
        observer.join()
    process_monitor_running = False
    log("Shield stopped.")

def daemon_loop():
    start_watching()
    monitor_thread = threading.Thread(target=monitor_processes, daemon=True)
    monitor_thread.start()
    log("Process monitor active (suspend+backup on allow).")
    root = tk.Tk()
    root.withdraw()
    def check_alerts():
        try:
            restored = alert_queue.get_nowait()
            messagebox.showwarning("RansomShield Alert", f"Ransomware neutralized!\nRestored {restored} files.\nShield continues to protect.")
        except queue.Empty:
            pass
        root.after(1000, check_alerts)
    root.after(1000, check_alerts)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        root.destroy()
    finally:
        stop_watching()
        sys.exit(0)

def find_pythonw():
    """Locate pythonw.exe (used for no‑console background execution)."""
    # Try common locations
    possible = [
        sys.executable.replace("python.exe", "pythonw.exe"),
        os.path.join(os.path.dirname(sys.executable), "pythonw.exe"),
        shutil.which("pythonw")
    ]
    for p in possible:
        if p and os.path.exists(p):
            return p
    # Fallback to sys.executable (will show console, but better than nothing)
    return sys.executable

def install_task():
    """Create scheduled task that starts shield silently at logon."""
    folder = input("Enter the full path of the folder you want to protect: ").strip()
    if not os.path.exists(folder):
        print("Folder does not exist. Create it first.")
        sys.exit(1)
    save_config(folder)
    script_path = os.path.abspath(__file__)
    pythonw = find_pythonw()
    task_name = "RansomShield"
    # Delete any existing task first
    subprocess.run(f'schtasks /delete /tn "{task_name}" /f', shell=True, stderr=subprocess.DEVNULL)
    # Create new task with proper settings
    cmd = (
        f'schtasks /create /tn "{task_name}" '
        f'/tr "{pythonw} \\"{script_path}\\" --daemon" '
        f'/sc onlogon /ru "{os.environ["USERNAME"]}" '
        f'/f /rl HIGHEST'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"RansomShield installed. Will protect: {folder}")
        print("The shield will start automatically on next boot.")
        print("To start immediately, run: python shield.py --start")
    else:
        print("Installation failed. Try running as Administrator.")
        print(result.stderr)

def main():
    parser = argparse.ArgumentParser(description="RansomShield - Hybrid Ransomware Defense")
    parser.add_argument("--install", action="store_true", help="Install as Windows startup task")
    parser.add_argument("--uninstall", action="store_true", help="Remove Windows startup task")
    parser.add_argument("--start", action="store_true", help="Start the shield in background (daemon)")
    parser.add_argument("--stop", action="store_true", help="Stop the background shield")
    parser.add_argument("--status", action="store_true", help="Check if shield is running")
    parser.add_argument("--daemon", action="store_true", help="Internal: run as daemon (no console)")
    args = parser.parse_args()

    if args.install:
        install_task()
        return

    if args.uninstall:
        task_name = "RansomShield"
        subprocess.run(f'schtasks /delete /tn "{task_name}" /f', shell=True)
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        print("RansomShield uninstalled.")
        return

    if args.status:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            if psutil.pid_exists(pid):
                print("RansomShield is RUNNING.")
            else:
                print("RansomShield is NOT running (stale PID file).")
                os.remove(PID_FILE)
        else:
            # Also check if the scheduled task's process is running (fallback)
            # For simplicity, just say not running.
            print("RansomShield is NOT running.")
        return

    if args.stop:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            try:
                p = psutil.Process(pid)
                p.terminate()
                time.sleep(2)
                if p.is_running():
                    p.kill()
                os.remove(PID_FILE)
                print("RansomShield stopped.")
            except:
                print("Could not stop shield.")
        else:
            print("Shield is not running.")
        return

    if args.start or args.daemon:
        if not load_config():
            print("No configuration found. Run --install first.")
            sys.exit(1)
        # Remove stale PID if exists
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    old_pid = int(f.read().strip())
                if not psutil.pid_exists(old_pid):
                    os.remove(PID_FILE)
            except:
                os.remove(PID_FILE)
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        daemon_loop()
        return

    parser.print_help()

if __name__ == "__main__":
    main()