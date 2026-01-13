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

import customtkinter as ctk
from tkinter import messagebox
import threading, os, json, sys, time, platform
from core import DiskCore

# Global constants for the application
VERSION = "1.0.1"
APP_NAME = "DiskWiper"
CONFIG_NAME = "config.json"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=15, border_width=2, border_color="#333")
        self.parent = parent
        self.debug_visible = False
        self._init_ui()

    def _init_ui(self):
        # Header for settings panel
        ctk.CTkLabel(self, text="Settings", font=("Roboto", 22, "bold")).pack(pady=(20, 15))

        # Settings switches linked to application state
        self.usb_switch = ctk.CTkSwitch(self, text="Show USB Devices", command=self.update_parent_cfg)
        self.usb_switch.pack(pady=10, padx=40, anchor="w")
        
        self.details_switch = ctk.CTkSwitch(self, text="Extended Disk Info", command=self.update_parent_cfg)
        self.details_switch.pack(pady=10, padx=40, anchor="w")

        ctk.CTkLabel(self, text=f"Version: {VERSION}", font=("Roboto", 12, "italic"), text_color="gray").pack(pady=(15, 5))
        
        # Debugging information toggle
        self.debug_btn = ctk.CTkButton(self, text="▶ Show Debug Info", fg_color="transparent", 
                                      hover=False, text_color="#3b8ed0", command=self.toggle_debug)
        self.debug_btn.pack(pady=5)
        
        self.debug_text = ctk.CTkTextbox(self, width=320, height=120, font=("Consolas", 11), state="disabled")
        
        # Bottom navigation
        ctk.CTkButton(self, text="Close & Return", fg_color="#444", hover_color="#555", 
                      command=self.hide).pack(side="bottom", pady=20)

    def toggle_debug(self):
        if not self.debug_visible:
            info = (f"OS: {platform.system()} {platform.release()}\n"
                    f"Node: {platform.node()}\n"
                    f"Arch: {platform.machine()}\n"
                    f"Python: {sys.version.split()[0]}\n"
                    f"Path: {os.path.abspath(sys.argv[0])}")
            
            self.debug_text.configure(state="normal")
            self.debug_text.delete("1.0", "end")
            self.debug_text.insert("1.0", info)
            self.debug_text.configure(state="disabled")
            self.debug_text.pack(pady=10, padx=20)
            self.debug_btn.configure(text="▼ Hide Debug Info")
        else:
            self.debug_text.pack_forget()
            self.debug_btn.configure(text="▶ Show Debug Info")
        self.debug_visible = not self.debug_visible

    def update_parent_cfg(self):
        self.parent.settings['usb'] = bool(self.usb_switch.get())
        self.parent.settings['details'] = bool(self.details_switch.get())
        self.parent.save_settings()

    def show(self):
        self.usb_switch.select() if self.parent.settings['usb'] else self.usb_switch.deselect()
        self.details_switch.select() if self.parent.settings['details'] else self.details_switch.deselect()
        self.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.7)
        self.lift()

    def hide(self):
        self.place_forget()

class DiskWiperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("600x780")
        self.resizable(False, False)
        
        self.core = DiskCore()
        self.checkboxes = {}
        self.is_wiping = False
        self.disk_count_cache = 0
        self.settings = {'usb': True, 'details': False}

        self.app_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), APP_NAME)
        self.config_file = os.path.join(self.app_dir, CONFIG_NAME)
        
        self.setup_ui()
        self.load_settings()

        self.settings_overlay = SettingsFrame(self)
        
        self.refresh()
        self.start_auto_refresh()

    def setup_ui(self):
        # Application Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(header, text=APP_NAME.upper(), font=("Roboto", 28, "bold"), text_color="#3b8ed0").pack(side="left", padx=10)
        ctk.CTkButton(header, text="⚙ Settings", width=100, command=lambda: self.settings_overlay.show()).pack(side="right", padx=10)
        
        # Scrollable area for drive list
        self.scroll = ctk.CTkScrollableFrame(self, width=640, height=350, label_text="Physical Storage Detection")
        self.scroll.pack(pady=10, padx=20)

        # Progress reporting
        self.prog_lbl = ctk.CTkLabel(self, text="Progress: 0%", font=("Roboto", 12))
        self.prog_lbl.pack()
        self.bar = ctk.CTkProgressBar(self, width=520)
        self.bar.set(0)
        self.bar.pack(pady=5)

        # Control panel
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(pady=15)

        self.master_cb = ctk.CTkCheckBox(controls, text="", width=30, command=self.toggle_all_disks)
        self.master_cb.grid(row=0, column=0, padx=(0, 15))

        self.refresh_btn = ctk.CTkButton(controls, text="Refresh", width=140, height=38, command=self.refresh)
        self.refresh_btn.grid(row=0, column=1, padx=5)
        
        self.wipe_btn = ctk.CTkButton(controls, text="WIPE", width=180, height=38, 
                                     fg_color="#a10000", hover_color="#7d0000", font=("Roboto", 13, "bold"),
                                     command=self.confirm_action)
        self.wipe_btn.grid(row=0, column=2, padx=5)
        self.log_box = ctk.CTkTextbox(self, width=640, height=150, font=("Consolas", 12), state="disabled")
        self.log_box.pack(pady=(5, 20), padx=20)
        
        self.log_box._textbox.tag_config("info", foreground="#3b8ed0")
        self.log_box._textbox.tag_config("success", foreground="#2eb82e")
        self.log_box._textbox.tag_config("error", foreground="#ff4d4d")

    def load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.settings['usb'] = data.get('show_usb', True)
                    self.settings['details'] = data.get('show_details', False)
        except Exception: pass

    def save_settings(self):
        try:
            os.makedirs(self.app_dir, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({'show_usb': self.settings['usb'], 'show_details': self.settings['details']}, f, indent=4)
            self.refresh()
        except Exception: pass

    def start_auto_refresh(self):
        # Polling background thread for hardware changes
        def check_loop():
            while True:
                time.sleep(4)
                if not self.is_wiping:
                    disks = self.core.get_disk_list(self.settings['usb'])
                    count = len(disks) if isinstance(disks, list) else 0
                    if count != self.disk_count_cache:
                        self.disk_count_cache = count
                        self.after(0, self.refresh)
        threading.Thread(target=check_loop, daemon=True).start()

    def toggle_all_disks(self):
        state = self.master_cb.get()
        for cb, _ in self.checkboxes.values():
            cb.select() if state else cb.deselect()

    def log(self, msg, level="default"):
        self.after(0, lambda: self._log_exec(msg, level))

    def _log_exec(self, msg, level):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{msg}\n", level)
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def refresh(self):
        for w in self.scroll.winfo_children(): w.destroy()
        self.checkboxes = {}
        disks = self.core.get_disk_list(self.settings['usb'])
        
        if isinstance(disks, str): return self.log(disks, "error")
        if not disks:
            self.log("No compatible storage devices detected.", "info")
            self.disk_count_cache = 0
            return

        self.disk_count_cache = len(disks)
        
        for d in disks:
            size_gb = round(int(d['Size']) / (1024**3))
            row = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row.pack(fill="x", pady=5, padx=5)
            
            # Formatted drive label
            info = f"Disk {d['Number']} | {size_gb} GB | {d['FriendlyName'][:15]}"
            if self.settings['details']:
                info += (f"\n   > SN: {d.get('SerialNumber', 'Unknown').strip()} | "
                         f"Vol: {d['PartitionCount']} | Health: {d['HealthStatus']} | FS: {d.get('FileSystem', 'None')}")

            cb = ctk.CTkCheckBox(row, text=info, font=("Roboto", 11 if self.settings['details'] else 12))
            cb.pack(side="left", padx=5)
            
            # Per-drive format selection
            fs_menu = ctk.CTkOptionMenu(row, values=["NTFS", "FAT32", "exFAT"], width=80, height=24, font=("Roboto", 10))
            fs_menu.set("NTFS")
            fs_menu.pack(side="right", padx=5)
            
            self.checkboxes[d['Number']] = (cb, fs_menu)

    def confirm_action(self):
        selected = [(k, v[1].get()) for k, v in self.checkboxes.items() if v[0].get()]
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one drive.")
            return
        
        msg = f"WARNING!\n\nYou are about to wipe {len(selected)} drive(s).\nAll data will be destroyed!\n\nContinue?"
        if messagebox.askyesno("Confirmation", msg, icon='warning'):
            self.start_wipe(selected)

    def start_wipe(self, selected):
        self.is_wiping = True
        self.completed, self.total = 0, len(selected)
        self.wipe_btn.configure(state="disabled")
        self.refresh_btn.configure(state="disabled")
        self.bar.set(0)
        self.log(f"\n--- SESSION STARTED ({self.total} drives) ---", "info")
        threading.Thread(target=self.worker, args=(selected,), daemon=True).start()

    def worker(self, selected):
        for did, fs in selected:
            self.core.wipe_disk(did, fs, self.log)
            self.after(0, self.update_progress)
        self.log("--- OPERATIONS FINISHED ---", "info")
        self.after(0, self.finish_ui)

    def finish_ui(self):
        self.is_wiping = False
        self.wipe_btn.configure(state="normal")
        self.refresh_btn.configure(state="normal")
        self.master_cb.deselect()
        messagebox.showinfo("Complete", "Wiping process has finished.")
        self.refresh()

    def update_progress(self):
        self.completed += 1
        val = self.completed / self.total
        self.bar.set(val)
        self.prog_lbl.configure(text=f"Progress: {int(val*100)}%")

if __name__ == "__main__":
    app = DiskWiperGUI()
    app.mainloop()