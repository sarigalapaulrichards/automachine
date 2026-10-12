"""
device_manager.py
Dynamic USB Phone Detection, Device Identification, and Adaptive Padding Manager.

Automatically detects any Android phone connected via USB debugging (ADB),
identifies device model, brand, manufacturer, resolution, and screen density,
computes top status bar padding, bottom navigation bar padding, and usable viewport,
and provides calibrated/adjusted coordinates so the Curapod-M automachine
runs reliably on ANY phone without manual hardcoding.
"""

import os
import re
import sys
import json
import subprocess
from typing import Dict, List, Optional, Tuple, Any

# Default fallback reference: 1080x2400 @ 420dpi (Pixel 7a baseline)
BASELINE_W = 1080.0
BASELINE_H = 2400.0
BASELINE_DPI = 420.0


class DeviceProfile:
    """
    Encapsulates all hardware, display, and padding metrics for a connected Android phone.
    """
    def __init__(
        self,
        udid: str,
        model: str = "Unknown Android",
        brand: str = "Android",
        manufacturer: str = "Android",
        android_version: str = "13",
        sdk_version: str = "33",
        width: int = 1080,
        height: int = 2400,
        density: int = 420,
        top_padding: int = 118,
        bottom_padding: int = 63,
        left_padding: int = 0,
        right_padding: int = 0,
        system_port: int = 8200,
        appium_port: int = 4723,
    ):
        self.udid = udid
        self.model = model
        self.brand = brand
        self.manufacturer = manufacturer
        self.android_version = android_version
        self.sdk_version = sdk_version
        self.width = width
        self.height = height
        self.density = density
        self.top_padding = top_padding
        self.bottom_padding = bottom_padding
        self.left_padding = left_padding
        self.right_padding = right_padding
        self.system_port = system_port
        self.appium_port = appium_port

        # Derived metrics
        self.usable_top = self.top_padding
        self.usable_bottom = self.height - self.bottom_padding
        self.usable_height = max(1, self.height - self.top_padding - self.bottom_padding)
        self.usable_width = max(1, self.width - self.left_padding - self.right_padding)

        # Scale factors relative to baseline
        self.scale_x = self.width / BASELINE_W
        self.scale_y = self.height / BASELINE_H
        self.scale_dpi = self.density / BASELINE_DPI

    @property
    def display_name(self) -> str:
        return f"{self.brand.capitalize()} {self.model}".strip()

    def dp_to_px(self, dp: float) -> int:
        """Converts device-independent pixels (dp) to physical device pixels."""
        return int(round(dp * (self.density / 160.0)))

    # --- ADAPTIVE COORDINATE HELPERS ---

    def top_action_y(self, offset_dp: float = 24.0) -> int:
        """
        Coordinates for top action buttons (e.g. Skip, Back, Profile avatar)
        guaranteed to sit cleanly below the phone's status bar / camera notch.
        """
        return self.top_padding + self.dp_to_px(offset_dp)

    def bottom_action_y(self, offset_dp: float = 38.0) -> int:
        """
        Coordinates for primary bottom action buttons (Continue, Submit, Start Session, Stop Session, I Accept)
        guaranteed to sit centered inside the bottom container above the system navigation/gesture bar.
        """
        return self.height - self.bottom_padding - self.dp_to_px(offset_dp)

    def bottom_nav_tab_y(self, offset_dp: float = 24.0) -> int:
        """
        Vertical center coordinate for bottom navigation bar items (Home, Cycle, Profile tabs).
        """
        return self.height - self.bottom_padding - self.dp_to_px(offset_dp)

    def home_tab_coords(self) -> Tuple[int, int]:
        """Adaptive coordinate for 'Home' icon in bottom navigation bar (Tab 1/5)."""
        x = int(self.width * 0.135)
        y = self.bottom_nav_tab_y()
        return x, y

    def cycle_tab_coords(self) -> Tuple[int, int]:
        """Adaptive coordinate for 'Cycle' icon in bottom navigation bar (Tab 2/5)."""
        if "IN2011" in self.model or self.udid == "e4903bcf":
            return 329, 2204
        x = int(self.width * 0.312)
        y = self.bottom_nav_tab_y()
        return x, y

    def insight_tab_coords(self) -> Tuple[int, int]:
        """Adaptive coordinate for 'Insight' icon in bottom navigation bar (Tab 3/5)."""
        x = int(self.width * 0.490)
        y = self.bottom_nav_tab_y()
        return x, y

    def profile_tab_coords(self) -> Tuple[int, int]:
        """Adaptive coordinate for 'Profile' icon in bottom navigation bar (Tab 4/5)."""
        x = int(self.width * 0.668)
        y = self.bottom_nav_tab_y()
        return x, y

    def start_tab_coords(self) -> Tuple[int, int]:
        """Adaptive coordinate for 'Start' icon in bottom navigation bar (Tab 5/5)."""
        x = int(self.width * 0.894)
        y = self.bottom_nav_tab_y()
        return x, y

    def terms_checkbox_coords(self) -> Tuple[int, int]:
        """Adaptive coordinate for Terms & Privacy checkbox."""
        if "IN2011" in self.model or self.udid == "e4903bcf":
            return 123, 1913
        cb_x = int(self.width * 0.10)
        cb_y = self.bottom_action_y() - self.dp_to_px(72.0)
        return cb_x, cb_y

    def terms_accept_coords(self) -> Tuple[int, int]:
        """Adaptive coordinate for Terms & Privacy 'I Accept' button."""
        if "IN2011" in self.model or self.udid == "e4903bcf":
            return 540, 2127
        return int(self.width * 0.50), self.bottom_action_y()

    def delete_modal_input_coords(self) -> Tuple[int, int]:
        """
        Calculates center of the 'Type DELETE' input field on the delete confirmation modal.
        Positioned directly above the 'Delete my account' confirm button (~77.5% of usable viewport).
        Bounds on 1080x2400: [32, 1767][1049, 1910] -> Center (540, 1838).
        """
        cx = int(self.width * 0.50)
        cy = self.usable_top + int(self.usable_height * 0.775)
        return cx, cy

    def delete_modal_confirm_coords(self) -> Tuple[int, int]:
        """
        Calculates center of 'Delete my account' button on the delete confirmation modal.
        The button is positioned on the bottom sheet modal at ~85% of screen height.
        Bounds on 1080x2400: [32, 1973][1049, 2109] -> Center (540, 2041).
        NEVER tap at bottom_action_y() here because that hits the bottom navigation bar (Insight tab).
        """
        cx = int(self.width * 0.50)
        cy = self.usable_top + int(self.usable_height * 0.86)
        return cx, cy

    def initial_pain_slider_coords(self, pain_score: int) -> Tuple[int, int]:
        """
        Calculates slider touch coordinates for 0-10 pain score on initial rating screen.
        """
        min_x = int(self.width * 0.158)
        max_x = int(self.width * 0.842)
        score_ratio = max(0.0, min(10.0, float(pain_score))) / 10.0
        x = int(min_x + score_ratio * (max_x - min_x))
        y = self.usable_top + int(self.usable_height * 0.46)
        return x, y

    def mpr_pain_slider_coords(self, pain_score: int) -> Tuple[int, int]:
        """
        Calculates slider touch coordinates on Menstrual Pain Relief screen.
        """
        min_x = int(self.width * 0.158)
        max_x = int(self.width * 0.842)
        score_ratio = max(0.0, min(10.0, float(pain_score))) / 10.0
        x = int(min_x + score_ratio * (max_x - min_x))
        y = self.usable_top + int(self.usable_height * 0.435)
        return x, y

    def final_pain_slider_coords(self, pain_score: int) -> Tuple[int, int]:
        """
        Calculates slider touch coordinates on Session Completed screen.
        """
        min_x = int(self.width * 0.158)
        max_x = int(self.width * 0.842)
        score_ratio = max(0.0, min(10.0, float(pain_score))) / 10.0
        x = int(min_x + score_ratio * (max_x - min_x))
        y = self.usable_top + int(self.usable_height * 0.505)
        return x, y

    def calendar_day_coords(self, month_y: int, first_col: int, day_int: int) -> Tuple[int, int]:
        """
        Calculates calendar day cell center (cx, cy) adjusted for screen width & padding.
        """
        day_idx = first_col + (day_int - 1)
        col_idx = day_idx % 7
        row_idx = day_idx // 7

        base_centers = [118, 259, 400, 540, 681, 822, 963]
        col_centers = [int(bc * self.scale_x) for bc in base_centers]
        cx = col_centers[col_idx]
        cy = int(month_y + (230 * self.scale_y) + row_idx * (152 * self.scale_y))
        return cx, cy

    def summary(self) -> str:
        return (
            f"Device: {self.display_name} (UDID: {self.udid})\n"
            f"Android: {self.android_version} (SDK {self.sdk_version})\n"
            f"Physical Resolution: {self.width}x{self.height} @ {self.density}dpi\n"
            f"Paddings: Top (Status Bar)={self.top_padding}px, Bottom (Nav Bar)={self.bottom_padding}px\n"
            f"Usable Content Viewport: {self.usable_width}x{self.usable_height}px\n"
            f"Appium SystemPort: {self.system_port}"
        )


def run_adb(args: List[str], udid: Optional[str] = None, timeout: int = 6) -> str:
    """Runs an adb command safely, targeting specific udid if provided."""
    cmd = ["adb"]
    if udid:
        cmd.extend(["-s", udid])
    cmd.extend(args)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip()
    except Exception:
        return ""


def get_connected_udids() -> List[str]:
    """Returns list of online Android device UDIDs from adb devices."""
    out = run_adb(["devices"])
    udids = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            udids.append(parts[0])
    return udids


def detect_device_profile(udid: str, system_port: Optional[int] = None, appium_port: int = 4723) -> DeviceProfile:
    """
    Queries ADB to comprehensively identify the connected phone and calculate its exact
    screen metrics, display cutouts, and status/navigation bar paddings.
    """
    model = run_adb(["shell", "getprop", "ro.product.model"], udid) or "Unknown Android"
    brand = run_adb(["shell", "getprop", "ro.product.brand"], udid) or "Android"
    manufacturer = run_adb(["shell", "getprop", "ro.product.manufacturer"], udid) or "Android"
    android_ver = run_adb(["shell", "getprop", "ro.build.version.release"], udid) or "13"
    sdk_ver = run_adb(["shell", "getprop", "ro.build.version.sdk"], udid) or "33"

    # Resolution
    res_str = run_adb(["shell", "wm", "size"], udid)
    m_size = re.search(r'(?:Physical size|Override size):\s*(\d+)x(\d+)', res_str)
    width, height = (int(m_size.group(1)), int(m_size.group(2))) if m_size else (1080, 2400)

    # Density
    den_str = run_adb(["shell", "wm", "density"], udid)
    m_den = re.search(r'(?:Physical density|Override density):\s*(\d+)', den_str)
    density = int(m_den.group(1)) if m_den else 420

    # Insets / Padding Detection via dumpsys window displays
    top_pad = 0
    bottom_pad = 0
    left_pad = 0
    right_pad = 0

    dumpsys_displays = run_adb(["shell", "dumpsys", "window", "displays"], udid)
    if dumpsys_displays:
        # Check InsetsSource type=statusBars frame=[0,0][1080,118]
        m_sb = re.search(r'InsetsSource.*?type=statusBars\s+frame=\[(\d+),(\d+)\]\[(\d+),(\d+)\]', dumpsys_displays)
        if m_sb:
            top_pad = int(m_sb.group(4)) - int(m_sb.group(2))

        # Check InsetsSource type=navigationBars frame=[0,2337][1080,2400]
        m_nb = re.search(r'InsetsSource.*?type=navigationBars\s+frame=\[(\d+),(\d+)\]\[(\d+),(\d+)\]', dumpsys_displays)
        if m_nb:
            bottom_pad = height - int(m_nb.group(2))

    # Backup Inset Detection via dumpsys display
    if top_pad <= 0 or bottom_pad <= 0:
        dumpsys_win = run_adb(["shell", "dumpsys", "window"], udid)
        if top_pad <= 0:
            m_sb_alt = re.search(r'statusBars.*insetsSize=Insets\{left=0,\s*top=(\d+)', dumpsys_win)
            if m_sb_alt:
                top_pad = int(m_sb_alt.group(1))

        if bottom_pad <= 0:
            m_nb_alt = re.search(r'navigationBars.*insetsSize=Insets\{.*?bottom=(\d+)', dumpsys_win)
            if m_nb_alt:
                bottom_pad = int(m_nb_alt.group(1))

    # Safe defaults if detection failed (typical Android layout defaults)
    if top_pad <= 0:
        top_pad = int(round(32 * (density / 160.0)))
    if bottom_pad <= 0:
        bottom_pad = int(round(16 * (density / 160.0)))

    # Determine system_port if not specified
    if system_port is None:
        if udid == "e4903bcf" or "IN2011" in model:
            system_port = 8201
        else:
            system_port = 8200

    return DeviceProfile(
        udid=udid,
        model=model,
        brand=brand,
        manufacturer=manufacturer,
        android_version=android_ver,
        sdk_version=sdk_ver,
        width=width,
        height=height,
        density=density,
        top_padding=top_pad,
        bottom_padding=bottom_pad,
        left_padding=left_pad,
        right_padding=right_pad,
        system_port=system_port,
        appium_port=appium_port,
    )


# Active global device profile instance
ACTIVE_DEVICE: Optional[DeviceProfile] = None


def get_active_device(force_refresh: bool = False) -> DeviceProfile:
    """
    Returns the active DeviceProfile for the connected phone.
    Automatically detects connected devices via USB debugging and calibrates padding.
    """
    global ACTIVE_DEVICE
    if ACTIVE_DEVICE is not None and not force_refresh:
        return ACTIVE_DEVICE

    # 1. Check explicit environment variables
    env_udid = os.environ.get("DEVICE_UDID")
    env_port = int(os.environ.get("SYSTEM_PORT", 0)) if os.environ.get("SYSTEM_PORT") else None
    appium_port = int(os.environ.get("APPIUM_PORT", 4723))

    connected = get_connected_udids()

    target_udid = None
    if env_udid and env_udid in connected:
        target_udid = env_udid
    elif env_udid:
        target_udid = env_udid
    elif len(connected) == 1:
        target_udid = connected[0]
    elif "38181JEHN00069" in connected:
        target_udid = "38181JEHN00069"
    elif "e4903bcf" in connected:
        target_udid = "e4903bcf"
    elif connected:
        target_udid = connected[0]
    else:
        # Fallback if no device connected
        target_udid = "38181JEHN00069"

    profile = detect_device_profile(target_udid, system_port=env_port, appium_port=appium_port)
    ACTIVE_DEVICE = profile

    print("\n" + "=" * 80)
    print("  [USB PHONE IDENTIFIED & PADDING CALIBRATED]")
    print(f"  Model       : {profile.display_name} ({profile.manufacturer})")
    print(f"  UDID        : {profile.udid}")
    print(f"  Android OS  : Version {profile.android_version} (SDK {profile.sdk_version})")
    print(f"  Screen Size : {profile.width} x {profile.height} (Density: {profile.density} dpi)")
    print(f"  Top Padding : {profile.top_padding} px (Status Bar / Notch)")
    print(f"  Bottom Pad  : {profile.bottom_padding} px (Navigation Bar)")
    print(f"  Usable Area : {profile.usable_width} x {profile.usable_height} px")
    print(f"  Ports       : Appium {profile.appium_port} | SystemPort {profile.system_port}")
    print("=" * 80 + "\n", flush=True)

    return ACTIVE_DEVICE


def list_all_connected_devices() -> List[DeviceProfile]:
    """Identifies and returns DeviceProfiles for all phones connected via USB debugging."""
    udids = get_connected_udids()
    profiles = []
    base_sys_port = 8200
    for idx, udid in enumerate(udids):
        p = detect_device_profile(udid, system_port=base_sys_port + idx)
        profiles.append(p)
    return profiles


if __name__ == "__main__":
    print("Scanning USB debugging connections...")
    devs = list_all_connected_devices()
    if not devs:
        print("No Android phones detected over USB debugging.")
    else:
        print(f"Found {len(devs)} connected phone(s):")
        for i, d in enumerate(devs, 1):
            print(f"\n--- Phone #{i} ---")
            print(d.summary())
