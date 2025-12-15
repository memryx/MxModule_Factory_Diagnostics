# Factory Diagnostic Test Guide

This repository contains the **factory diagnostic test program** and associated **test patterns**.
The intended manufacturing workflow assumes the DUT’s flash is initially empty and proceeds as follows:

1. Boot the DUT using **PCIe or USB boot**.
2. Run the **diagnostic test suite**.
3. Program the **formal release firmware** into flash.
4. Switch the DUT back to **flash boot**.
5. Run a real AI model to validate final functional correctness.

---

## Host Preparation

### 1. Remove SDK `memx-drivers` (if previously installed)

```
sudo apt remove memx-drivers
sudo rmmod memx_cascade_plus_pcie

```

### 2. Prepare the environment and build kernel/user drivers

Navigate to the repo directory:

```
cd MxModule_Factory_Diagnostics/
```

Run the appropriate environment script:

**PCIe host interface**

```
./environment_prepare_pcie.sh
```

<details>
<summary>Sample output from environment_prepare_pcie.sh</summary>

```
[2025-12-15 15:36:30] [INFO] Working directory: /home/memryx/MxModule_Factory_Diagnostics
[2025-12-15 15:36:30] [INFO] Build log: /home/memryx/MxModule_Factory_Diagnostics/preparation_logs/prepare_20251215_153630.log
[2025-12-15 15:36:30] [INFO] Mode: QUIET
[2025-12-15 15:36:30] [INFO] Detected architecture: x86_64

[15:36:30] ▶ Firmware
[2025-12-15 15:36:30] [INFO] Copying diagnostics firmware to /lib/firmware/cascade.bin
[2025-12-15 15:36:30] [INFO] SUDO: cp ./0_fwimage/cascade_diag.bin /lib/firmware/cascade.bin 

[15:36:30] ▶ Cleanup (best-effort)
[2025-12-15 15:36:30] [INFO] Removing memx-drivers (best-effort)
[2025-12-15 15:36:30] [INFO] SUDO: apt remove -y memx-drivers 
[2025-12-15 15:36:31] [INFO] Unloading kernel module memx_cascade_plus_pcie (best-effort)
[2025-12-15 15:36:31] [WARN] Kernel module memx_cascade_plus_pcie not loaded; skipping rmmod

[15:36:31] ▶ Kernel Driver (pcie)
[2025-12-15 15:36:31] [INFO] Building kernel driver (pcie)
[2025-12-15 15:36:31] [INFO] MAKE: make clean 
[2025-12-15 15:36:31] [INFO] MAKE: make all 
[2025-12-15 15:36:35] [INFO] RUN: cp ./memx_cascade_plus_pcie.ko ../memx_cascade_plus.ko 
[2025-12-15 15:36:35] [INFO] MAKE: make clean 

[15:36:35] ▶ System Paths
[2025-12-15 15:36:35] [INFO] Ensuring /usr/include/memx exists
[2025-12-15 15:36:35] [INFO] SUDO: mkdir -p /usr/include/memx 
[2025-12-15 15:36:35] [INFO] Removing old flash tool directory (if present)
[2025-12-15 15:36:35] [INFO] RUN: rm -rf ./3_flashupdate/memx_usb_update_flash_tool 

[15:36:35] ▶ User Libraries & Tools (x86_64)
[2025-12-15 15:36:35] [INFO] Configuring for x86_64
[2025-12-15 15:36:35] [INFO] SUDO: cp ./2_udrv_lib/x86_64/libmemx.so /usr/lib/ 
[2025-12-15 15:36:35] [INFO] SUDO: cp ./2_udrv_lib/x86_64/memx.h /usr/include/memx/ 
[2025-12-15 15:36:35] [INFO] RUN: cp -f ./3_flashupdate/x86_64/pcieupdateflash ./3_flashupdate/pcieupdateflash 
[2025-12-15 15:36:35] [INFO] RUN: cp -f ./3_flashupdate/x86_64/read_fwver ./3_flashupdate/read_fwver 
[2025-12-15 15:36:35] [INFO] RUN: cp -f ./3_flashupdate/x86_64/check_version ./3_flashupdate/check_version 

[15:36:35] ▶ Python Module
[2025-12-15 15:36:35] [INFO] Building pymodule
[2025-12-15 15:36:35] [INFO] MAKE: make clean 
[2025-12-15 15:36:35] [INFO] MAKE: make all 
[2025-12-15 15:36:36] [INFO] RUN: cp -r ./bin/mxa.cpython-312-x86_64-linux-gnu.so ../../4_testsuit/ 
[2025-12-15 15:36:36] [INFO] MAKE: make clean 

[15:36:36] ▶ Done
[2025-12-15 15:36:36] [INFO] Preparation is done.
[2025-12-15 15:36:36] [INFO] Full log: /home/memryx/MxModule_Factory_Diagnostics/preparation_logs/prepare_20251215_153630.log


```

</details>


**USB host interface**

```
./environment_prepare_usb.sh
```

### 3. Firmware Prerequisite

Place the **latest public SDK release firmware image** in the path below.  
The latest firmware files are available in the following repository: [MX3 Driver Public Repo](https://github.com/memryx/mx3_driver_pub/tree/release/firmware)

> **Note:** Select the correct module firmware file for the build line (e.g., `cascade_4chips_flash.bin` or `cascade_2chips_flash.bin`), then copy it as `cascade.bin`.
```
MxModule_Factory_Diagnostics/3_flashupdate/cascade.bin
```

### WARNING

Ensure the firmware image corresponds to the correct release version.
Incorrect firmware may render devices non-functional.

### 4. Third-party lib install

Install pandas lib as a prerequisite to run the ral model inference test (`./r3_4chip.sh` or `./r3_2chip.sh`)

```
sudo apt-get install python3-pandas
```

---

## Step 1: Load Kernel Driver and Boot DUT via PCIe/USB

**Condition:** Set DUT bootstrap to **PCIe** or **USB**, then reboot/power-cycle DUT.

**Action:**

```
./r0_load.sh
```

This script loads the kernel driver and boots the DUT using the diagnostic firmware image provided in the 0_fwimage folder, enabling the DUT to enter diagnostic mode.

---

## Step 2: Run Diagnostic Tests

**Action:**

```
./r1_Diag.sh
```
The script runs a series of tests to verify multiple system functions and to ensure there are no electrical or soldering defects in the module.

<details>
<summary>Diagnostic output includes entries such as:</summary>

```
[70363.072064] memryx: memx_init: pcie init success, char major Id(234)
[70377.160994] =============CHIP(0) WP(443) RP(0) Total(443)=============
[70377.160998] memx7 <<pass_7>>
[70377.160999] memx10 <<pass_10>>
[70377.161000] memx0 <<pass_0>>
[70377.161000] memx1 <<pass_1>>
[70377.161000] memx2 <<pass_2>>
[70377.161001] memx3 <<pass_3>>
[70377.161001] memx4 <<pass_4>>
[70377.161001] memx5 <<pass_5>>
[70377.161002] PMIC Output Voltage      (700)mV(0x0369)
[70377.161002] VOUT_MAX        (1080)mV(0x0544)
[70377.161003] VOUT_MARGIN_HIGH(1080)mV(0x0543)
[70377.161003] VOUT_MARGIN_LOW (600)mV(0x02EC)
[70377.161004] 0x43FF 0x14C5 0x0824 0x03F0 0x25CF
[70377.161004] 0x0E90 0x0008 0x0000 0x5449
[70377.161004] Power = 4429 mW
[70377.161005] memx6 <<pass_6>>
[70377.161005] memx8 <<pass_8>>
[70377.161005] memx9 <<pass_9>>
[70377.161006] ============================================================
[70377.161007] memryx: fs_cmd_handler: dump of chip_id(0)'s fw_log success

```
</details>

### Diagnostic Test Item Summary

| Test ID | Description                           |
| ------- | ------------------------------------- |
| memx0   | CPU Test                              |
| memx1   | SRAM Read/Write                       |
| memx2   | MPU IO                                |
| memx3   | Watchdog Timer (WDT)                  |
| memx4   | Timer                                 |
| memx5   | DMA                                   |
| memx6   | PMIC                                  |
| memx7   | Chip-to-chip / Chip-to-host bandwidth |
| memx8   | MPU FMEM/WTMEM                        |
| memx9   | Flash Read/Write                      |
| memx10  | PVTS                                  |

### PASS/FAIL Rule

* **`memx9 <<pass_9>>` is the final PASS indicator.**
* Any earlier failure **aborts** the test flow.

### WARNING

Do **not** proceed to flash programming if any diagnostic fails.

---

## Step 3: Program Formal Firmware Image to Flash

**Action:**

```
./r2_updateflash.sh
```

This script writes the latest production firmware image into the DUT’s flash module. 
The flash module is still expected to be blank at this stage of the manufacturing process (For rework units, flash may not be empty, but this does not affect programming).

Successful output ends with:

```
ALL X Devices FLASH IMAGE upgrade OK
```

<details>
<summary> Sample output of flash update tool </summary>

```
########## Memryx Flash UpdateTool - Directed (V1.6) ###############
0000:01:00.0 vendor=1fe9 device=0100 class=1200 irq=0 (pin 1) base0=84000004 (Device 0100)
****Found 1 MemryX Devices.****

(DEICE1): Start Update Flash----
BAR0: Base Address: 0x0000000084000000  Size=0x01000000
BAR1: Base Address: 0x0000000000000000  Size=0x00000000
BAR2: Base Address: 0x0000000085000000  Size=0x01000000
BAR3: Base Address: 0x0000000000000000  Size=0x00000000
BAR4: Base Address: 0x0000000086000000  Size=0x00100000
BAR5: Base Address: 0x0000000000000000  Size=0x00000000
Image size is: 0x1f7e8
Update Flash OK
NewVer=0x6A1800D1 Date=0x68DC9500 MODEL=0x00043358

##########################################################
*****************ALL 1 Devices FLASH IMAGE upgrade OK
##########################################################

```
</details>


### NOTE

Firmware revision displayed at completion must match the formal release version.

---

## Step 4: Reboot DUT to Activate New Firmware

**Condition:** Switch DUT bootstrap back to **FLASH boot**.

**Actions:**

**PCIe host:**

```
sudo reboot
```

**USB host:**
Perform a **DUT power cycle** (host reboot not required).

---

## Step 5: Load Kernel Driver and Run Real Model Test

**4-chip product:**

```
./r0_load.sh; ./r3_4chip.sh
```

**2-chip product:**

```
./r0_load.sh; ./r3_2chip.sh
```

A typical output:

```
model_explorer_yolov8l-cls_local_model , PASS, 168.685
```

<details>
<summary>Full sample output:</summary>

```
10-02 11:02:39: Running model_explorer_yolov8l-cls_local_model...
model_explorer_yolov8l-cls_local_model                          , PASS, 168.685

log/performance_result.csv
log/performance_golden.csv
log/performance_compare.csv
10-02 11:02:42: Test Finished
```
</details>


**Results are saved to:**

```
./log/performance_result.csv
```

### Performance PASS Rule

Uses **80% of nominal FPS** as the PASS threshold.

Example:

```
Normal FPS = 168
Pass threshold = 168 × 0.8 = 134 FPS
```

---

## Step 6: Verify Flash Image Version

**Action:**

```
cat /proc/memx0/verinfo
```

Sample output:

```
pcie intf device:
SDK version: 2.0
kdriver version: 1.3.4
FW_CommitID=0x12345678 DateCode=0x87654321
ManufacturerID=0xe30a340700000094
Cold+Warm-RebootCnt=1  Warm-RebootCnt=0
BootMode=QSPI  Chip=A1
```

Verify the following:

* `FW_CommitID` and `DateCode` match the formal release image.
* `BootMode=QSPI`

### WARNING

If BootMode is not **QSPI**, the firmware may not be booting from flash correctly.

---

## Step 7: Troubleshooting

| Issue                    | Resolution                                 |
| ------------------------ | ------------------------------------------ |
| `crc32` not found        | `sudo apt-get install libarchive-zip-perl` |
| `libpci.so` missing      | `sudo apt-get install libpci-dev`          |
| USB mode requires libusb | `sudo apt install -y libusb-1.0-0-dev`     |

---

## Additional Notes and Warnings

### NOTES

* Ensure kernel headers match the running kernel version before driver build.
* Confirm `cascade.bin` is placed in the correct directory before running the flash update tool.

### WARNINGS

* **Do not interrupt flash programming**—this can permanently corrupt DUT flash.
* Ensure the DUT bootstrap mode is correct at each stage.
* Using mismatched kernel drivers may prevent DUT enumeration and initialization.
