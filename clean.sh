# #!/bin/bash
# rm -rf ./1_kdrv_src/memx_cascade_plus.ko
# rm -rf ./1_kdrv_src/pymodule/bin
# rm -rf ./1_kdrv_src/pymodule/build
# rm -rf ./3_flashupdate/memx_usb_update_flash_tool
# rm -rf ./3_flashupdate/check_version
# rm -rf ./3_flashupdate/pcieupdateflash
# rm -rf ./3_flashupdate/read_fwver
# rm -rf ./4_testsuit/*.so



#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

# ----------------- logging -----------------
ts() { date +"%Y-%m-%d %H:%M:%S"; }
ts_short() { date +%H:%M:%S; }

log() { printf "[%s] [%s] %s\n" "$(ts)" "$1" "$2"; }
info(){ log "INFO" "$*"; }
warn(){ log "WARN" "$*"; }
err() { log "ERROR" "$*" >&2; }

# Print commands as one line, safely quoted
cmd_str() { printf '%q ' "$@"; }

# Section header
section() { printf "\n[%s] ▶ %s\n" "$(ts_short)" "$1"; }

# ----------------- helpers -----------------
rm_safe() {
  info "REMOVE: $(cmd_str rm -rf "$@")"
  rm -rf "$@"
}

# ----------------- start -----------------
section "Cleanup Build Artifacts"

rm_safe "./1_kdrv_src/memx_cascade_plus.ko"

rm_safe "./1_kdrv_src/pymodule/bin"
rm_safe "./1_kdrv_src/pymodule/build"

rm_safe "./3_flashupdate/memx_usb_update_flash_tool"
rm_safe "./3_flashupdate/check_version"
rm_safe "./3_flashupdate/pcieupdateflash"
rm_safe "./3_flashupdate/read_fwver"

rm_safe "./4_testsuit/"*.so

section "Done"
info "Cleanup completed successfully."
