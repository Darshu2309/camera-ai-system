import psycopg2
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "surveillance"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5000"),
    "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "2")),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id SERIAL PRIMARY KEY,
        camera_id INTEGER,
        timestamp TIMESTAMP,
        file_path TEXT,
        labels TEXT,
        count INTEGER,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION
    )
    """)

    cursor.execute(
        "ALTER TABLE images ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION"
    )
    cursor.execute(
        "ALTER TABLE images ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION"
    )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media_events (
        id SERIAL PRIMARY KEY,
        camera_id INTEGER,
        camera_name TEXT,
        timestamp TIMESTAMP,
        event_type TEXT,
        file_path TEXT,
        thumbnail_path TEXT,
        latitude NUMERIC(11, 8),
        longitude NUMERIC(11, 8),
        confidence DOUBLE PRECISION,
        labels TEXT
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()

def insert_image(camera_id, file_path, labels, count, latitude=None, longitude=None):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO images (
        camera_id,
        timestamp,
        file_path,
        labels,
        count,
        latitude,
        longitude
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        camera_id,
        datetime.now(),
        str(file_path),
        labels,
        count,
        latitude,
        longitude,
    ))

    conn.commit()
    cursor.close()
    conn.close()


def insert_media_event(
    camera_id,
    camera_name,
    event_type,
    file_path,
    thumbnail_path=None,
    latitude=None,
    longitude=None,
    confidence=None,
    labels=None,
):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO media_events (
        camera_id,
        camera_name,
        timestamp,
        event_type,
        file_path,
        thumbnail_path,
        latitude,
        longitude,
        confidence,
        labels
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """, (
        camera_id,
        camera_name,
        datetime.now(),
        event_type,
        str(file_path),
        str(thumbnail_path) if thumbnail_path else None,
        latitude,
        longitude,
        confidence,
        labels,
    ))

    event_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return event_id


def get_media_events(
    start_time=None,
    end_time=None,
    camera_id=None,
    event_type=None,
    limit=100,
):
    conn = get_conn()
    cursor = conn.cursor()

    filters = []
    values = []

    if start_time:
        filters.append("timestamp >= %s")
        values.append(start_time)
    if end_time:
        filters.append("timestamp <= %s")
        values.append(end_time)
    if camera_id:
        filters.append("camera_id = %s")
        values.append(camera_id)
    if event_type:
        filters.append("event_type = %s")
        values.append(event_type)

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    values.append(limit)

    cursor.execute(f"""
    SELECT
        id,
        camera_id,
        camera_name,
        timestamp,
        event_type,
        file_path,
        thumbnail_path,
        latitude,
        longitude,
        confidence,
        labels
    FROM media_events
    {where}
    ORDER BY timestamp DESC
    LIMIT %s
    """, values)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "camera_id": row[1],
            "camera_name": row[2],
            "timestamp": str(row[3]),
            "event_type": row[4],
            "file_path": row[5],
            "thumbnail_path": row[6],
            "latitude": float(row[7]) if row[7] is not None else None,
            "longitude": float(row[8]) if row[8] is not None else None,
            "confidence": row[9],
            "labels": row[10],
        }
        for row in rows
    ]

def get_all_images():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM images ORDER BY timestamp DESC")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
