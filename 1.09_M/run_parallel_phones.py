"""
Multi-Device Parallel Test Runner for Curapod-M Automated Testing
Executes pytest across two connected Android devices simultaneously in real-time.
"""

import subprocess
import threading
import sys
import os

def get_connected_devices():
    try:
        out = subprocess.check_output(["adb", "devices", "-l"], text=True)
        lines = out.strip().splitlines()[1:]
        devices = []
        for line in lines:
            line = line.strip()
            if not line or "offline" in line:
                continue
            parts = line.split()
            udid = parts[0]
            model = "Android Device"
            for p in parts[1:]:
                if p.startswith("model:"):
                    model = p.split("model:")[1]
            devices.append({"udid": udid, "model": model})
        return devices
    except Exception as e:
        print(f"[Error] Failed to query adb devices: {e}")
        return []

def stream_process_output(pipe, prefix):
    for line in iter(pipe.readline, ''):
        if line:
            print(f"{prefix} {line.rstrip()}", flush=True)
    pipe.close()

def run_device_test(device_info, system_port, tag):
    udid = device_info["udid"]
    model = device_info["model"]
    prefix = f"[{tag} | {model}]"

    print(f"\n>>> Starting Test on {prefix} (UDID: {udid}, SystemPort: {system_port})...\n", flush=True)

    env = os.environ.copy()
    env["DEVICE_UDID"] = udid
    env["SYSTEM_PORT"] = str(system_port)
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        r"D:\automachine\test\test_pain_tracking.py",
        "-v",
        "-s"
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
        cwd=r"D:\automachine"
    )

    stream_process_output(proc.stdout, prefix)
    proc.wait()
    return proc.returncode

def main():
    print("=" * 80)
    print("  CURAPOD-M MULTI-DEVICE PARALLEL TEST RUNNER")
    print("=" * 80)

    devices = get_connected_devices()
    print(f"Detected {len(devices)} device(s) via ADB:\n")
    for i, dev in enumerate(devices, 1):
        print(f"  {i}. Model: {dev['model']} (UDID: {dev['udid']})")
    print("-" * 80)

    if len(devices) == 0:
        print("[Error] No Android devices detected via ADB. Connect devices and enable USB Debugging.")
        sys.exit(1)

    if len(devices) == 1:
        print("[Note] Only 1 phone connected right now. Connect a 2nd phone via USB to run both simultaneously.")
        print(f"Running test on single connected phone: {devices[0]['model']} ({devices[0]['udid']})\n")
        run_device_test(devices[0], 8200, "PHONE 1")
        return

    # Two or more devices connected: launch parallel execution!
    dev1 = devices[0]
    dev2 = devices[1]

    print(f"Ready to run in parallel on 2 devices simultaneously:")
    print(f"  - Phone 1: {dev1['model']} (UDID: {dev1['udid']}, SystemPort: 8200)")
    print(f"  - Phone 2: {dev2['model']} (UDID: {dev2['udid']}, SystemPort: 8201)")
    print("=" * 80 + "\n")

    results = {}

    def worker1():
        results["Phone 1"] = run_device_test(dev1, 8200, "PHONE 1")

    def worker2():
        results["Phone 2"] = run_device_test(dev2, 8201, "PHONE 2")

    t1 = threading.Thread(target=worker1)
    t2 = threading.Thread(target=worker2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print("\n" + "=" * 80)
    print("  MULTI-DEVICE EXECUTION COMPLETED")
    print("=" * 80)
    for dev_tag, code in results.items():
        st = "SUCCESS (Code 0)" if code == 0 else f"FAILED (Code {code})"
        print(f"  {dev_tag}: {st}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
