"""
Dedicated Runner for OnePlus IN2011 (e4903bcf)
Executes the complete Curapod-M test suite exclusively on OnePlus.
"""

import subprocess
import sys
import os

def main():
    print("=" * 80)
    print("  RUNNING COMPLETE CURAPOD-M TEST SUITE ON ONEPLUS (IN2011)")
    print("=" * 80)

    udid = "e4903bcf"
    system_port = 8201

    env = os.environ.copy()
    env["DEVICE_UDID"] = udid
    env["SYSTEM_PORT"] = str(system_port)
    env["APPIUM_HOST"] = "http://127.0.0.1:4725"
    env["APPIUM_SERVER_URL"] = "http://127.0.0.1:4725"
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        r"D:\automachine\test\test_pain_tracking_oneplus.py",
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

    for line in iter(proc.stdout.readline, ''):
        if line:
            print(f"[OnePlus] {line.rstrip()}", flush=True)
    proc.stdout.close()
    proc.wait()
    print("\n" + "=" * 80)
    print(f"  ONEPLUS RUN COMPLETED (Exit Code: {proc.returncode})")
    print("=" * 80)

if __name__ == "__main__":
    main()
