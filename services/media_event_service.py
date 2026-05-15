from database import get_media_events, init_db


def search_events(start_time=None, end_time=None, camera_id=None, event_type=None, limit=100):
    try:
        init_db()
        return {
            "status": "ok",
            "events": get_media_events(
                start_time=start_time,
                end_time=end_time,
                camera_id=camera_id,
                event_type=event_type,
                limit=limit,
            ),
        }
    except Exception as e:
        return {
            "status": "db_unavailable",
            "events": [],
            "message": str(e),
        }
