#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

# ----------------- config / flags -----------------
VERBOSE=0

usage() {
  cat <<'EOF'
Usage: ./environment_prepare_pcie.sh [--verbose|-v]

Default (quiet): make output is suppressed (logged to file only). On failure, prints the last 60 lines.
Verbose:         make output is shown live (and logged).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--verbose) VERBOSE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

# ----------------- logging -----------------
ts()  { date +"%Y-%m-%d %H:%M:%S"; }
ts_short() { date +%H:%M:%S; }

log() { printf "[%s] [%s] %s\n" "$(ts)" "$1" "$2"; }
info(){ log "INFO" "$*"; }
warn(){ log "WARN" "$*"; }
err() { log "ERROR" "$*" >&2; }

# Print commands as one line, safely quoted
cmd_str() { printf '%q ' "$@"; }

# Section header (stdout)
section() { printf "\n[%s] ▶ %s\n" "$(ts_short)" "$1"; }

ROOT_DIR="$(pwd)"
LOG_DIR="${ROOT_DIR}/preparation_logs"
mkdir -p "$LOG_DIR"
BUILD_LOG="${LOG_DIR}/prepare_$(date +%Y%m%d_%H%M%S).log"

info "Working directory: ${ROOT_DIR}"
info "Build log: ${BUILD_LOG}"
info "Mode: $([[ $VERBOSE -eq 1 ]] && echo 'VERBOSE' || echo 'QUIET')"

# ----------------- error reporting -----------------
on_err() {
  local exit_code=$?
  local line_no=${BASH_LINENO[0]:-?}
  local cmd=${BASH_COMMAND:-?}
  err "Command failed (exit=${exit_code}) at line ${line_no}: ${cmd}"
  err "See log: ${BUILD_LOG}"
  exit "$exit_code"
}
trap on_err ERR

# ----------------- helpers -----------------
require_file() {
  [[ -f "$1" ]] || { err "Missing required file: $1"; exit 2; }
}
require_dir() {
  [[ -d "$1" ]] || { err "Missing required directory: $1"; exit 2; }
}

run() {
  info "RUN: $(cmd_str "$@")"
  "$@" 2>&1 | tee -a "$BUILD_LOG"
  local rc=${PIPESTATUS[0]}
  [[ $rc -eq 0 ]] || exit "$rc"
}

sudo_run() {
  info "SUDO: $(cmd_str "$@")"
  sudo "$@" 2>&1 | tee -a "$BUILD_LOG"
  local rc=${PIPESTATUS[0]}
  [[ $rc -eq 0 ]] || exit "$rc"
}

run_make() {
  info "MAKE: $(cmd_str "$@")"

  if [[ $VERBOSE -eq 1 ]]; then
    "$@" 2>&1 | tee -a "$BUILD_LOG"
    local rc=${PIPESTATUS[0]}
    [[ $rc -eq 0 ]] || exit "$rc"
  else
    if ! "$@" >>"$BUILD_LOG" 2>&1; then
      local rc=$?
      err "Make failed (exit=${rc}): $(cmd_str "$@")"
      err "Last 60 log lines:"
      tail -n 60 "$BUILD_LOG" >&2 || true
      exit "$rc"
    fi
  fi
}

# ----------------- start -----------------
# Ensure running from repo root (adjust this check if needed)
require_dir "./1_kdrv_src"
require_dir "./4_testsuit"

arch="$(uname -m)"
info "Detected architecture: ${arch}"

# Sanity checks
require_file "./0_fwimage/cascade_diag.bin"
require_dir  "./1_kdrv_src/pcie"
require_dir  "./1_kdrv_src/pymodule"
require_dir  "./2_udrv_lib"
require_dir  "./3_flashupdate"

# 1) Copy diagnostics firmware
section "Firmware"
info "Copying diagnostics firmware to /lib/firmware/cascade.bin"
sudo_run cp "./0_fwimage/cascade_diag.bin" "/lib/firmware/cascade.bin"

# 2) Remove prior installation + unload module (best-effort)
section "Cleanup (best-effort)"
info "Removing memx-drivers (best-effort)"
if dpkg -s memx-drivers >/dev/null 2>&1; then
  # Silence apt output to console; keep it in the log
  info "SUDO: $(cmd_str apt remove -y memx-drivers)"
  sudo apt remove -y memx-drivers >>"$BUILD_LOG" 2>&1 || true
else
  warn "memx-drivers not installed; skipping"
fi

info "Unloading kernel module memx_cascade_plus_pcie (best-effort)"
if lsmod | awk '{print $1}' | grep -qx "memx_cascade_plus_pcie"; then
  sudo_run rmmod memx_cascade_plus_pcie
else
  warn "Kernel module memx_cascade_plus_pcie not loaded; skipping rmmod"
fi

# 3) Build kernel driver
section "Kernel Driver (pcie)"
info "Building kernel driver (pcie)"
require_file "./1_kdrv_src/pcie/Makefile"

pushd "./1_kdrv_src/pcie" >/dev/null
run_make make clean
run_make make all
require_file "./memx_cascade_plus_pcie.ko"
run cp "./memx_cascade_plus_pcie.ko" "../memx_cascade_plus.ko"
run_make make clean
popd >/dev/null

# 4) Prepare include dir and clean old tool
section "System Paths"
info "Ensuring /usr/include/memx exists"
sudo_run mkdir -p "/usr/include/memx"

info "Removing old flash tool directory (if present)"
run rm -rf "./3_flashupdate/memx_usb_update_flash_tool"

# 5) Install user driver lib + headers + arch tools
section "User Libraries & Tools (${arch})"
case "$arch" in
  x86_64)
    info "Configuring for x86_64"
    require_file "./2_udrv_lib/x86_64/libmemx.so"
    require_file "./2_udrv_lib/x86_64/memx.h"
    require_file "./3_flashupdate/x86_64/pcieupdateflash"
    require_file "./3_flashupdate/x86_64/read_fwver"
    require_file "./3_flashupdate/x86_64/check_version"

    sudo_run cp "./2_udrv_lib/x86_64/libmemx.so" "/usr/lib/"
    sudo_run cp "./2_udrv_lib/x86_64/memx.h" "/usr/include/memx/"
    run cp -f "./3_flashupdate/x86_64/pcieupdateflash" "./3_flashupdate/pcieupdateflash"
    run cp -f "./3_flashupdate/x86_64/read_fwver"      "./3_flashupdate/read_fwver"
    run cp -f "./3_flashupdate/x86_64/check_version"   "./3_flashupdate/check_version"
    ;;

  aarch64)
    info "Configuring for aarch64"
    require_file "./2_udrv_lib/aarch64/libmemx.so"
    require_file "./2_udrv_lib/aarch64/memx.h"
    require_file "./3_flashupdate/aarch64/pcieupdateflash"
    require_file "./3_flashupdate/aarch64/read_fwver"
    require_file "./3_flashupdate/aarch64/check_version"

    sudo_run cp "./2_udrv_lib/aarch64/libmemx.so" "/usr/lib/"
    sudo_run cp "./2_udrv_lib/aarch64/memx.h" "/usr/include/memx/"
    run cp -f "./3_flashupdate/aarch64/pcieupdateflash" "./3_flashupdate/pcieupdateflash"
    run cp -f "./3_flashupdate/aarch64/read_fwver"      "./3_flashupdate/read_fwver"
    run cp -f "./3_flashupdate/aarch64/check_version"   "./3_flashupdate/check_version"
    ;;

  *)
    err "Unknown/unsupported architecture: ${arch}"
    exit 3
    ;;
esac

# 6) Build pymodule
section "Python Module"
info "Building pymodule"
pushd "./1_kdrv_src/pymodule" >/dev/null
run_make make clean
run_make make all
require_dir "./bin"
run cp -r ./bin/* "../../4_testsuit/"
run_make make clean
popd >/dev/null

section "Done"
info "Preparation is done."
info "Full log: ${BUILD_LOG}"
