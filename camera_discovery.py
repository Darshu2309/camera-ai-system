import requests
from wsdiscovery.discovery import ThreadedWSDiscovery as WSDiscovery


CONFIG_SERVER = "http://127.0.0.1:8001/add_camera"


def discover_onvif_cameras():
    print("[DISCOVERY] Starting ONVIF scan...")

    wsd = WSDiscovery()
    wsd.start()

    services = wsd.searchServices()

    cameras = []

    for service in services:
        xaddr = service.getXAddrs()[0]

        try:
            ip = xaddr.split("/")[2].split(":")[0]

            print(f"[FOUND] Camera at {ip}")

            cameras.append({
                "ip": ip,
                "username": "admin",     # default guess
                "password": "admin",     # change if needed
                "name": f"AutoCam-{ip}"
            })

        except Exception:
            continue

    wsd.stop()
    return cameras


def register_cameras(cameras):
    print("[REGISTER] Sending cameras to config server...")

    for cam in cameras:
        try:
            response = requests.post(CONFIG_SERVER, json=cam, timeout=5)

            if response.status_code == 200:
                print(f"[ADDED] {cam['ip']}")
            else:
                print(f"[SKIP] {cam['ip']} already exists")

        except Exception as e:
            print(f"[ERROR] {cam['ip']} → {e}")


def auto_discover_and_register():
    cams = discover_onvif_cameras()

    if not cams:
        print("[INFO] No cameras found")
        return

    register_cameras(cams)


if __name__ == "__main__":
    auto_discover_and_register()