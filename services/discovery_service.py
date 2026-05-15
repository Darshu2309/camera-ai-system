import json
import socket
import requests
import cv2

from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor


# ============================================================
# STORAGE
# ============================================================

CAMERA_DB = Path("cameras.json")


# ============================================================
# MAIN DISCOVERY ENTRY
# ============================================================

def discover_onvif_cameras(timeout=4):

    discovered = []

    # --------------------------------------------------------
    # ONVIF WS DISCOVERY
    # --------------------------------------------------------

    try:

        ws_cameras = discover_ws_cameras(timeout)

        discovered.extend(ws_cameras)

    except Exception as e:

        print("[DISCOVERY] WS discovery failed:", e)

    # --------------------------------------------------------
    # SUBNET SCAN
    # --------------------------------------------------------

    try:

        subnet_cameras = scan_local_network()

        existing_ips = {
            cam["ip"]
            for cam in discovered
        }

        for cam in subnet_cameras:

            if cam["ip"] not in existing_ips:
                discovered.append(cam)

    except Exception as e:

        print("[DISCOVERY] Subnet scan failed:", e)

    # --------------------------------------------------------
    # STORE DISCOVERED CAMERAS
    # --------------------------------------------------------

    save_discovered_cameras(discovered)

    return discovered


# ============================================================
# ONVIF WS DISCOVERY
# ============================================================

def discover_ws_cameras(timeout=4):

    services = _discover_ws_services(timeout)

    cameras = []

    seen_ips = set()

    for service in services:

        xaddrs = _safe_call(service, "getXAddrs") or []
        scopes = _safe_call(service, "getScopes") or []

        ip = _extract_ip(xaddrs)

        if not ip or ip in seen_ips:
            continue

        seen_ips.add(ip)

        cameras.append({

            "camera_name":
                _camera_name_from_scopes(
                    scopes,
                    ip
                ),

            "ip": ip,

            "vendor":
                detect_vendor(ip),

            "mac": None,

            "onvif": True,

            "rtsp_capable": True,

            "authenticated": False,

            "stream_ready": False,

            "rtsp_url": None,

            "ptz_supported":
                detect_ptz_support(
                    service,
                    xaddrs
                ),

            "source":
                "onvif_ws_discovery"
        })

    return cameras


# ============================================================
# LOCAL NETWORK SCAN
# ============================================================

def scan_local_network(

    subnet="192.168.1.",

    start=1,

    end=255
):

    discovered = []

    def check_ip(i):

        ip = f"{subnet}{i}"

        try:

            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            sock.settimeout(0.3)

            result = sock.connect_ex((ip, 80))

            sock.close()

            if result == 0:

                camera = probe_camera(ip)

                if camera:
                    discovered.append(camera)

        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=64) as executor:

        executor.map(
            check_ip,
            range(start, end)
        )

    return discovered


# ============================================================
# CAMERA PROBE
# ============================================================

def probe_camera(ip):

    try:

        response = requests.get(
            f"http://{ip}",
            timeout=1
        )

        server = response.headers.get(
            "Server",
            ""
        ).lower()

        text = response.text.lower()

        vendor = None

        if "dahua" in server or "dahua" in text:
            vendor = "Dahua"

        elif "hikvision" in server or "hikvision" in text:
            vendor = "Hikvision"

        elif "ip camera" in text:
            vendor = "Generic IP Camera"

        if not vendor:
            return None

        return {

            "camera_name":
                f"{vendor} Camera {ip}",

            "ip": ip,

            "vendor": vendor,

            "mac": None,

            "onvif": True,

            "rtsp_capable": True,

            "authenticated": False,

            "stream_ready": False,

            "rtsp_url": None,

            "ptz_supported": False,

            "source": "network_scan"
        }

    except Exception:

        return None


# ============================================================
# SAVE DISCOVERED CAMERAS
# ============================================================

def save_discovered_cameras(cameras):

    existing = []

    if CAMERA_DB.exists():

        try:

            with open(CAMERA_DB, "r") as f:
                existing = json.load(f)

        except Exception:
            existing = []

    existing_ips = {
        cam.get("ip")
        for cam in existing
    }

    next_id = max(
        [cam.get("id", 0) for cam in existing],
        default=0
    ) + 1

    added = 0

    for cam in cameras:

        if cam["ip"] in existing_ips:
            continue

        cam["id"] = next_id

        next_id += 1

        existing.append(cam)

        added += 1

    with open(CAMERA_DB, "w") as f:

        json.dump(
            existing,
            f,
            indent=2
        )

    print(
        f"[DISCOVERY] Added {added} new cameras."
    )


# ============================================================
# VENDOR DETECTION
# ============================================================

def detect_vendor(ip):

    try:

        response = requests.get(
            f"http://{ip}",
            timeout=1
        )

        server = response.headers.get(
            "Server",
            ""
        ).lower()

        text = response.text.lower()

        if "dahua" in server or "dahua" in text:
            return "Dahua"

        if "hikvision" in server or "hikvision" in text:
            return "Hikvision"

    except Exception:
        pass

    return "Unknown"


# ============================================================
# PTZ SUPPORT
# ============================================================

def detect_ptz_support(
    service,
    xaddrs
):

    types = (
        _safe_call(service, "getTypes")
        or []
    )

    text = " ".join([
        str(item).lower()
        for item in types + xaddrs
    ])

    return "ptz" in text


# ============================================================
# WS DISCOVERY
# ============================================================

def _discover_ws_services(timeout):

    try:

        from wsdiscovery.discovery import (
            ThreadedWSDiscovery
        )

    except Exception as e:

        print(
            "[DISCOVERY] wsdiscovery unavailable:",
            e
        )

        return []

    wsd = ThreadedWSDiscovery()

    try:

        wsd.start()

        return wsd.searchServices(
            timeout=timeout
        )

    except TypeError:

        return wsd.searchServices()

    except Exception as e:

        print(
            "[DISCOVERY] ONVIF scan failed:",
            e
        )

        return []

    finally:

        try:
            wsd.stop()

        except Exception:
            pass


# ============================================================
# HELPERS
# ============================================================

def _extract_ip(xaddrs):

    for xaddr in xaddrs:

        parsed = urlparse(xaddr)

        if parsed.hostname:
            return parsed.hostname

    return None


def _camera_name_from_scopes(
    scopes,
    ip
):

    for scope in scopes:

        value = str(scope)

        if "name/" in value:

            return (
                value
                .rsplit("/", 1)[-1]
                .replace("%20", " ")
            )

    return f"Discovered Camera {ip}"


def _safe_call(
    obj,
    method_name
):

    try:

        return getattr(
            obj,
            method_name
        )()

    except Exception:

        return None
    
def validate_rtsp_url(
    rtsp_url,
    timeout_seconds=3
):

    if not rtsp_url:

        return {
            "valid": False,
            "reason": "missing_rtsp_url"
        }

    cap = None

    try:

        cap = cv2.VideoCapture(
            rtsp_url,
            cv2.CAP_FFMPEG
        )

        cap.set(
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
            int(timeout_seconds * 1000)
        )

        cap.set(
            cv2.CAP_PROP_READ_TIMEOUT_MSEC,
            int(timeout_seconds * 1000)
        )

        ok, frame = cap.read()

        if ok and frame is not None:

            return {
                "valid": True,
                "reason": "ok"
            }

        return {
            "valid": False,
            "reason": "no_frame"
        }

    except Exception as e:

        return {
            "valid": False,
            "reason": str(e)
        }

    finally:

        if cap:
            cap.release()