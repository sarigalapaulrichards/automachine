"""
main.py
Universal Automachine Entry Point with Dynamic USB Phone Identification & Adaptive Padding.

When a phone is connected through USB debugging:
1. Detects and identifies the phone (Brand, Model, OS, UDID, Resolution, Density).
2. Computes the phone's exact padding (Top Status Bar, Bottom Navigation Bar, Usable Viewport).
3. Automatically calibrates all touch coordinates and UI offsets according to that phone.
4. Executes the Curapod-M automachine suite seamlessly.
"""

import os
import sys
import argparse
import subprocess
import time

# Ensure workspace root is in python path
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from device_manager import (
    get_active_device,
    list_all_connected_devices,
    detect_device_profile,
    DeviceProfile
)


def print_banner(profile: DeviceProfile):
    print("\n" + "=" * 80)
    print("      CURAPOD-M MOBILE AUTOMACHINE - ADAPTIVE MULTI-DEVICE RUNNER")
    print("=" * 80)
    print(f"  [DEVICE IDENTIFIED VIA USB DEBUGGING]")
    print(f"    Phone Model      : {profile.display_name} ({profile.manufacturer})")
    print(f"    Device UDID      : {profile.udid}")
    print(f"    Android Release  : Version {profile.android_version} (API Level {profile.sdk_version})")
    print(f"    Display Size     : {profile.width} x {profile.height} @ {profile.density} dpi")
    print(f"    Top Padding      : {profile.top_padding} px (Status Bar / Display Notch)")
    print(f"    Bottom Padding   : {profile.bottom_padding} px (System Navigation / Gesture Bar)")
    print(f"    Usable Viewport  : {profile.usable_width} x {profile.usable_height} px")
    print(f"    Calibrated Scale : X={profile.scale_x:.3f} | Y={profile.scale_y:.3f} | DPI={profile.scale_dpi:.3f}")
    print(f"    Assigned Ports   : Appium Port {profile.appium_port} | SystemPort {profile.system_port}")
    print("=" * 80 + "\n", flush=True)


def run_automachine_on_device(profile: DeviceProfile, extra_args=None):
    """
    Sets up the device environment and executes the Curapod-M automachine suite.
    """
    print_banner(profile)

    env = os.environ.copy()
    env["DEVICE_UDID"] = profile.udid
    env["SYSTEM_PORT"] = str(profile.system_port)
    env["APPIUM_PORT"] = str(profile.appium_port)
    env["APPIUM_HOST"] = f"http://127.0.0.1:{profile.appium_port}"
    env["PYTHONUNBUFFERED"] = "1"

    # Forward optional settings from extra_args
    if extra_args:
        if extra_args.excel:
            env["EXCEL_PATH"] = extra_args.excel
        if extra_args.row:
            env["EXCEL_ROW"] = str(extra_args.row)
        if extra_args.skip_session:
            env["SKIP_PAIN_SESSION"] = "true"

    runner_script = os.path.join(WORKSPACE_DIR, "run_excel_suite.py")

    cmd = [sys.executable, runner_script]
    if extra_args and extra_args.row:
        cmd.extend(["--row", str(extra_args.row)])
    if extra_args and extra_args.excel:
        cmd.extend(["--excel", extra_args.excel])
    if extra_args and extra_args.skip_session:
        cmd.append("--skip-session")

    print(f">>> Launching Curapod-M Automachine on {profile.display_name}...\n", flush=True)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
        cwd=WORKSPACE_DIR
    )

    for line in iter(proc.stdout.readline, ''):
        if line:
            print(line.rstrip(), flush=True)
    proc.stdout.close()
    proc.wait()

    print("\n" + "=" * 80)
    print(f"  AUTOMACHINE RUN FINISHED on {profile.display_name} (Exit Code: {proc.returncode})")
    print("=" * 80 + "\n")
    return proc.returncode


def main():
    parser = argparse.ArgumentParser(description="Universal Curapod-M Automachine Runner")
    parser.add_argument("--device", help="Target device UDID (optional, auto-detected by default)")
    parser.add_argument("--excel", help="Custom path to test Excel spreadsheet")
    parser.add_argument("--row", type=int, help="Single Excel row / iteration index to execute")
    parser.add_argument("--skip-session", action="store_true", help="Skip the 2-minute pain relief session")
    parser.add_argument("--info-only", action="store_true", help="Scan and display connected devices and paddings without running")
    parser.add_argument("--parallel", action="store_true", help="Run in parallel across all connected phones")
    args = parser.parse_args()

    connected = list_all_connected_devices()

    if not connected:
        print("\n[Error] No Android phones detected via USB debugging (ADB).")
        print("Please connect your phone via USB, enable 'USB Debugging' in Developer Options, and try again.\n")
        sys.exit(1)

    print(f"\n[USB Discovery] Found {len(connected)} phone(s) connected via USB debugging:")
    for idx, d in enumerate(connected, 1):
        print(f"  {idx}. {d.display_name} (UDID: {d.udid}, Resolution: {d.width}x{d.height}, TopPad: {d.top_padding}px, BottomPad: {d.bottom_padding}px)")

    if args.info_only:
        for d in connected:
            print_banner(d)
        return

    # If parallel flag is set and multiple devices are present
    if args.parallel and len(connected) >= 2:
        import run_parallel_phones
        run_parallel_phones.main()
        return

    # Target specific device if requested
    target_device = None
    if args.device:
        for d in connected:
            if d.udid == args.device or args.device.lower() in d.model.lower():
                target_device = d
                break
        if not target_device:
            print(f"[Error] Specified device '{args.device}' not found in connected devices.")
            sys.exit(1)
    else:
        # Default to first connected or primary device
        target_device = connected[0]

    # Run automachine on chosen device with calibrated padding
    code = run_automachine_on_device(target_device, extra_args=args)
    sys.exit(code)


if __name__ == "__main__":
    main()
