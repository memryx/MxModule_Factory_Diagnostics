# #!/bin/bash
# sudo insmod ./1_kdrv_src/memx_cascade_plus.ko g_drv_fs_type=1 fs_debug_en=1


#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ts() { date +"%Y-%m-%d %H:%M:%S"; }
log() { printf "[%s] [%s] %s\n" "$(ts)" "$1" "$2"; }
info(){ log "INFO" "$*"; }
err() { log "ERROR" "$*" >&2; }

on_err() {
  local rc=$?
  err "FAILED: load driver (exit=${rc})"
  exit "$rc"
}
trap on_err ERR

MODULE="./1_kdrv_src/memx_cascade_plus.ko"
PARAMS=(g_drv_fs_type=1 fs_debug_en=1)

info "STEP: load kernel module"
[[ -f "$MODULE" ]] || { err "Missing module: $MODULE"; exit 2; }

# Optional: avoid confusing failure if already loaded (factory operators hit 'run' twice)
if lsmod | awk '{print $1}' | grep -qx "memx_cascade_plus"; then
  err "Module already loaded: memx_cascade_plus (unload first or reboot)"
  exit 3
fi

info "RUN: sudo insmod ${MODULE} ${PARAMS[*]}"
sudo insmod "$MODULE" "${PARAMS[@]}"

info "PASS: driver loaded"
