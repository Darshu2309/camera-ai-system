from onvif import ONVIFCamera

class PTZController:
    def __init__(self, ip, username, password, port=80):
        self.camera = ONVIFCamera(ip, port, username, password)
        self.media = self.camera.create_media_service()
        self.ptz = self.camera.create_ptz_service()

        self.profile = self.media.GetProfiles()[0]
        self.token = self.profile.token

    def move(self, pan=0, tilt=0, zoom=0):
        request = self.ptz.create_type('ContinuousMove')
        request.ProfileToken = self.token

        request.Velocity = {
            'PanTilt': {'x': pan, 'y': tilt},
            'Zoom': {'x': zoom}
        }

        self.ptz.ContinuousMove(request)

    def stop(self):
        request = self.ptz.create_type('Stop')
        request.ProfileToken = self.token
        request.PanTilt = True
        request.Zoom = True
        self.ptz.Stop(request)