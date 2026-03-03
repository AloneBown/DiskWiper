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
import tkinter as tk
from tkinter import messagebox
import threading, os, json, time
from core import DiskCore
import qrcode

VERSION = "1.0.4"
APP_NAME = "DiskWiper"
CONFIG_NAME = "config.json"

COLOR_CRITICAL = "#ff4d4d"
COLOR_INFO = "#3b8ed0"
COLOR_SUCCESS = "#2eb82e"
COLOR_TEXT_DIM = "#cccccc"
GRADE_COLORS = {
    "A+": "#2eb82e", "A": "#85e085", "B": "#ffcc00",
    "C": "#ff9933", "D": "#ff4d4d", "N/A": "#666666"
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        
        label = tk.Label(tw, text=self.text, justify="left",
                         bg="#222222", fg="#ffffff", relief="solid", borderwidth=1,
                         font=("Roboto", 10), padx=8, pady=5)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class SmartInfoWindow(ctk.CTkToplevel):
    def __init__(self, parent, disk_id, disk_name):
        super().__init__(parent)
        self.title(f"S.M.A.R.T. Analysis - Disk {disk_id}")
        self.geometry("850x650")
        self.resizable(False, False)
        
        self.critical_ids = {5, 175, 187, 188, 196, 197, 198, 199}
        self.disk_info_data = {}
        self.img_ctk = None 
        
        self._setup_ui(disk_id, disk_name)
        threading.Thread(target=self._load_async, args=(disk_id,), daemon=True).start()

    def _setup_ui(self, disk_id, disk_name):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        ctk.CTkLabel(header_frame, text=f"Health Report: {disk_name}", font=("Roboto", 16, "bold")).pack(side="left")
        self.qr_btn = ctk.CTkButton(header_frame, text="Generate QR", width=100, command=self._show_qr, state="disabled")
        self.qr_btn.pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        
        self.scroll.grid_columnconfigure(0, weight=0, minsize=50)
        self.scroll.grid_columnconfigure(1, weight=1, minsize=280)
        self.scroll.grid_columnconfigure(2, weight=0, minsize=80)
        self.scroll.grid_columnconfigure(3, weight=0, minsize=80)
        self.scroll.grid_columnconfigure(4, weight=0, minsize=200)
        
        headers = ["ID", "Attribute", "Value", "Worst", "Raw"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self.scroll, text=h, font=("Roboto", 11, "bold"), text_color="gray").grid(row=0, column=i, padx=12, sticky="w")

    def _load_async(self, disk_id):
        raw_data = self.master.core.get_detailed_smart(disk_id)
        disk_details = next((d for d in self.master.core.disks if str(d['Number']) == str(disk_id)), {})
        grade_info = self.master.core.calculate_grade(raw_data, disk_details)
        
        self.disk_info_data = {
            "sn": disk_details.get("SerialNumber", "N/A").strip(),
            "model": disk_details.get("FriendlyName", "Unknown"),
            "size": f"{round(int(disk_details.get('Size', 0)) / (1024**3))} GB",
            "grade": grade_info['grade'],
            "hours": grade_info['hours'],
            "warnings": grade_info.get('warnings', [])
        }
        self.after(0, self._render_data, raw_data, grade_info)

    def _render_data(self, data, grade_info):
        if not data:
            ctk.CTkLabel(self.scroll, text="Access Denied: Run as Administrator to read SMART.", text_color="orange").grid(row=1, column=0, columnspan=5, pady=30)
            return

        self.qr_btn.configure(state="normal")
        summary = ctk.CTkFrame(self.scroll, fg_color="#222", corner_radius=5)
        summary.grid(row=1, column=0, columnspan=5, sticky="ew", pady=5, padx=5)
        
        grade_label = ctk.CTkLabel(summary, text=f"Grade: {grade_info['grade']}", text_color=GRADE_COLORS.get(grade_info['grade'], "#fff"), font=("Roboto", 14, "bold"))
        grade_label.pack(side="left", padx=10)
        
        tooltip_text = (
            f"Grading Criteria:\n"
            f"• Power-On Hours: {grade_info['hours']}h\n"
            f"• Reallocated Sectors: {grade_info['realloc']}\n"
            f"• Pending Sectors: {grade_info['pending']}\n"
            f"• Power Cycles: {grade_info['starts']}\n"
            f"• Written: {grade_info['writes_gb']} GB\n"
            f"• Read: {grade_info['reads_gb']} GB"
        )
        ToolTip(grade_label, tooltip_text)
        
        ctk.CTkLabel(summary, text=f"POH: {grade_info['hours']}h | Health: {grade_info['health_pct']}%", text_color="gray").pack(side="right", padx=10)

        for i, attr in enumerate(data, start=2):
            aid = attr.get('ID', '-')
            name = attr.get('Name', f"Unknown Attribute {aid}")
            val = attr.get('Value', '-')
            worst = attr.get('Worst', '-')
            raw = attr.get('Raw', '-')
            
            color = COLOR_TEXT_DIM
            try:
                if isinstance(aid, int) and aid in self.critical_ids and str(raw) != "0" and raw != 0: 
                    color = COLOR_CRITICAL
                elif aid == 9 or aid == "SYS" or aid == "NVMe": 
                    color = COLOR_INFO
            except: pass

            ctk.CTkLabel(self.scroll, text=str(aid), text_color=color).grid(row=i, column=0, padx=12, sticky="w")
            ctk.CTkLabel(self.scroll, text=str(name), text_color=color).grid(row=i, column=1, padx=12, sticky="w")
            ctk.CTkLabel(self.scroll, text=str(val), text_color=color).grid(row=i, column=2, padx=12, sticky="w")
            ctk.CTkLabel(self.scroll, text=str(worst), text_color=color).grid(row=i, column=3, padx=12, sticky="w")
            ctk.CTkLabel(self.scroll, text=str(raw), text_color=color).grid(row=i, column=4, padx=12, sticky="w")

    def _show_qr(self):
        qr_window = ctk.CTkToplevel(self)
        qr_window.title("Disk ID Card")
        qr_window.geometry("400x520")
        qr_window.resizable(False, False)
        
        qr_str = (f"SN:{self.disk_info_data['sn']}\n"
                  f"MDL:{self.disk_info_data['model']}\n"
                  f"CAP:{self.disk_info_data['size']}\n"
                  f"GRD:{self.disk_info_data['grade']}\n"
                  f"POH:{self.disk_info_data['hours']}")
                  
        warnings = self.disk_info_data.get("warnings", [])
        if warnings:
            qr_str += f"\nWARN:{','.join(warnings)}"
            
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        
        self.img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(300, 300))
        
        ctk.CTkLabel(qr_window, text="Disk Identity QR", font=("Roboto", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(qr_window, image=self.img_ctk, text="").pack(pady=10)
        
        display_str = qr_str.replace(',', ', ')
        ctk.CTkLabel(qr_window, text=display_str, font=("Consolas", 10), justify="left").pack(pady=10)

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=15, border_width=2, border_color="#333")
        self.parent = parent
        self._init_ui()

    def _init_ui(self):
        ctk.CTkLabel(self, text="Settings", font=("Roboto", 22, "bold")).pack(pady=20)
        
        self.usb_sw = ctk.CTkSwitch(self, text="Show USB Devices")
        self.usb_sw.pack(pady=5, padx=40, anchor="w")
        self.det_sw = ctk.CTkSwitch(self, text="Extended View")
        self.det_sw.pack(pady=5, padx=40, anchor="w")
        self.disk0_sw = ctk.CTkSwitch(self, text="Show Disk 0 (OS/Test)")
        self.disk0_sw.pack(pady=5, padx=40, anchor="w")
        
        ctk.CTkLabel(self, text="Window Size:", font=("Roboto", 12)).pack(pady=(15, 0), padx=40, anchor="w")
        self.size_var = ctk.StringVar(value="850x700")
        self.size_menu = ctk.CTkOptionMenu(self, values=["700x700", "850x700", "1024x800", "1280x900"], variable=self.size_var)
        self.size_menu.pack(pady=5, padx=40, anchor="w")

        ctk.CTkButton(self, text="Close", fg_color="#444", command=self.hide).pack(side="bottom", pady=25)
        
        self.usb_sw.configure(command=self._save)
        self.det_sw.configure(command=self._save)
        self.disk0_sw.configure(command=self._save)
        self.size_menu.configure(command=self._save_size)

    def _save(self):
        self.parent.settings['usb'] = bool(self.usb_sw.get())
        self.parent.settings['details'] = bool(self.det_sw.get())
        self.parent.settings['disk0'] = bool(self.disk0_sw.get())
        self.parent.save_settings()
        
    def _save_size(self, choice):
        self.parent.settings['window_size'] = choice
        self.parent.geometry(choice)
        self.parent.save_settings(refresh_ui=False)

    def show(self):
        if self.parent.settings.get('usb', True): self.usb_sw.select()
        else: self.usb_sw.deselect()
        if self.parent.settings.get('details', False): self.det_sw.select()
        else: self.det_sw.deselect()
        if self.parent.settings.get('disk0', False): self.disk0_sw.select()
        else: self.disk0_sw.deselect()
        
        self.size_var.set(self.parent.settings.get('window_size', '850x700'))
        
        self.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.7)
        self.lift()

    def hide(self): self.place_forget()

class DiskWiperGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings_overlay = None
        self.title(APP_NAME)
        
        self.core = DiskCore()
        self.checkboxes = {}
        self.is_wiping = False
        self.refreshing = False
        self.settings = {'usb': True, 'details': False, 'disk0': False, 'window_size': '850x700'}
        
        self.app_dir = os.path.join(os.environ.get('APPDATA', ''), APP_NAME)
        self.config_file = os.path.join(self.app_dir, CONFIG_NAME)
        
        self.load_settings()
        self.geometry(self.settings.get('window_size', '850x700'))
        
        self.settings_overlay = SettingsFrame(self)
        self._setup_main_ui()
        
        self.after(100, self.refresh)
        threading.Thread(target=self._auto_refresh_loop, daemon=True).start()

    def _setup_main_ui(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(head, text=APP_NAME.upper(), font=("Roboto", 26, "bold"), text_color=COLOR_INFO).pack(side="left")
        ctk.CTkButton(head, text="⚙ Settings", width=90, command=self.settings_overlay.show).pack(side="right")
        
        self.scroll = ctk.CTkScrollableFrame(self, label_text="Drive Inventory")
        self.scroll.pack(fill="both", expand=True, pady=10, padx=20)
        
        self.prog_lbl = ctk.CTkLabel(self, text="Ready", font=("Roboto", 12))
        self.prog_lbl.pack()
        
        self.bar = ctk.CTkProgressBar(self)
        self.bar.set(0)
        self.bar.pack(fill="x", padx=20, pady=5)
        
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=15)
        self.m_cb = ctk.CTkCheckBox(btns, text="", width=30, command=self._toggle_all)
        self.m_cb.grid(row=0, column=0, padx=10)
        self.ref_btn = ctk.CTkButton(btns, text="Refresh", width=130, command=self.refresh)
        self.ref_btn.grid(row=0, column=1, padx=5)
        self.wipe_btn = ctk.CTkButton(btns, text="WIPE", width=160, fg_color="#a10000", font=("Roboto", 13, "bold"), command=self.confirm_wipe)
        self.wipe_btn.grid(row=0, column=2, padx=5)
        
        self.log_box = ctk.CTkTextbox(self, height=120, font=("Consolas", 11), state="disabled")
        self.log_box.pack(fill="x", pady=10, padx=20)
        for tag, color in [("info", COLOR_INFO), ("success", COLOR_SUCCESS), ("error", COLOR_CRITICAL)]:
            self.log_box._textbox.tag_config(tag, foreground=color)

    def load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f: 
                    self.settings.update(json.load(f))
        except: pass

    def save_settings(self, refresh_ui=True):
        try:
            os.makedirs(self.app_dir, exist_ok=True)
            with open(self.config_file, 'w') as f: 
                json.dump(self.settings, f)
            if refresh_ui:
                self.refresh()
        except: pass

    def _auto_refresh_loop(self):
        while True:
            time.sleep(15)
            if not self.is_wiping and not self.refreshing: 
                self.after(0, self.refresh)

    def refresh(self):
        if self.refreshing or self.is_wiping: return
        self.refreshing = True
        self.ref_btn.configure(state="disabled", text="Scanning...")
        threading.Thread(target=self._refresh_task, daemon=True).start()

    def _refresh_task(self):
        disks = self.core.get_disk_list(self.settings.get('usb', True), self.settings.get('disk0', False))
        self.after(0, self._rebuild_list, disks)

    def _rebuild_list(self, disks):
        for child in self.scroll.winfo_children(): child.destroy()
        self.checkboxes.clear()
        
        for d in disks:
            row = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row.pack(fill="x", pady=4, padx=5)
            gb = round(int(d['Size']) / (1024**3))
            label = f"Disk {d['Number']} | {gb} GB | {d['FriendlyName'][:20]}"
            if self.settings.get('details', False): 
                label += f"\n   > SN: {d.get('SerialNumber', 'N/A').strip()} | FS: {d.get('FileSystem', 'RAW')}"
            
            cb = ctk.CTkCheckBox(row, text=label, font=("Roboto", 11 if self.settings.get('details', False) else 12))
            cb.pack(side="left", padx=5)
            
            if str(d['Number']) == '0':
                cb.configure(state="disabled", text_color="orange")
            
            ctk.CTkButton(row, text="SMART", width=55, height=24, fg_color="#333", command=lambda n=d['Number'], fn=d['FriendlyName']: SmartInfoWindow(self, n, fn)).pack(side="right", padx=2)
            fs = ctk.CTkOptionMenu(row, values=["NTFS", "FAT32", "exFAT"], width=75, height=24)
            fs.set("NTFS")
            fs.pack(side="right", padx=2)
            self.checkboxes[d['Number']] = (cb, fs)
            
        self.ref_btn.configure(state="normal", text="Refresh")
        self.refreshing = False

    def log(self, msg, level="default"): 
        self.after(0, self._log_write, msg, level)
        
    def _log_write(self, msg, level):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{msg}\n", level)
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def _toggle_all(self):
        state = self.m_cb.get()
        for cb, _ in self.checkboxes.values():
            if state and cb.cget("state") != "disabled": cb.select()
            else: cb.deselect()

    def confirm_wipe(self):
        targets = [(k, v[1].get()) for k, v in self.checkboxes.items() if v[0].get() and v[0].cget("state") != "disabled"]
        if not targets: 
            return messagebox.showwarning("Warning", "Select at least one drive.")
        
        if any(str(k) == '0' for k, _ in targets):
            messagebox.showerror("CRITICAL ERROR", "Wiping Disk 0 is prohibited!")
            return
            
        if messagebox.askyesno("DANGER", f"Wipe {len(targets)} drive(s)? ALL DATA WILL BE LOST!"): 
            self._execute_wipe(targets)

    def _execute_wipe(self, targets):
        self.is_wiping = True
        self.ref_btn.configure(state="disabled")
        self.wipe_btn.configure(state="disabled")
        self.log(f"[*] Started mass-wipe for {len(targets)} drives.", "info")
        threading.Thread(target=self._wipe_worker, args=(targets,), daemon=True).start()

    def _wipe_worker(self, targets):
        for i, (did, fs) in enumerate(targets, 1):
            self.core.wipe_disk(did, fs, self.log)
            self.after(0, self._update_prog, i/len(targets))
        self.after(0, self._on_wipe_done)

    def _update_prog(self, p):
        self.bar.set(p)
        self.prog_lbl.configure(text=f"Progress: {int(p*100)}%")

    def _on_wipe_done(self):
        self.is_wiping = False
        self.ref_btn.configure(state="normal")
        self.wipe_btn.configure(state="normal")
        messagebox.showinfo("Task Done", "Drive cleaning finished.")
        self.refresh()

if __name__ == "__main__":
    app = DiskWiperGUI()
    app.mainloop()