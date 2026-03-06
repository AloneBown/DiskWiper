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

import subprocess, tempfile, os, sys, json, re

# Fallback SMART dictionary for offline initialization
SMART_NAMES = {
    1: "Raw Read Error Count", 2: "Throughput Performance", 3: "Spin-Up Time", 4: "Start Stop Count",
    5: "Reallocated Sector Count", 6: "Read Channel Margin", 7: "Seek Error Rate", 8: "Seek Time Performance",
    9: "Power On Hours", 10: "Spin Retry Count", 11: "Calibration Retry Count", 12: "Power Cycle Count",
    13: "Read Soft Error Rate", 14: "Device Raw Capacity", 15: "Device User Capacity", 16: "Initial Spare Blocks",
    17: "Remaining Spare Blocks", 18: "Head Health", 22: "Helium Level", 23: "Helium Condition Lower",
    24: "Helium Condition Upper", 27: "MAMR Health Monitor", 32: "Lifetime Write AmpFctr", 33: "Write AmpFctr",
    71: "Milli Micro Actuator", 82: "Head Health Score", 90: "NAND Master", 100: "Total Erase Count",
    102: "Lifetime PS4 Entry Ct", 103: "Lifetime PS3 Exit Ct", 110: "Proprietary HWC", 111: "Proprietary MP",
    112: "Proprietary RtR", 113: "Proprietary RR", 120: "Proprietary HFAll", 121: "Proprietary HF1st",
    122: "Proprietary HF2nd", 123: "Proprietary HF3rd", 125: "Proprietary SFAll", 126: "Proprietary SF1st",
    127: "Proprietary SF2nd", 128: "Proprietary SF3rd", 148: "Total SLC Erase Ct", 149: "Max SLC Erase Ct",
    150: "Min SLC Erase Ct", 151: "Average SLC Erase Ct", 159: "DRAM 1 Bit Error Count", 160: "Uncorrectable Error Cnt",
    161: "Valid Spare Block Cnt", 162: "Spare Block Count", 163: "Initial Bad Block Count", 164: "Total Erase Count",
    165: "Max Erase Count", 166: "Min Erase Count", 167: "Average Erase Count", 168: "SATA PHY Error Count",
    169: "Remaining Lifetime Perc", 170: "Available Reservd Space", 171: "Program Fail Count", 172: "Erase Fail Count",
    173: "Wear Leveling Count", 174: "Unexpect Power Loss Ct", 175: "Bad Cluster Table Count", 176: "Erase Fail Count Chip",
    177: "Wear Range Delta", 178: "Runtime Invalid Blk Cnt", 179: "Used Rsvd Blk Cnt Tot", 180: "End to End Err Detect",
    181: "Non4k Aligned Access", 182: "Erase Fail Count", 183: "SATA Downshift Count", 184: "End-to-End Error",
    185: "E2E ErrCnt SATA", 187: "Reported Uncorrectable Errors", 188: "Command Timeout", 189: "Factory Bad Block Ct",
    190: "Airflow Temperature", 191: "G-Sensor Shock Count", 192: "Unsafe Shutdown Count", 193: "Load/Unload Cycle Count",
    194: "Temperature", 195: "Hardware ECC Recovered", 196: "Reallocation Event Count", 197: "Current Pending Sector Count",
    198: "Offline Uncorrectable", 199: "CRC Error Count", 200: "Write Error Rate", 201: "Soft Read Error Rate",
    202: "Data Address Mark Errors", 203: "Run Out Cancel", 204: "Soft ECC Correction", 205: "Thermal Asperity Rate",
    206: "Flying Height", 207: "Spin High Current", 208: "Spin Buzz", 209: "Offline Seek Performnce", 210: "SATA CRC Error Count",
    211: "Vibration During Write", 212: "Shock During Write", 213: "Spare Block Cnt Worst", 214: "Reserved Attribute",
    215: "Current TRIM Percent", 218: "CRC Error Count", 220: "Disk Shift", 221: "G-Sense Error Rate", 222: "Loaded Hours",
    223: "Load Retry Count", 224: "Load Friction", 225: "Load/Unload Cycle Count", 226: "Load-In Time", 227: "Torq-Amp Count",
    228: "Power-Off Retract Cycle", 229: "Flash ID", 230: "GMR Head Amplitude", 231: "SSD Life Left",
    232: "Available Reserved Space", 233: "Media Wearout Indicator", 234: "Average Erase Count", 235: "Good Block Count",
    236: "Unstable Power Count", 237: "Flash Writes LBAs High", 240: "Head Flying Hours", 241: "Total LBAs Written",
    242: "Total LBAs Read", 243: "NAND Writes 32MiB", 244: "Average Erase Count", 245: "Max Erase Count",
    246: "Total Host Sector Writes", 247: "Host Program Page Count", 248: "Background Program Page Count", 249: "NAND Writes 1GiB",
    250: "Read Error Retry Rate", 251: "Total NAND Read Ct GiB", 252: "Added Bad Flash Blk Ct", 253: "Unkn CrucialMicron Attr",
    254: "Free Fall Sensor"
}

class DiskCore:
    CREATE_NO_WINDOW = 0x08000000

    def __init__(self):
        self.disks = []
        self.smart_names = SMART_NAMES.copy()
        self.smart_models = []
        
        app_dir = os.path.join(os.environ.get('APPDATA', ''), "DiskWiper")
        downloaded_db = os.path.join(app_dir, "smart_db.json")
        
        if os.path.exists(downloaded_db):
            self.load_smart_db(downloaded_db)
        else:
            self.load_smart_db(self._get_resource_path("smart_db.json"))

    def _get_resource_path(self, relative_path):
        # PyInstaller MEIPASS resolution
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        return os.path.join(base_path, relative_path)

    def load_smart_db(self, path):
        try:
            if not os.path.exists(path): return False
            with open(path, 'r', encoding='utf-8') as f:
                ext_db = json.load(f)
            
            if "base" in ext_db:
                for k, v in ext_db["base"].items():
                    self.smart_names[int(k)] = v
            if "models" in ext_db:
                self.smart_models = ext_db["models"]
            return True
        except Exception:
            return False

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
            "Get-Disk | Select-Object Number, FriendlyName, BusType, Size, AllocatedSize, SerialNumber, "
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
            self.disks = [d for d in raw_list if (str(d['Number']) != '0' or show_disk0) and (show_usb or d['BusType'] != 'USB')]
            self.disks.sort(key=lambda x: int(x['Number']))
            return self.disks
        except Exception: 
            return []

    def get_detailed_smart(self, disk_number):
        data = self._get_smart_legacy(disk_number) or self._get_smart_fallback(disk_number)
        if data:
            # Inject critical attributes if hidden by vendor firmware
            existing_ids = {d.get('ID') for d in data}
            if 5 not in existing_ids:
                data.append({'ID': 5, 'Name': self.smart_names.get(5, "Reallocated sector count"), 'Value': '100', 'Worst': '100', 'Raw': '0'})
            if 197 not in existing_ids:
                data.append({'ID': 197, 'Name': self.smart_names.get(197, "Current pending sector count"), 'Value': '100', 'Worst': '100', 'Raw': '0'})
                
            data.sort(key=lambda x: int(x.get('ID')) if isinstance(x.get('ID'), (int, str)) and str(x.get('ID')).isdigit() else 999)
        return data

    def _get_smart_fallback(self, disk_number):
        # OS-level reliability counters fallback for NVMe/blocked controllers
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
            lbl = "NVMe" if disk_info and disk_info.get('BusType') == 'NVMe' else "SYS"
            res = []
            keys = ['PowerOnHours', 'PowerCycles', 'Temperature', 'ReadErrorsTotal', 'WriteErrorsTotal', 'Wear', 'PercentageUsed']
            
            for key in keys:
                if key in raw and raw[key] is not None:
                    aid = 9 if key == 'PowerOnHours' else 12 if key == 'PowerCycles' else 194 if key == 'Temperature' else 231 if key in ('Wear', 'PercentageUsed') else lbl
                    res.append({'ID': aid, 'Name': key, 'Value': '-', 'Worst': '-', 'Raw': str(raw[key])})
            return res
        except Exception:
            return []

    def _get_smart_legacy(self, disk_number):
        # Reads 6-byte raw ATA SMART payload via WMI bypass
        ps_script = f"""
        $dd = Get-WmiObject Win32_DiskDrive | Where-Object Index -eq {disk_number}
        if ($dd) {{
            $smartList = Get-WmiObject -Namespace root\\wmi -Class MSStorageDriver_FailurePredictData -ErrorAction SilentlyContinue
            foreach ($s in $smartList) {{
                if ($s.InstanceName -match [regex]::Escape($dd.PNPDeviceID)) {{
                    $v = $s.VendorSpecific
                    $res = @()
                    for ($i = 2; $i -le 361; $i += 12) {{
                        $id = $v[$i]
                        if ($id -eq 0) {{ continue }}
                        [uint64]$r = $v[$i+5] + ([uint64]$v[$i+6] -shl 8) + ([uint64]$v[$i+7] -shl 16) + ([uint64]$v[$i+8] -shl 24) + ([uint64]$v[$i+9] -shl 32) + ([uint64]$v[$i+10] -shl 40)
                        $res += [PSCustomObject]@{{ ID=$id; Value=$v[$i+3]; Worst=$v[$i+4]; Raw=$r }}
                    }}
                    $res | ConvertTo-Json -Compress
                    break
                }}
            }}
        }}
        """
        output = self._run_ps(ps_script)
        try:
            raw_list = json.loads(output)
            raw_list = raw_list if isinstance(raw_list, list) else [raw_list]
            disk_info = next((d for d in self.disks if str(d['Number']) == str(disk_number)), None)
            
            friendly_name = str(disk_info.get("FriendlyName", "")) if disk_info else ""
            fname_lower = friendly_name.lower()
            is_ssd = disk_info and ((str(disk_info.get("MediaType", "")).upper() == "SSD") or ("ssd" in fname_lower) or (str(disk_info.get("BusType", "")).upper() == "NVME") or (str(disk_info.get("SpindleSpeed", "")) == "0"))
            
            vendor_attrs, vendor_life_id = {}, None
            for model in self.smart_models:
                try:
                    if re.match(model.get('regex', ''), friendly_name, re.IGNORECASE):
                        vendor_attrs, vendor_life_id = model.get('attributes', {}), model.get('life_id')
                        break
                except Exception: pass

            ssd_indicators = {231, 233, 177, 179, 180, 247, 248, 160, 161, 164, 168, 169}
            if any(d.get('ID') in ssd_indicators for d in raw_list): 
                is_ssd = True
            
            res, composite_ids = [], {1, 7, 9, 189, 195}
            
            for d in raw_list:
                str_id = str(d['ID'])
                if not is_ssd and d['ID'] in (231, 233): continue
                
                d['Name'] = vendor_attrs.get(str_id, self.smart_names.get(d['ID'], f"Vendor Specific ({d['ID']})"))
                if vendor_life_id and str_id == vendor_life_id: d['Is_Life_Attr'] = True
                    
                raw_val = d['Raw_Int'] = int(d['Raw'])
                
                # Seagate composite hex decoding (w2/w1/w0 format)
                if not is_ssd and raw_val > 0xFFFFFFFF and d['ID'] in composite_ids:
                    w2, w1, w0 = (raw_val >> 32) & 0xFFFF, (raw_val >> 16) & 0xFFFF, raw_val & 0xFFFF
                    d['Raw'] = f"{w2}/{w1}/{w0}"
                else:
                    d['Raw'] = str(raw_val)
                res.append(d)
                
            return res
        except Exception:
            return []

    def calculate_grade(self, smart_data, disk_details):
        if not smart_data:
            return {"grade": "N/A", "trigger": None, "hours": 0, "health_pct": 0, "realloc": 0, "pending": 0, "starts": 0, "writes_gb": 0, "reads_gb": 0, "warnings": []}
            
        fname = str(disk_details.get("FriendlyName", "")).lower()
        is_ssd = (str(disk_details.get("MediaType", "")).upper() == "SSD") or ("ssd" in fname) or (str(disk_details.get("BusType", "")).upper() == "NVME") or (str(disk_details.get("SpindleSpeed", "")) == "0")
        if not is_ssd and any(d.get('ID') in {231, 233, 177, 179, 180, 247, 248, 160, 161, 164, 168, 169} for d in smart_data):
            is_ssd = True
        
        metrics = {}
        for d in smart_data:
            if isinstance(d['ID'], int):
                val = d.get('Raw_Int')
                if val is None:
                    try: val = int(float(str(d['Raw']).split('/')[0]))
                    except: val = 0
                
                if not is_ssd and val > 0xFFFFFFFF and d['ID'] in (1, 7, 9, 195):
                    val = (val >> 32) & 0xFFFF
                metrics[d['ID']] = val
                
                if d.get('Is_Life_Attr') or any(k in str(d.get('Name', '')).lower() for k in ['wear leveling', 'life left', 'wearout', 'remain life', 'health status']):
                    try: metrics['life_val'] = int(d['Value'])
                    except: pass
                    
            elif d.get('Name') == 'BytesWrittenTotal':
                try: metrics['bytes_w'] = int(float(str(d['Raw']).split('/')[0]))
                except: pass
            elif d.get('Name') == 'BytesReadTotal':
                try: metrics['bytes_r'] = int(float(str(d['Raw']).split('/')[0]))
                except: pass
            elif d.get('Name') in ('Wear', 'PercentageUsed'):
                try: metrics['wear'] = int(float(str(d['Raw']).split('/')[0]))
                except: pass
                
        hours, realloc, pending, starts = metrics.get(9, 0), metrics.get(5, 0), metrics.get(197, 0), metrics.get(12, 0)
        life = 100 - metrics['wear'] if 'wear' in metrics else metrics.get('life_val', 100)
        life = max(0, life)
            
        sec_size = disk_details.get('LogicalSectorSize', 512) or 512
        gb_div = 1024**3
        raw_writes, raw_reads = metrics.get(241, metrics.get(246, metrics.get(175, 0))), metrics.get(242, 0)
        
        if 'bytes_w' in metrics: 
            writes_gb, reads_gb = metrics['bytes_w'] // gb_div, metrics.get('bytes_r', 0) // gb_div
        else: 
            # Phison/SMI controllers 32MB blocks heuristic
            budget_brands = ['kingston', 'king cell', 'apacer', 'patriot', 'goodram', 'adata', 'silicon power', 'spcc', 'phison', 'smi', 'transcend', 'team', 'pny', 'netac', 'kingspec', 'goldenafir', 'gigabyte']
            if raw_writes > 50000000: 
                writes_gb, reads_gb = round((raw_writes * sec_size) / gb_div), round((raw_reads * sec_size) / gb_div)
            elif any(b in fname for b in budget_brands) or (50000 < raw_writes <= 50000000):
                writes_gb, reads_gb = round((raw_writes * 32) / 1024), round((raw_reads * 32) / 1024)
            else:
                writes_gb, reads_gb = raw_writes, raw_reads

        # Vector grading calculation to pinpoint the exact downgrade trigger
        grade_weights = {'A+': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        m_grades = {}

        if is_ssd:
            m_grades['pending'] = 'D' if pending >= 10 else ('C' if pending > 0 else 'A+')
            m_grades['realloc'] = 'D' if realloc >= 10 else ('C' if realloc > 0 else 'A+')
            m_grades['hours'] = 'D' if hours >= 50000 else ('C' if hours >= 35000 else ('B' if hours >= 25000 else ('A' if hours >= 20000 else 'A+')))
            m_grades['starts'] = 'D' if starts >= 20000 else ('C' if starts >= 10000 else ('B' if starts >= 5000 else ('A' if starts >= 3000 else 'A+')))
            m_grades['health_pct'] = 'D' if life < 10 else ('C' if life < 50 else ('B' if life < 75 else ('A' if life < 95 else 'A+')))
            m_grades['writes_gb'] = 'D' if writes_gb >= 150000 else ('C' if writes_gb >= 100000 else ('B' if writes_gb >= 50000 else ('A' if writes_gb >= 20000 else 'A+')))
            m_grades['reads_gb'] = 'D' if reads_gb >= 200000 else ('C' if reads_gb >= 120000 else ('B' if reads_gb >= 70000 else ('A' if reads_gb >= 30000 else 'A+')))
        else:
            m_grades['pending'] = 'D' if pending >= 10 else ('C' if pending > 0 else 'A+')
            m_grades['realloc'] = 'D' if realloc >= 2000 else ('C' if realloc >= 200 else ('B' if realloc >= 20 else ('A' if realloc > 0 else 'A+')))
            m_grades['hours'] = 'C' if hours >= 60000 else ('B' if hours >= 40000 else ('A' if hours >= 20000 else 'A+'))

        # Select the metric with the lowest grade weight to act as the downgrade trigger
        if m_grades:
            trigger = min(m_grades, key=lambda k: grade_weights.get(m_grades[k], 5))
            grade = m_grades[trigger]
        else:
            trigger, grade = None, 'N/A'

        warnings = []
        if metrics.get(199, 0) > 0: warnings.append(f"CRC_Err:{metrics[199]}")
        if max(metrics.get(187, 0), metrics.get(198, 0)) > 0: warnings.append(f"Uncorr:{max(metrics.get(187, 0), metrics.get(198, 0))}")
        if metrics.get(188, 0) > 0: warnings.append(f"Timeouts:{metrics[188]}")
        
        if is_ssd:
            if max(metrics.get(174, 0), metrics.get(192, 0)) > 20: warnings.append(f"PwrLoss:{max(metrics.get(174, 0), metrics.get(192, 0))}")
            if max(metrics.get(171, 0), metrics.get(181, 0)) > 0: warnings.append(f"ProgFail:{max(metrics.get(171, 0), metrics.get(181, 0))}")
            if max(metrics.get(172, 0), metrics.get(182, 0)) > 0: warnings.append(f"ErsFail:{max(metrics.get(172, 0), metrics.get(182, 0))}")
        else:
            if metrics.get(191, 0) > 0: warnings.append(f"GShock:{metrics[191]}")
            if metrics.get(10, 0) > 0: warnings.append(f"SpinRtry:{metrics[10]}")
            
        return {
            "grade": grade, "trigger": trigger if grade != 'A+' else None,
            "hours": hours, "health_pct": life if is_ssd else 100,
            "realloc": realloc, "pending": pending, "starts": starts,
            "writes_gb": writes_gb, "reads_gb": reads_gb, "warnings": warnings, "is_ssd": is_ssd
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