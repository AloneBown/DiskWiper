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

SMART_NAMES = {
    1: "Raw read error rate", 2: "Throughput Performance", 3: "Spin-up time", 4: "Start/stop count",
    5: "Reallocated sector count", 6: "Read Channel Margin", 7: "Seek error rate", 8: "Seek time performance", 
    9: "Power-on time", 10: "Spin retry count", 11: "Recalibration retries", 12: "Power cycle count", 
    13: "Soft read error rate", 22: "Current Helium Level",
    160: "Uncorrectable sector count read/write", 161: "Number of valid spare block", 
    163: "Number of initial invalid block", 164: "Total erase count", 165: "Maximum erase count", 
    166: "Minimum erase count", 167: "Average erase count", 168: "Max NAND erase count", 
    169: "Total bad block count / SMI remain life", 170: "Available Reserved Space",
    171: "SSD Program Fail Count", 172: "SSD Erase Fail Count", 173: "SSD Wear Leveling Count", 
    174: "Unexpected Power Loss Count", 175: "Bad Cluster Table Count", 176: "Erase Failure Count",
    177: "Wear Range Delta", 178: "Used Reserved Block Count", 179: "Used Reserved Block Count Total",
    180: "Unused Reserved Block Count", 181: "Program Fail Count Total", 182: "Erase Fail Count", 
    183: "SATA Downshift Error", 184: "End-to-End error", 187: "Reported Uncorrectable Errors", 
    188: "Command Timeout", 189: "High Fly Writes", 190: "Airflow Temperature", 191: "G-SENSOR shock counter", 
    192: "Power-off retract count", 193: "Load/unload cycle count", 194: "HDA Temperature", 
    195: "Hardware ECC Recovered", 196: "Reallocation event count", 197: "Current pending sector count", 
    198: "Offline uncorrectable", 199: "Ultra DMA CRC errors", 200: "Write error rate / Multi-Zone Error", 
    201: "Soft Read Error Rate", 202: "Data Address Mark errors", 203: "Run Out Cancel", 204: "Soft ECC Correction",
    205: "Thermal Asperity Rate", 206: "Flying Height", 207: "Spin High Current", 208: "Spin Buzz", 
    209: "Offline Seek Performance", 211: "Vibration During Write", 212: "Shock During Write",
    221: "G-Sense Error Rate", 222: "Loaded Hours", 223: "Load/Unload Retry Count", 224: "Load Friction",
    225: "Load/Unload Cycle Count", 226: "Load-In Time", 227: "Torq-Amp Count", 228: "Power-Off Retract Cycle",
    230: "GMR Head Amplitude", 231: "SSD Life Left / Temperature", 232: "Available Reserved Space",
    233: "Media Wearout Indicator", 234: "Average erase count", 235: "Good Block Count",
    240: "Head flying hours", 241: "Total sectors write", 242: "Total LBA read", 
    246: "Total Host Sector Writes", 247: "Host Program Page Count", 248: "Background Program Page Count", 
    250: "Read Error Retry Rate", 254: "Free-fall counter"
}

class DiskCore:
    CREATE_NO_WINDOW = 0x08000000

    def __init__(self):
        self.disks = []

    def _run_ps(self, cmd):
        try:
            return subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", cmd],
                text=True, encoding='cp866', creationflags=self.CREATE_NO_WINDOW
            ).strip()
        except Exception:
            return ""

    def get_disk_list(self, show_usb=True, show_disk0=False):
        ps_cmd = (
            "Get-Disk | "
            "Select-Object Number, FriendlyName, BusType, Size, AllocatedSize, SerialNumber, "
            "LogicalSectorSize, HealthStatus, OperationalStatus, "
            "@{Name='MediaType';Expression={(Get-PhysicalDisk | Where-Object DeviceId -eq $_.Number).MediaType}}, "
            "@{Name='SpindleSpeed';Expression={(Get-PhysicalDisk | Where-Object DeviceId -eq $_.Number).SpindleSpeed}}, "
            "@{Name='PartitionCount';Expression={(Get-Partition -DiskNumber $_.Number | Measure-Object).Count}}, "
            "@{Name='FileSystem';Expression={$fs = (Get-Partition -DiskNumber $_.Number | Get-Volume -ErrorAction SilentlyContinue).FileSystemType | Select-Object -Unique; if ($fs) { $fs -join ', ' } else { 'RAW' }}} | "
            "ConvertTo-Json -Compress"
        )
        
        output = self._run_ps(ps_cmd)
        if not output: return []

        try:
            data = json.loads(output)
            raw_list = data if isinstance(data, list) else [data]
            self.disks = [
                d for d in raw_list 
                if (str(d['Number']) != '0' or show_disk0) and (show_usb or d['BusType'] != 'USB')
            ]
            self.disks.sort(key=lambda x: int(x['Number']))
            return self.disks
        except: return []

    def get_detailed_smart(self, disk_number):
        data = self._get_smart_legacy(disk_number)
        
        if not data:
            data = self._get_smart_fallback(disk_number)
            
        if data:
            existing_ids = {d.get('ID') for d in data}
            if 5 not in existing_ids:
                data.append({'ID': 5, 'Name': SMART_NAMES[5], 'Value': '100', 'Worst': '100', 'Raw': '0'})
            if 197 not in existing_ids:
                data.append({'ID': 197, 'Name': SMART_NAMES[197], 'Value': '100', 'Worst': '100', 'Raw': '0'})
                
            def sort_key(x):
                aid = x.get('ID')
                return int(aid) if isinstance(aid, int) or (isinstance(aid, str) and aid.isdigit()) else 999
            
            data.sort(key=sort_key)

        return data

    def _get_smart_fallback(self, disk_number):
        ps_cmd = (
            f"$pd = Get-PhysicalDisk | Where-Object DeviceId -eq '{disk_number}'; "
            "if ($pd) { $cnt = $pd | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue; "
            "if ($cnt) { $cnt | Select-Object * | ConvertTo-Json -Compress } }"
        )
        output = self._run_ps(ps_cmd)
        
        if not output: return []
        try:
            raw = json.loads(output)
            disk_info = next((d for d in self.disks if str(d['Number']) == str(disk_number)), None)
            is_nvme = disk_info and disk_info.get('BusType') == 'NVMe'
            
            lbl = "NVMe" if is_nvme else "SYS"
            res = []
            interesting_keys = [
                'PowerOnHours', 'PowerCycles', 'Temperature', 'TemperatureMax', 
                'ReadErrorsTotal', 'WriteErrorsTotal', 'ReadErrorsCorrected', 'WriteErrorsCorrected',
                'ReadLatencyMax', 'WriteLatencyMax', 'FlushLatencyMax',
                'BytesWrittenTotal', 'BytesReadTotal', 'Wear', 'PercentageUsed'
            ]
            
            for key in interesting_keys:
                if key in raw and raw[key] is not None:
                    aid = lbl
                    if key == 'PowerOnHours': aid = 9
                    elif key == 'PowerCycles': aid = 12
                    elif key == 'Temperature': aid = 194
                    elif key in ('Wear', 'PercentageUsed'): aid = 231
                    res.append({'ID': aid, 'Name': key, 'Value': '-', 'Worst': '-', 'Raw': str(raw[key])})
            return res
        except Exception:
            return []

    def _get_smart_legacy(self, disk_number):
        ps_script = f"""
        $dd = Get-WmiObject Win32_DiskDrive | Where-Object Index -eq {disk_number}
        if ($dd) {{
            $pnp = $dd.PNPDeviceID
            $smartList = Get-WmiObject -Namespace root\\wmi -Class MSStorageDriver_FailurePredictData -ErrorAction SilentlyContinue
            $smartData = $null
            
            foreach ($s in $smartList) {{
                if ($s.InstanceName -match [regex]::Escape($pnp)) {{
                    $smartData = $s
                    break
                }}
            }}
            
            if ($smartData) {{
                $v = $smartData.VendorSpecific
                $res = @()
                for ($i = 2; $i -le 361; $i += 12) {{
                    $id = $v[$i]
                    if ($id -eq 0) {{ continue }}
                    [uint64]$raw64 = $v[$i+5] + ([uint64]$v[$i+6] -shl 8) + ([uint64]$v[$i+7] -shl 16) + ([uint64]$v[$i+8] -shl 24) + ([uint64]$v[$i+9] -shl 32) + ([uint64]$v[$i+10] -shl 40)
                    $res += [PSCustomObject]@{{ 
                        ID = $id; Value = $v[$i+3]; Worst = $v[$i+4]; Raw = $raw64
                    }}
                }}
                $res | ConvertTo-Json -Compress
            }}
        }}
        """
        output = self._run_ps(ps_script)
        try:
            data = json.loads(output)
            raw_list = data if isinstance(data, list) else [data]
            disk_info = next((d for d in self.disks if str(d['Number']) == str(disk_number)), None)
            
            is_ssd = False
            if disk_info:
                media_type = str(disk_info.get("MediaType", "")).upper()
                fname = str(disk_info.get("FriendlyName", "")).lower()
                btype = str(disk_info.get("BusType", "")).upper()
                spindle = str(disk_info.get("SpindleSpeed", ""))
                is_ssd = (media_type == "SSD") or ("ssd" in fname) or (btype == "NVME") or (spindle == "0")
            
            has_ssd_attr = any(d.get('ID') in {231, 233, 177, 179, 180, 247, 248, 160, 161, 164, 168, 169} for d in raw_list)
            if has_ssd_attr: is_ssd = True
            
            res = []
            for d in raw_list:
                if not is_ssd and d['ID'] in (231, 233): continue
                d['Name'] = SMART_NAMES.get(d['ID'], f"Vendor Specific ({d['ID']})")
                d['Raw'] = str(d['Raw'])
                res.append(d)
                
            return res
        except Exception:
            return []

    def calculate_grade(self, smart_data, disk_details):
        if not smart_data:
            return {"grade": "N/A", "hours": 0, "health_pct": 0, "realloc": 0, "pending": 0, "starts": 0, "writes_gb": 0, "reads_gb": 0, "warnings": []}
            
        is_ssd = False
        media_type = str(disk_details.get("MediaType", "")).upper()
        fname = str(disk_details.get("FriendlyName", "")).lower()
        btype = str(disk_details.get("BusType", "")).upper()
        spindle = str(disk_details.get("SpindleSpeed", ""))
        is_ssd = (media_type == "SSD") or ("ssd" in fname) or (btype == "NVME") or (spindle == "0")

        ssd_ids = {231, 233, 177, 179, 180, 247, 248, 160, 161, 164, 168, 169}
        if not is_ssd and any(d.get('ID') in ssd_ids for d in smart_data):
            is_ssd = True
        
        metrics = {}
        for d in smart_data:
            if isinstance(d['ID'], int):
                try: metrics[d['ID']] = int(float(d['Raw']))
                except: metrics[d['ID']] = 0
                if d['ID'] == 231:
                    try: metrics['life_val'] = int(d['Value'])
                    except: pass
            elif d.get('Name') == 'BytesWrittenTotal': metrics['bytes_w'] = int(float(d['Raw']))
            elif d.get('Name') == 'BytesReadTotal': metrics['bytes_r'] = int(float(d['Raw']))
            elif d.get('Name') in ('Wear', 'PercentageUsed'): metrics['wear'] = int(float(d['Raw']))
                
        hours = metrics.get(9, 0)
        realloc = metrics.get(5, 0)
        pending = metrics.get(197, 0)
        starts = metrics.get(12, 0)
        
        if 'wear' in metrics:
            life = 100 - metrics['wear']
            if life < 0: life = 0
        elif 'life_val' in metrics and metrics['life_val'] > 0:
            life = metrics['life_val']
        else:
            life = 100
            
        sec_size = disk_details.get('LogicalSectorSize', 512) or 512
        gb_div = 1024**3
        
        raw_writes = metrics.get(241, metrics.get(246, metrics.get(175, 0)))
        raw_reads = metrics.get(242, 0)
        
        if 'bytes_w' in metrics: 
            writes_gb = metrics['bytes_w'] // gb_div
            reads_gb = metrics.get('bytes_r', 0) // gb_div
        else: 
            writes_gb = round((raw_writes * sec_size) / gb_div) if raw_writes > 1000000 else raw_writes
            reads_gb = round((raw_reads * sec_size) / gb_div) if raw_reads > 1000000 else raw_reads

        grade = "D"
        health_pct = life if is_ssd else 100
        
        if is_ssd:
            if realloc == 0 and hours < 20000 and starts < 3000 and life >= 95 and writes_gb < 20000 and reads_gb < 30000: grade = "A+"
            elif realloc == 0 and hours < 25000 and starts < 5000 and life >= 75 and writes_gb < 50000 and reads_gb < 70000: grade = "A"
            elif realloc == 0 and hours < 35000 and starts < 10000 and life >= 50 and writes_gb < 100000 and reads_gb < 120000: grade = "B"
            elif realloc < 10 and hours < 50000 and starts < 20000 and life < 50 and writes_gb < 150000 and reads_gb <= 200000: grade = "C"
            else: grade = "D"
        else:
            if realloc == 0 and pending == 0 and hours < 20000: grade = "A+"
            elif realloc <= 20 and pending == 0 and hours > 20000: grade = "A"
            elif realloc <= 200 and pending == 0 and hours < 25000: grade = "B"
            elif realloc <= 2000 or pending < 10: grade = "C"
            else: grade = "D"

        warnings = []
        if metrics.get(199, 0) > 0: warnings.append(f"CRC_Err:{metrics[199]}")
        uncorr = max(metrics.get(187, 0), metrics.get(198, 0))
        if uncorr > 0: warnings.append(f"Uncorr:{uncorr}")
        if metrics.get(188, 0) > 0: warnings.append(f"Timeouts:{metrics[188]}")
        
        if is_ssd:
            pwr_loss = max(metrics.get(174, 0), metrics.get(192, 0))
            if pwr_loss > 20: warnings.append(f"PwrLoss:{pwr_loss}")
            prog_fails = max(metrics.get(171, 0), metrics.get(181, 0))
            if prog_fails > 0: warnings.append(f"ProgFail:{prog_fails}")
            erase_fails = max(metrics.get(172, 0), metrics.get(182, 0))
            if erase_fails > 0: warnings.append(f"ErsFail:{erase_fails}")
        else:
            if metrics.get(191, 0) > 0: warnings.append(f"GShock:{metrics[191]}")
            if metrics.get(10, 0) > 0: warnings.append(f"SpinRtry:{metrics[10]}")
            
        return {
            "grade": grade, "hours": hours, "health_pct": health_pct,
            "realloc": realloc, "pending": pending, "starts": starts,
            "writes_gb": writes_gb, "reads_gb": reads_gb, "warnings": warnings
        }

    def wipe_disk(self, disk_id, fs_type, callback_log):
        if str(disk_id) == '0':
            callback_log("[ERR] Security restriction: Wiping Disk 0 is forbidden.", "error")
            return False

        callback_log(f"[*] Starting wipe for Disk {disk_id} -> {fs_type.upper()}", "info")
        commands = [f"select disk {disk_id}", "clean", "create partition primary", f"format fs={fs_type.lower()} quick", "assign", "exit"]
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("\n".join(commands))
                tmp_path = f.name
            res = subprocess.run(['diskpart', '/s', tmp_path], capture_output=True, text=True, encoding='cp866', creationflags=self.CREATE_NO_WINDOW)
            if res.returncode == 0:
                callback_log(f"[OK] Disk {disk_id} wipe completed successfully.", "success")
                return True
            callback_log(f"[ERR] Disk {disk_id} error: {res.stderr[:50]}", "error")
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass