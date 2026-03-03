# DiskWiper

A robust, graphical interface for Windows disk management, diagnostics, and secure wiping.

---

## Overview

DiskWiper provides a secure and intuitive Graphical User Interface (GUI) for the native Windows `diskpart` utility. It allows system administrators, technicians, and power users to efficiently wipe, partition, and format storage drives without relying on the command-line interface.

---

## Key Features

### Dynamic Hardware Detection

- Real-time monitoring of connected storage devices
- Automatic refresh on drive insertion or removal

### S.M.A.R.T. Diagnostics & Grading

Integrated low-level health monitoring, including:

- Power-On Hours
- Reallocated Sectors
- Wear Leveling
- Total Bytes Written (TBW)

Assigns an overall drive health grade from A+ to D.

### Automated Wipe Sequence

Executes a fully unattended cleaning process with a single click:

1. Cleans the existing disk signature and partition table
2. Creates a new primary partition
3. Performs a quick format (NTFS, FAT32, or exFAT)
4. Automatically assigns an available drive letter

### Failsafe Mechanisms

- The primary system drive (Disk 0) is restricted by default
- Prevents accidental destruction of the operating system partition

### Inventory Reporting

- Generates scannable QR codes
- Includes Serial Number, Model, and health metrics
- Designed for streamlined inventory management

### Persistent Configuration

- Automatically saves and restores UI preferences
- USB visibility mode
- Extended metadata mode

---

## Usage Guide

### 1. Identify the Target Drive

Locate the designated drive in the inventory list and carefully verify:

- Capacity
- Filesystem
- Friendly Name
- Serial Number

### 2. Select the Drive

- Use the corresponding checkbox
- Bulk selection is supported for multi-drive operations

### 3. Execute

- Click the WIPE button
- Review the security prompt
- Explicitly confirm the destructive action

### 4. Completion

Monitor the execution log. Once the following message appears:

```
[OK] Disk wipe completed successfully
```

The drive is provisioned and ready for use.

---

## Building from Source

### Prerequisites

- Python 3.x installed
- Python added to system PATH

### Dependencies

Install required packages:

```bash
pip install customtkinter pyinstaller pillow qrcode
```

### Compilation

Generate a portable folder build with embedded UAC administrator manifest:

```bash
pyinstaller --noconfirm --onedir --windowed --uac-admin --collect-all "customtkinter" --name "DiskWiper" main.py
```

If you prefer a single executable file:

```bash
pyinstaller --noconfirm --onefile --windowed --uac-admin --collect-all "customtkinter" --name "DiskWiper" main.py
```

Note: Using `--onefile` may increase startup time slightly.

---

## Technical Specifications

| Component    | Technology / Detail |
|-------------|---------------------|
| Core Engine | Python 3, Windows PowerShell, native `diskpart` |
| Interface   | CustomTkinter (Modern Dark UI) |
| Architecture| Asynchronous multi-threading (non-blocking UI and monitoring) |
| Permissions | Requires elevated Administrator privileges (UAC) |

---

## Security Warning

CRITICAL:

This software performs irreversible, destructive operations.

Executing a wipe command will result in permanent loss of all data on the selected storage device.

Always double-check your selection before proceeding.

---

## License

This project is distributed under the GNU GPL v3 License.

See the `LICENSE` file for full terms and conditions.