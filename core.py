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
        # We add -Unique to the FileSystem search to avoid repeating the same FS types 
        # from multiple service partitions (like EFI, Recovery, etc.)
        ps_cmd = (
            "Get-Disk | "
            "Select-Object Number, FriendlyName, BusType, Size, AllocatedSize, SerialNumber, "
            "HealthStatus, OperationalStatus, "
            "@{Name='PartitionCount';Expression={(Get-Partition -DiskNumber $_.Number | Measure-Object).Count}}, "
            "@{Name='FileSystem';Expression={$fs = (Get-Partition -DiskNumber $_.Number | Get-Volume -ErrorAction SilentlyContinue).FileSystemType | Select-Object -Unique; if ($fs) { $fs -join ', ' } else { 'RAW' }}} | "
            "ConvertTo-Json -Compress"
        )
        
        try:
            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                text=True, encoding='cp866', creationflags=0x08000000
            ).strip()

            if not output: return []
            data = json.loads(output)
            raw = data if isinstance(data, list) else [data]
            
            processed = []
            for d in raw:
                d_id = str(d['Number'])
                # Skip system drive and filter USB if needed
                if d_id == '0' or (not show_usb and d['BusType'] == 'USB'):
                    continue
                processed.append(d)
            
            processed.sort(key=lambda x: int(x['Number']))
            self.disks = processed
            return self.disks
        except Exception as e:
            return f"Error: {str(e)}"

    def wipe_disk(self, disk_id, fs_type, callback_log):
        # Supported fs_type: ntfs, fat32, exfat
        callback_log(f"[*] Starting wipe for Disk {disk_id} (FS: {fs_type.upper()})...", "info")
        
        commands = [
            f"select disk {disk_id}",
            "clean",
            "create partition primary",
            f"format fs={fs_type.lower()} quick",
            "assign",
            "exit"
        ]
        
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("\n".join(commands))
                tmp_path = f.name
            
            res = subprocess.run(
                ['diskpart', '/s', tmp_path],
                capture_output=True, text=True, encoding='cp866',
                creationflags=0x08000000
            )
            
            if res.returncode == 0:
                callback_log(f"[OK] Disk {disk_id} wiped and formatted as {fs_type.upper()}.", "success")
                return True
            
            err = res.stderr.strip() or "Diskpart error"
            callback_log(f"[FAIL] Disk {disk_id}: {err[:60]}", "error")
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass