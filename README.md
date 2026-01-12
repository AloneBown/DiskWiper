# 🧹 DiskWiper v1.0  
---

## 🎯 Purpose

**DiskWiper** provides a safe and intuitive graphical interface for the Windows `diskpart` utility, allowing users to quickly **wipe, partition, and format drives** without using the command line.

---

## ✨ Key Features

### 🔍 Automatic Disk Detection
Real-time monitoring of connected hardware.  
The disk list updates automatically when you plug in or remove a drive.
You can also use **Refresh** button for manual update.

### 🛡️ Safe Selection
By default, the system drive (**Disk 0**) is hidden to prevent accidental data loss on your OS partition.

### 📊 Extended Drive Metadata
Toggle **Extended Info** to view:
- Number of volumes  
- Operational status  
- Allocated space  

### ⚡ One-Click Wipe Process
Performs a fully automated cleaning sequence:
1. Cleans the disk signature  
2. Creates a new primary partition  
3. Performs a quick **NTFS** format  
4. Assigns a drive letter  

### 💾 Persistent Configuration
Remembers your view preferences (**Show USB**, **Extended Info**) across sessions.

---

## 📖 How to Use

Follow these steps to safely clean your storage devices:

1. **Identify Your Disk**  
   Locate the target drive in the list.  
   Double-check the **size** and **friendly name**.

2. **Select**  
   - Click the checkbox next to the disk(s) you wish to wipe  
   - Or use the master checkbox for bulk selection

3. **Confirm**  
   Click the **WIPE** button and confirm the destructive action.

4. **Done**  
   Once the log shows:  --- OPERATIONS FINISHED ---, your drive is ready to use.

---
## 🛠 Building from Source

To build **DiskWiper** as a portable executable, make sure **Python 3** is installed on your system, then follow these steps:

---

### 📦 Install Dependencies

Install the required Python packages:

```bash
pip install customtkinter
pip install pyinstaller
```

### 🏗 Build the Project

Use the following command to generate a portable folder build with an embedded administrator (UAC) manifest:
```bash
pyinstaller --noconfirm --onedir --windowed --uac-admin --collect-all "customtkinter" --name "DiskWiper" main.py
```
## 🛠 Technical Details

| Component     | Technology                                   |
|---------------|----------------------------------------------|
| Engine        | Python 3 + Windows PowerShell + Diskpart     |
| Interface     | Modern Dark UI via CustomTkinter             |
| Architecture | Multi-threaded (Monitoring & Processing)     |
| Privileges   | Requires Elevated Administrator Rights       |

---

## 📜 License

This project is licensed under the **GNU GPL v3**.  
See `LICENSE` for details.

---

## ⚠️ Warning

### ❗ EXTREME CAUTION REQUIRED

This software performs **destructive operations**.  
Wiping a disk will result in the **permanent loss of all data** on that device.

**Always double-check your selection before clicking _WIPE_.**