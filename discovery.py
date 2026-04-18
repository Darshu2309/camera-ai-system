from onvif import ONVIFCamera
from zeep.transports import Transport
import requests

def discover_camera(ip, username, password):
    try:
        camera = ONVIFCamera(ip, 80, username, password)

        media = camera.create_media_service()
        profiles = media.GetProfiles()

        stream_uri = media.GetStreamUri({
            'StreamSetup': {
                'Stream': 'RTP-Unicast',
                'Transport': {'Protocol': 'RTSP'}
            },
            'ProfileToken': profiles[0].token
        })

        return {
            "ip": ip,
            "rtsp": stream_uri.Uri
        }

    except Exception as e:
        return {"error": str(e)}