from datetime import datetime
import pytz
ist = pytz.timezone("Asia/Kolkata")


tracking_sessions = {}


def start_tracking(camera_id, target):

    current_time_ist = datetime.now(
        ist
    ).strftime("%Y-%m-%d %H:%M:%S IST")

    tracking_sessions[camera_id] = {

        "target": target,

        "started_at": current_time_ist,

        "status": "tracking"
    }

    print(f"""
=========================
TRACKING STARTED

Camera: {camera_id}

Target: {target}

Started At: {current_time_ist}
=========================
""")

    return tracking_sessions[camera_id]


def stop_tracking(camera_id):

    if camera_id in tracking_sessions:

        del tracking_sessions[camera_id]

    print(f"""
=========================
TRACKING STOPPED

Camera: {camera_id}
=========================
""")

    return {
        "status": "stopped"
    }


def get_tracking_sessions():

    return tracking_sessions