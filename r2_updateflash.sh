#!/bin/bash

if [ -f "./3_flashupdate/memx_usb_update_flash_tool" ]; then
   echo "run usb updateflash tool: please put formal fw to 3_flashupdate/cascade.bin"
   sudo ./3_flashupdate/memx_usb_update_flash_tool -flash ./3_flashupdate/cascade.bin
   echo "please perform DUT power cycle to activate new firmware image"
else
   echo "run pcie updateflash tool: please put formal fw to 3_flashupdate/cascade.bin"
   sudo ./3_flashupdate/pcieupdateflash -f ./3_flashupdate/cascade.bin
   echo "please reboot host to activate new firmware image"
fi
