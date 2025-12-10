#!/bin/bash

arch=$(uname -m)

sudo cp ./0_fwimage/cascade_diag.bin /lib/firmware/cascade.bin
cd 1_kdrv_src/pcie; make clean; make all;cp memx_cascade_plus_pcie.ko ../memx_cascade_plus.ko;make clean; cd ../..
mkdir -p /usr/include/memx
rm -rf ./3_flashupdate/memx_usb_update_flash_tool

if [ "$arch" = "x86_64" ]; then
    sudo cp ./2_udrv_lib/x86_64/libmemx.so /usr/lib/
    sudo cp ./2_udrv_lib/x86_64/memx.h /usr/include/memx/
    cp -rf ./3_flashupdate/x86_64/pcieupdateflash ./3_flashupdate/pcieupdateflash
    cp -rf ./3_flashupdate/x86_64/read_fwver ./3_flashupdate/read_fwver
    cp -rf ./3_flashupdate/x86_64/check_version ./3_flashupdate/check_version
	echo "This system is x86_64 system. Preparation is done."
elif [ "$arch" = "aarch64" ]; then
    sudo cp ./2_udrv_lib/aarch64/libmemx.so /usr/lib/
    sudo cp ./2_udrv_lib/aarch64/memx.h /usr/include/memx/
    cp -rf ./3_flashupdate/aarch64/pcieupdateflash ./3_flashupdate/pcieupdateflash
    cp -rf ./3_flashupdate/aarch64/read_fwver ./3_flashupdate/read_fwver
    cp -rf ./3_flashupdate/aarch64/check_version ./3_flashupdate/check_version
	echo "This system is aarch64 system. Preparation is done."
else
    echo "Unknown architecture: $arch"
fi
