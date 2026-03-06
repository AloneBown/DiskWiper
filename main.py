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

import os, json, time, threading, urllib.request, webbrowser
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

import config
from core import DiskCore
from ui import SmartInfoWindow, SettingsFrame

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class DiskWiperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(config.APP_NAME)
        self.core = DiskCore()
        self.checkboxes, self.is_wiping, self.refreshing = {}, False, False
        self.settings = {'usb': True, 'details': False, 'disk0': False, 'debug': False, 'window_size': '850x700'}
        self.app_dir = os.path.join(os.environ.get('APPDATA', ''), config.APP_NAME)
        self.config_file = os.path.join(self.app_dir, config.CONFIG_NAME)
        
        self.load_settings()
        self.geometry(self.settings.get('window_size', '850x700'))
        
        self.settings_overlay = SettingsFrame(self)
        self._setup_ui()
        self.after(100, self.refresh)
        
        self._check_for_updates()
        self._update_smart_db()
        threading.Thread(target=self._auto_refresh_loop, daemon=True).start()

    def _setup_ui(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(head, text=config.APP_NAME.upper(), font=("Roboto", 26, "bold"), text_color=config.COLOR_INFO).pack(side="left")
        ctk.CTkButton(head, text="⚙ Settings", width=90, command=self.settings_overlay.show).pack(side="right")
        
        self.scroll = ctk.CTkScrollableFrame(self, label_text="Drive Inventory")
        self.scroll.pack(fill="both", expand=True, pady=10, padx=20)
        
        self.prog_lbl = ctk.CTkLabel(self, text="Ready", font=("Roboto", 12)); self.prog_lbl.pack()
        self.bar = ctk.CTkProgressBar(self); self.bar.set(0); self.bar.pack(fill="x", padx=20, pady=5)
        
        btns = ctk.CTkFrame(self, fg_color="transparent"); btns.pack(pady=15)
        self.m_cb = ctk.CTkCheckBox(btns, text="", width=30, command=self._toggle_all); self.m_cb.grid(row=0, column=0, padx=10)
        self.ref_btn = ctk.CTkButton(btns, text="Refresh", width=130, command=self.refresh); self.ref_btn.grid(row=0, column=1, padx=5)
        self.wipe_btn = ctk.CTkButton(btns, text="WIPE", width=160, fg_color="#a10000", font=("Roboto", 13, "bold"), command=self.confirm_wipe); self.wipe_btn.grid(row=0, column=2, padx=5)
        
        self.log_box = ctk.CTkTextbox(self, height=120, font=("Consolas", 11), state="disabled")
        self.log_box.pack(fill="x", pady=10, padx=20)
        for tag, color in [("info", config.COLOR_INFO), ("success", config.COLOR_SUCCESS), ("error", config.COLOR_CRITICAL), ("debug", "gray")]: self.log_box._textbox.tag_config(tag, foreground=color)
        
        footer = ctk.CTkFrame(self, fg_color="transparent"); footer.pack(fill="x", side="bottom", pady=(0, 5), padx=20)
        ctk.CTkLabel(footer, text=f"{config.APP_NAME} v{config.VERSION} | Created by AloneBown", font=("Roboto", 10), text_color="gray").pack(side="right")

    def _check_for_updates(self):
        def fetch():
            try:
                with urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest", headers={'User-Agent': config.APP_NAME}), timeout=5) as r:
                    data = json.loads(r.read().decode())
                    v = data.get("tag_name", "").lstrip("v")
                    if v and v != config.VERSION and [int(x) for x in v.split(".")] > [int(x) for x in config.VERSION.split(".")]:
                        self.after(500, lambda: messagebox.askyesno("Update", f"New version (v{v}) available!\nOpen download page?") and webbrowser.open(data.get("html_url", "")))
            except Exception: pass
        threading.Thread(target=fetch, daemon=True).start()

    def _update_smart_db(self):
        # Silent SMART DB update from GitHub
        def fetch():
            try:
                with urllib.request.urlopen(urllib.request.Request(f"https://raw.githubusercontent.com/{config.GITHUB_REPO}/main/smart_db.json", headers={'User-Agent': config.APP_NAME}), timeout=5) as r:
                    db_path = os.path.join(self.app_dir, "smart_db.json")
                    with open(db_path, "w", encoding="utf-8") as f: f.write(r.read().decode('utf-8'))
                    if self.core.load_smart_db(db_path) and self.settings.get('debug'): self.log("[DEBUG] SMART DB updated from GitHub.", "debug")
            except Exception as e:
                if self.settings.get('debug'): self.log(f"[DEBUG] SMART DB fetch failed: {e}", "debug")
        threading.Thread(target=fetch, daemon=True).start()

    def load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f: self.settings.update(json.load(f))
        except Exception: pass

    def save_settings(self, refresh_ui=True):
        try:
            os.makedirs(self.app_dir, exist_ok=True)
            with open(self.config_file, 'w') as f: json.dump(self.settings, f)
            if refresh_ui: self.refresh()
        except Exception: pass

    def _auto_refresh_loop(self):
        # Passive hardware polling
        while True:
            time.sleep(15)
            if not self.is_wiping and not self.refreshing: self.after(0, self.refresh)

    def refresh(self):
        if self.refreshing or self.is_wiping: return
        self.refreshing = True
        self.ref_btn.configure(state="disabled", text="Scanning...")
        if self.settings.get('debug'): self.log("[DEBUG] Scanning...", "debug")
        threading.Thread(target=lambda: self.after(0, self._rebuild_list, self.core.get_disk_list(self.settings.get('usb', True), self.settings.get('disk0', False))), daemon=True).start()
        

    def _rebuild_list(self, disks):
        for c in self.scroll.winfo_children(): c.destroy()
        self.checkboxes.clear()
        
        for d in disks:
            row = ctk.CTkFrame(self.scroll, fg_color="transparent"); row.pack(fill="x", pady=4, padx=5)
            label = f"Disk {d['Number']} | {round(int(d['Size']) / (1024**3))} GB | {d['FriendlyName'][:20]}"
            if self.settings.get('details'): label += f"\n   > SN: {d.get('SerialNumber', 'N/A').strip()} | FS: {d.get('FileSystem', 'RAW')}"
            
            cb = ctk.CTkCheckBox(row, text=label, font=("Roboto", 11 if self.settings.get('details') else 12))
            cb.pack(side="left", padx=5)
            if str(d['Number']) == '0': cb.configure(state="disabled", text_color="orange")
            
            ctk.CTkButton(row, text="SMART", width=55, height=24, fg_color="#333", command=lambda n=d['Number'], fn=d['FriendlyName']: SmartInfoWindow(self, n, fn)).pack(side="right", padx=2)
            fs = ctk.CTkOptionMenu(row, values=["NTFS", "FAT32", "exFAT"], width=75, height=24); fs.set("NTFS"); fs.pack(side="right", padx=2)
            self.checkboxes[d['Number']] = (cb, fs)
            
        self.ref_btn.configure(state="normal", text="Refresh")
        self.refreshing = False

    def log(self, msg, level="default"): 
        if level != "debug" or self.settings.get('debug'): self.after(0, lambda: (self.log_box.configure(state="normal"), self.log_box.insert("end", f"{msg}\n", level), self.log_box.configure(state="disabled"), self.log_box.see("end")))

    def _toggle_all(self):
        s = self.m_cb.get()
        for cb, _ in self.checkboxes.values(): cb.select() if s and cb.cget("state") != "disabled" else cb.deselect()

    def confirm_wipe(self):
        targets = [(k, v[1].get()) for k, v in self.checkboxes.items() if v[0].get() and v[0].cget("state") != "disabled"]
        if not targets: return messagebox.showwarning("Warning", "Select at least one drive.")
        if any(str(k) == '0' for k, _ in targets): return messagebox.showerror("CRITICAL ERROR", "Wiping Disk 0 is prohibited!")
        if messagebox.askyesno("DANGER", f"Wipe {len(targets)} drive(s)? ALL DATA WILL BE LOST!"): 
            self.is_wiping = True
            self.ref_btn.configure(state="disabled"); self.wipe_btn.configure(state="disabled")
            self.log(f"[*] Started mass-wipe for {len(targets)} drives.", "info")
            threading.Thread(target=self._wipe_worker, args=(targets,), daemon=True).start()

    def _wipe_worker(self, targets):
        # Asynchronous execution of destructive commands
        for i, (did, fs) in enumerate(targets, 1):
            self.core.wipe_disk(did, fs, self.log)
            self.after(0, lambda p=i/len(targets): (self.bar.set(p), self.prog_lbl.configure(text=f"Progress: {int(p*100)}%")))
        self.after(0, lambda: (setattr(self, 'is_wiping', False), self.ref_btn.configure(state="normal"), self.wipe_btn.configure(state="normal"), messagebox.showinfo("Task Done", "Drive cleaning finished."), self.refresh()))

if __name__ == "__main__":
    app = DiskWiperGUI()
    app.mainloop()