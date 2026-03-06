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

import os, platform, sys, ctypes, threading
import tkinter as tk
import customtkinter as ctk
import qrcode
import config

class SmartInfoWindow(ctk.CTkToplevel):
    def __init__(self, parent, disk_id, disk_name):
        super().__init__(parent)
        self.title(f"S.M.A.R.T. Analysis - Disk {disk_id}")
        self.geometry("750x500") # Сделал окно компактнее
        self.resizable(False, False)
        self.critical_ids = {5, 175, 187, 188, 196, 197, 198, 199}
        self.disk_info_data, self.img_ctk = {}, None 
        self._setup_ui(disk_id, disk_name)
        threading.Thread(target=self._load_async, args=(disk_id,), daemon=True).start()

    def _setup_ui(self, disk_id, disk_name):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        ctk.CTkLabel(header, text=f"Health Report: {disk_name}", font=("Roboto", 16, "bold")).pack(side="left")
        self.qr_btn = ctk.CTkButton(header, text="Generate QR", width=100, command=self._show_qr, state="disabled")
        self.qr_btn.pack(side="right")

        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        for i, w in enumerate([50, 280, 80, 80, 200]): self.scroll.grid_columnconfigure(i, weight=1 if i==1 else 0, minsize=w)
        for i, h in enumerate(["ID", "Attribute", "Value", "Worst", "Raw"]): ctk.CTkLabel(self.scroll, text=h, font=("Roboto", 11, "bold"), text_color="gray").grid(row=0, column=i, padx=12, sticky="w")

    def _load_async(self, disk_id):
        raw_data = self.master.core.get_detailed_smart(disk_id)
        details = next((d for d in self.master.core.disks if str(d['Number']) == str(disk_id)), {})
        grade_info = self.master.core.calculate_grade(raw_data, details)
        
        self.disk_info_data = {
            "sn": details.get("SerialNumber", "N/A").strip(), "model": details.get("FriendlyName", "Unknown"),
            "size": f"{round(int(details.get('Size', 0)) / (1024**3))} GB", "grade": grade_info['grade'],
            "hours": grade_info['hours'], "warnings": grade_info.get('warnings', [])
        }
        self.after(0, self._render_data, raw_data, grade_info)

    def _render_data(self, data, grade_info):
        if not data:
            return ctk.CTkLabel(self.scroll, text="Access Denied: Run as Administrator to read SMART.", text_color="orange").grid(row=1, column=0, columnspan=5, pady=30)
        self.qr_btn.configure(state="normal")
        
        summary = ctk.CTkFrame(self.scroll, fg_color="#222", corner_radius=5)
        summary.grid(row=1, column=0, columnspan=5, sticky="ew", pady=5, padx=5)
        
        g_color = config.GRADE_COLORS.get(grade_info['grade'], "#fff")
        
        glbl = ctk.CTkLabel(summary, text=f"Grade: {grade_info['grade']}", text_color=g_color, font=("Roboto", 16, "bold"))
        glbl.pack(side="left", padx=10, pady=8)
        
        stats_frame = ctk.CTkFrame(summary, fg_color="transparent")
        stats_frame.pack(side="left", fill="x", expand=True, padx=5)

        trigger = grade_info.get('trigger')
        
        # Разный список параметров в зависимости от типа диска
        if grade_info.get('is_ssd'):
            stats = [
                ('health_pct', f"Life: {grade_info['health_pct']}%"),
                ('writes_gb', f"W: {grade_info['writes_gb']}GB"),
                ('reads_gb', f"R: {grade_info['reads_gb']}GB"),
                ('hours', f"POH: {grade_info['hours']}h"),
                ('starts', f"Starts: {grade_info['starts']}"),
                ('realloc', f"Realloc: {grade_info['realloc']}"),
                ('pending', f"Pending: {grade_info['pending']}")
            ]
        else:
            stats = [
                ('hours', f"POH: {grade_info['hours']}h"),
                ('realloc', f"Realloc: {grade_info['realloc']}"),
                ('pending', f"Pending: {grade_info['pending']}")
            ]

        # Отрисовка статов с динамической подсветкой триггера
        for key, text in stats:
            color = g_color if key == trigger else "#aaaaaa"
            font = ("Roboto", 12, "bold") if key == trigger else ("Roboto", 11)
            ctk.CTkLabel(stats_frame, text=text, text_color=color, font=font).pack(side="left", padx=7)

        for i, attr in enumerate(data, start=2):
            aid, name, val, worst, raw = attr.get('ID', '-'), attr.get('Name', f"Unknown {attr.get('ID')}"), attr.get('Value', '-'), attr.get('Worst', '-'), attr.get('Raw', '-')
            color = config.COLOR_CRITICAL if isinstance(aid, int) and aid in self.critical_ids and str(raw) != "0" and raw != 0 else config.COLOR_INFO if aid in (9, "SYS", "NVMe") else config.COLOR_TEXT_DIM
            for j, t in enumerate([aid, name, val, worst, raw]): ctk.CTkLabel(self.scroll, text=str(t), text_color=color).grid(row=i, column=j, padx=12, sticky="w")

    def _show_qr(self):
        qw = ctk.CTkToplevel(self)
        qw.title("Disk ID Card"); qw.geometry("400x520"); qw.resizable(False, False)
        qr_str = f"SN:{self.disk_info_data['sn']}\nMDL:{self.disk_info_data['model']}\nCAP:{self.disk_info_data['size']}\nGRD:{self.disk_info_data['grade']}\nPOH:{self.disk_info_data['hours']}"
        if self.disk_info_data.get("warnings"): qr_str += f"\nWARN:{','.join(self.disk_info_data['warnings'])}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_str); qr.make(fit=True)
        self.img_ctk = ctk.CTkImage(light_image=qr.make_image(fill_color="black", back_color="white").convert("RGB"), size=(300, 300))
        ctk.CTkLabel(qw, text="Disk Identity QR", font=("Roboto", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(qw, image=self.img_ctk, text="").pack(pady=10)
        ctk.CTkLabel(qw, text=qr_str.replace(',', ', '), font=("Consolas", 10), justify="left").pack(pady=10)

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=15, border_width=2, border_color="#333")
        self.parent = parent
        ctk.CTkLabel(self, text="Settings", font=("Roboto", 22, "bold")).pack(pady=20)
        self.usb_sw = ctk.CTkSwitch(self, text="Show USB Devices", command=self._save); self.usb_sw.pack(pady=5, padx=40, anchor="w")
        self.det_sw = ctk.CTkSwitch(self, text="Extended View", command=self._save); self.det_sw.pack(pady=5, padx=40, anchor="w")
        self.disk0_sw = ctk.CTkSwitch(self, text="Show Disk 0 (OS/Test)", command=self._save); self.disk0_sw.pack(pady=5, padx=40, anchor="w")
        self.debug_sw = ctk.CTkSwitch(self, text="Enable Debug Logging", command=self._save); self.debug_sw.pack(pady=5, padx=40, anchor="w")
        ctk.CTkLabel(self, text="Window Size:", font=("Roboto", 12)).pack(pady=(15, 0), padx=40, anchor="w")
        self.size_var = ctk.StringVar(value="850x700")
        ctk.CTkOptionMenu(self, values=["700x700", "850x700", "1024x800", "1280x900"], variable=self.size_var, command=self._save_size).pack(pady=5, padx=40, anchor="w")
        ctk.CTkButton(self, text="System & Debug Info", fg_color="#3b8ed0", command=self._show_info).pack(pady=15, padx=40, fill="x")
        ctk.CTkButton(self, text="Close", fg_color="#444", command=self.hide).pack(side="bottom", pady=25)

    def _save(self):
        self.parent.settings.update({'usb': bool(self.usb_sw.get()), 'details': bool(self.det_sw.get()), 'disk0': bool(self.disk0_sw.get()), 'debug': bool(self.debug_sw.get())})
        self.parent.save_settings()
        
    def _save_size(self, choice):
        self.parent.settings['window_size'] = choice
        self.parent.geometry(choice)
        self.parent.save_settings(refresh_ui=False)

    def show(self):
        for sw, k in [(self.usb_sw, 'usb'), (self.det_sw, 'details'), (self.disk0_sw, 'disk0'), (self.debug_sw, 'debug')]:
            sw.select() if self.parent.settings.get(k, k=='usb') else sw.deselect()
        self.size_var.set(self.parent.settings.get('window_size', '850x700'))
        self.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.7); self.lift()

    def hide(self): self.place_forget()

    def _show_info(self):
        iw = ctk.CTkToplevel(self)
        iw.title("System Info"); iw.geometry("450x330"); iw.resizable(False, False); iw.attributes("-topmost", True)
        tb = ctk.CTkTextbox(iw, font=("Consolas", 12)); tb.pack(padx=10, pady=10, fill="both", expand=True)
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0 if hasattr(ctypes.windll.shell32, 'IsUserAnAdmin') else False
        tb.insert("0.0", f"--- Program Info ---\nApp Name : {config.APP_NAME}\nVersion  : {config.VERSION}\nGitHub   : {config.GITHUB_REPO}\nLocation : {os.path.abspath(os.getcwd())}\n\n--- System Info ---\nOS       : {platform.system()} {platform.release()} (Build {platform.version()})\nArch     : {platform.machine()} / {platform.architecture()[0]}\nPython   : {sys.version.split(' ')[0]}\nIs Admin : {'YES (Full Access)' if is_admin else 'NO (Limited Access)'}\n")
        tb.configure(state="disabled")