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
import sys
import ctypes
import platform
import threading
import tkinter as tk
import customtkinter as ctk
import qrcode
import config

class ToolTip:
    # Interactive tooltip controller
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
    # S.M.A.R.T. diagnostic and rendering window
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
        
        for i, h in enumerate(["ID", "Attribute", "Value", "Worst", "Raw"]):
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
        
        grade_label = ctk.CTkLabel(summary, text=f"Grade: {grade_info['grade']}", text_color=config.GRADE_COLORS.get(grade_info['grade'], "#fff"), font=("Roboto", 14, "bold"))
        grade_label.pack(side="left", padx=10)
        
        is_ssd = grade_info.get('is_ssd', False)
        
        if is_ssd:
            tooltip_text = (
                f"SSD Grading Criteria:\n"
                f"• Life Left: {grade_info['health_pct']}%\n"
                f"• Written: {grade_info['writes_gb']} GB\n"
                f"• Read: {grade_info['reads_gb']} GB\n"
                f"• Power-On Hours: {grade_info['hours']}h\n"
                f"• Reallocated Sectors: {grade_info['realloc']}\n"
                f"• Pending Sectors: {grade_info['pending']}"
            )
            health_str = f" | Health: {grade_info['health_pct']}%"
        else:
            tooltip_text = (
                f"HDD Grading Criteria:\n"
                f"• Power-On Hours: {grade_info['hours']}h\n"
                f"• Power Cycles: {grade_info['starts']}\n"
                f"• Reallocated Sectors: {grade_info['realloc']}\n"
                f"• Pending Sectors: {grade_info['pending']}"
            )
            health_str = ""
            
        ToolTip(grade_label, tooltip_text)
        ctk.CTkLabel(summary, text=f"POH: {grade_info['hours']}h{health_str}", text_color="gray").pack(side="right", padx=10)

        for i, attr in enumerate(data, start=2):
            aid = attr.get('ID', '-')
            name = attr.get('Name', f"Unknown Attribute {aid}")
            val = attr.get('Value', '-')
            worst = attr.get('Worst', '-')
            raw = attr.get('Raw', '-')
            color = config.COLOR_TEXT_DIM
            
            try:
                if isinstance(aid, int) and aid in self.critical_ids and str(raw) != "0" and raw != 0: 
                    color = config.COLOR_CRITICAL
                elif aid == 9 or aid == "SYS" or aid == "NVMe": 
                    color = config.COLOR_INFO
            except Exception: 
                pass

            ctk.CTkLabel(self.scroll, text=str(aid), text_color=color).grid(row=i, column=0, padx=12, sticky="w")
            ctk.CTkLabel(self.scroll, text=str(name), text_color=color).grid(row=i, column=1, padx=12, sticky="w")
            ctk.CTkLabel(self.scroll, text=str(val), text_color=color).grid(row=i, column=2, padx=12, sticky="w")
            ctk.CTkLabel(self.scroll, text=str(worst), text_color=color).grid(row=i, column=3, padx=12, sticky="w")
            ctk.CTkLabel(self.scroll, text=str(raw), text_color=color).grid(row=i, column=4, padx=12, sticky="w")

    def _show_qr(self):
        # QR Code identity generation
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
    # Application configuration overlay
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
        self.debug_sw = ctk.CTkSwitch(self, text="Enable Debug Logging")
        self.debug_sw.pack(pady=5, padx=40, anchor="w")
        
        ctk.CTkLabel(self, text="Window Size:", font=("Roboto", 12)).pack(pady=(15, 0), padx=40, anchor="w")
        self.size_var = ctk.StringVar(value="850x700")
        self.size_menu = ctk.CTkOptionMenu(self, values=["700x700", "850x700", "1024x800", "1280x900"], variable=self.size_var)
        self.size_menu.pack(pady=5, padx=40, anchor="w")

        self.info_btn = ctk.CTkButton(self, text="System & Debug Info", fg_color="#3b8ed0", command=self._show_info)
        self.info_btn.pack(pady=15, padx=40, fill="x")

        ctk.CTkButton(self, text="Close", fg_color="#444", command=self.hide).pack(side="bottom", pady=25)
        
        self.usb_sw.configure(command=self._save)
        self.det_sw.configure(command=self._save)
        self.disk0_sw.configure(command=self._save)
        self.debug_sw.configure(command=self._save)
        self.size_menu.configure(command=self._save_size)

    def _save(self):
        self.parent.settings['usb'] = bool(self.usb_sw.get())
        self.parent.settings['details'] = bool(self.det_sw.get())
        self.parent.settings['disk0'] = bool(self.disk0_sw.get())
        self.parent.settings['debug'] = bool(self.debug_sw.get())
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
        if self.parent.settings.get('debug', False): self.debug_sw.select()
        else: self.debug_sw.deselect()
        
        self.size_var.set(self.parent.settings.get('window_size', '850x700'))
        self.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.7)
        self.lift()

    def hide(self): 
        self.place_forget()

    def _show_info(self):
        info_win = ctk.CTkToplevel(self)
        info_win.title("System & Debug Info")
        info_win.geometry("450x330")
        info_win.resizable(False, False)
        info_win.attributes("-topmost", True)
        
        textbox = ctk.CTkTextbox(info_win, font=("Consolas", 12))
        textbox.pack(padx=10, pady=10, fill="both", expand=True)
        
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            is_admin = False
            
        info = f"--- Program Info ---\n"
        info += f"App Name : {config.APP_NAME}\n"
        info += f"Version  : {config.VERSION}\n"
        info += f"GitHub   : {config.GITHUB_REPO}\n"
        info += f"Location : {os.path.abspath(os.getcwd())}\n\n"
        info += f"--- System Info ---\n"
        info += f"OS       : {platform.system()} {platform.release()} (Build {platform.version()})\n"
        info += f"Arch     : {platform.machine()} / {platform.architecture()[0]}\n"
        info += f"Python   : {sys.version.split(' ')[0]}\n"
        info += f"Is Admin : {'YES (Full Access)' if is_admin else 'NO (Limited Access)'}\n"
        
        textbox.insert("0.0", info)
        textbox.configure(state="disabled")