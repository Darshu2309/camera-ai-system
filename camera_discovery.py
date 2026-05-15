from services.discovery_service import discover_onvif_cameras


def auto_discover_and_register():
    return discover_onvif_cameras()


if __name__ == "__main__":
    for camera in auto_discover_and_register():
        print(camera)
