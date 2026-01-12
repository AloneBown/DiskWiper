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
import threading, os, json, sys, time
from core import DiskCore

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class DiskWiperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DiskWiperv 1.0")
        self.geometry("600x780")
        self.resizable(False, False)
        
        self.core = DiskCore()
        self.checkboxes = {}
        self.disk_count_cache = 0
        self.app_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'DiskWiper')
        self.config_file = os.path.join(self.app_dir, 'config.json')
        
        self.setup_ui()
        self.load_settings()
        self.refresh()
        
        self.start_auto_refresh()

    def setup_ui(self):
        # Header
        ctk.CTkLabel(self, text="DISK WIPER", font=("Roboto", 34, "bold"), text_color="#3b8ed0").pack(pady=20)
        
        # Options toggles
        self.opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.opt_frame.pack(fill="x", padx=40)
        
        self.usb_switch = ctk.CTkSwitch(self.opt_frame, text="Show USB", command=self.save_settings)
        self.usb_switch.pack(side="left", padx=10)
        
        self.details_switch = ctk.CTkSwitch(self.opt_frame, text="Extended Info", command=self.save_settings)
        self.details_switch.pack(side="left", padx=10)

        # Drive list area
        self.scroll = ctk.CTkScrollableFrame(self, width=520, height=300, label_text="Physical Storage Detection")
        self.scroll.pack(pady=10, padx=20)

        # Progress reporting
        self.prog_lbl = ctk.CTkLabel(self, text="Progress: 0%", font=("Roboto", 12))
        self.prog_lbl.pack()
        self.bar = ctk.CTkProgressBar(self, width=520)
        self.bar.set(0)
        self.bar.pack(pady=5)

        # Control panel
        self.action_container = ctk.CTkFrame(self, fg_color="transparent")
        self.action_container.pack(pady=15)

        self.master_cb = ctk.CTkCheckBox(self.action_container, text="", width=30, command=self.toggle_all_disks)
        self.master_cb.grid(row=0, column=0, padx=(0, 15))

        self.refresh_btn = ctk.CTkButton(self.action_container, text="Refresh", width=140, height=38, command=self.refresh)
        self.refresh_btn.grid(row=0, column=1, padx=5)
        
        self.wipe_btn = ctk.CTkButton(self.action_container, text="WIPE", width=140, height=38, 
                                     fg_color="#a10000", hover_color="#7d0000", font=("Roboto", 13, "bold"),
                                     command=self.confirm_action)
        self.wipe_btn.grid(row=0, column=2, padx=5)

        # Log box
        self.log_box = ctk.CTkTextbox(self, width=520, height=160, font=("Consolas", 12))
        self.log_box.pack(pady=(5, 20), padx=20)
        
        self.log_box._textbox.tag_config("info", foreground="#3b8ed0")
        self.log_box._textbox.tag_config("success", foreground="#2eb82e")
        self.log_box._textbox.tag_config("error", foreground="#ff4d4d")

    def load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('show_usb', True): self.usb_switch.select()
                    else: self.usb_switch.deselect()
                    
                    if config.get('show_details', False): self.details_switch.select()
                    else: self.details_switch.deselect()
            else:
                self.usb_switch.select()
        except Exception:
            self.usb_switch.select()

    def save_settings(self):
        try:
            os.makedirs(self.app_dir, exist_ok=True)
            config = {
                'show_usb': bool(self.usb_switch.get()),
                'show_details': bool(self.details_switch.get())
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            self.refresh()
        except Exception as e:
            self.log(f"Config error: {e}", "error")

    def start_auto_refresh(self):
        # Polling background thread for hardware changes
        def check_loop():
            while True:
                time.sleep(3)
                disks = self.core.get_disk_list(self.usb_switch.get())
                current_count = len(disks) if isinstance(disks, list) else 0
                
                if current_count != self.disk_count_cache:
                    self.disk_count_cache = current_count
                    self.after(0, self.refresh)

        threading.Thread(target=check_loop, daemon=True).start()

    def toggle_all_disks(self):
        state = self.master_cb.get()
        for cb in self.checkboxes.values():
            if state: cb.select()
            else: cb.deselect()

    def log(self, msg, level="default"):
        self.after(0, lambda: self._log_exec(msg, level))

    def _log_exec(self, msg, level):
        self.log_box.insert("end", f"{msg}\n", level)
        self.log_box.see("end")

    def refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.checkboxes = {}
        disks = self.core.get_disk_list(self.usb_switch.get())
        
        if isinstance(disks, str):
            return self.log(disks, "error")

        if not disks:
            self.log("No compatible storage devices detected.", "info")
            self.disk_count_cache = 0
            return

        self.disk_count_cache = len(disks)
        show_ext = self.details_switch.get()

        for d in disks:
            size_gb = round(int(d['Size']) / (1024**3))
            header = f"Disk {d['Number']} | {size_gb} GB | {d['FriendlyName'][:20]}"
            
            if show_ext:
                used_gb = round(int(d['AllocatedSize']) / (1024**3))
                status = d['OperationalStatus']
                parts = d['PartitionCount']
                header += f"\n   > {status} | Volumes: {parts} | Allocated: {used_gb}GB"

            cb = ctk.CTkCheckBox(self.scroll, text=header, font=("Roboto", 12 if not show_ext else 11))
            cb.pack(anchor="w", pady=5, padx=10)
            self.checkboxes[d['Number']] = cb

    def confirm_action(self):
        selected = [k for k, v in self.checkboxes.items() if v.get()]
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one drive.")
            return
        
        warn = f"WARNING!\n\nYou are about to wipe {len(selected)} drive(s).\nAll files and partitions will be destroyed!\n\nContinue?"
        if messagebox.askyesno("Confirmation", warn, icon='warning'):
            self.start_wipe(selected)

    def start_wipe(self, selected):
        self.completed, self.total = 0, len(selected)
        self.wipe_btn.configure(state="disabled")
        self.refresh_btn.configure(state="disabled")
        self.bar.set(0)
        self.log(f"\n--- SESSION STARTED ({self.total} drives) ---", "info")
        threading.Thread(target=self.worker, args=(selected,), daemon=True).start()

    def worker(self, ids):
        for did in ids:
            self.core.wipe_disk(did, self.log)
            self.after(0, self.update_progress)
        self.log("--- OPERATIONS FINISHED ---", "info")
        self.after(0, self.finish_ui)

    def finish_ui(self):
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