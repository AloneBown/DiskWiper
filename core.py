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


import subprocess
import tempfile
import os
import json

class DiskCore:
    def __init__(self):
        self.disks = []

    def get_disk_list(self, show_usb=True):
        # Fetch physical disks via PowerShell with extended data in JSON format
        ps_cmd = (
            "Get-Disk | "
            "Select-Object Number, FriendlyName, BusType, Size, AllocatedSize, "
            "OperationalStatus, HealthStatus, @{Name='PartitionCount';Expression={(Get-Partition -DiskNumber $_.Number | Measure-Object).Count}} | "
            "ConvertTo-Json -Compress"
        )
        
        try:
            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                text=True, encoding='cp866', creationflags=0x08000000
            ).strip()

            if not output: return []
            
            data = json.loads(output)
            raw_list = data if isinstance(data, list) else [data]
            
            processed_disks = []
            for d in raw_list:
                d_id = str(d['Number'])
                # Skip system drive and filter USB if needed
                if d_id == '0' or (not show_usb and d['BusType'] == 'USB'):
                    continue
                processed_disks.append(d)
            
            processed_disks.sort(key=lambda x: int(x['Number']))
            
            self.disks = processed_disks
            return self.disks
        except Exception as e:
            return f"Error: {str(e)}"

    def wipe_disk(self, disk_id, callback_log):
        callback_log(f"[*] Initializing Disk {disk_id} wipe...", "info")
        script = (
            f"select disk {disk_id}\n"
            "clean\n"
            "create partition primary\n"
            "format fs=ntfs quick\n"
            "assign\n"
            "exit"
        )
        
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(script)
                tmp_path = f.name
            
            res = subprocess.run(
                ['diskpart', '/s', tmp_path],
                capture_output=True, text=True, encoding='cp866',
                creationflags=0x08000000
            )
            
            if res.returncode == 0:
                callback_log(f"[OK] Disk {disk_id} wiped and formatted.", "success")
                return True
            
            err = res.stderr.strip() or "Diskpart internal error"
            callback_log(f"[FAIL] Disk {disk_id}: {err[:60]}", "error")
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass