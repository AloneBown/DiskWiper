# DiskWiper
# Copyright (C) 2026 AloneBown
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# DO NOT REMOVE THIS HEADER

import os
import json
import time
import urllib.request
import webbrowser
import threading
from tkinter import messagebox
import config

def check_for_updates(app_instance):
    # Asynchronous GitHub API polling
    def fetch_update():
        try:
            url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': f'{config.APP_NAME}-App'})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "").lstrip("v")
                
                download_url = next((asset.get("browser_download_url") for asset in data.get("assets", []) if asset.get("name", "").endswith(".zip")), None)
                        
                if latest_version and latest_version != config.VERSION:
                    v_current = tuple(map(int, config.VERSION.split(".")))
                    v_latest = tuple(map(int, latest_version.split(".")))
                    
                    if v_latest > v_current:
                        app_instance.after(500, _prompt_update, app_instance, latest_version, download_url, data.get("html_url"))
        except Exception as e:
            app_instance.log(f"[DEBUG] GitHub Update Check Failed: {e}", "debug")
            
    threading.Thread(target=fetch_update, daemon=True).start()

def _prompt_update(app_instance, latest_version, download_url, release_url):
    if download_url:
        msg = f"A new version of {config.APP_NAME} (v{latest_version}) is available!\n\nWould you like to automatically download and install it?"
        if messagebox.askyesno("Update Available", msg):
            _perform_auto_update(app_instance, download_url)
    else:
        msg = f"A new version of {config.APP_NAME} (v{latest_version}) is available!\n\nWould you like to open the GitHub page?"
        if messagebox.askyesno("Update Available", msg):
            webbrowser.open(release_url)

def _perform_auto_update(app_instance, download_url):
    # Self-destructing batch script mechanism for hot-swapping executables
    app_instance.ref_btn.configure(state="disabled")
    app_instance.wipe_btn.configure(state="disabled")
    app_instance.log("[*] Downloading update from GitHub... Please wait.", "info")
    
    def downloader():
        try:
            zip_path = "update.zip"
            urllib.request.urlretrieve(download_url, zip_path)
            
            app_instance.log("[OK] Download complete. Restarting to apply update...", "success")
            time.sleep(1)
            
            bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
powershell -command "Expand-Archive -Force '{zip_path}' '.'"
del "{zip_path}"
start {config.APP_NAME}.exe
del "%~f0"
"""
            bat_path = "updater.bat"
            with open(bat_path, "w") as f:
                f.write(bat_content)
            
            os.startfile(bat_path)
            os._exit(0)
            
        except Exception as e:
            app_instance.log(f"[ERR] Auto-Update failed: {e}", "error")
            app_instance.after(0, lambda: app_instance.ref_btn.configure(state="normal"))
            app_instance.after(0, lambda: app_instance.wipe_btn.configure(state="normal"))

    threading.Thread(target=downloader, daemon=True).start()