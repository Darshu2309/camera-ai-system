import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
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
        count INTEGER
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()

def insert_image(camera_id, file_path, labels, count):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO images (camera_id, timestamp, file_path, labels, count)
    VALUES (%s, %s, %s, %s, %s)
    """, (camera_id, datetime.now(), file_path, labels, count))

    conn.commit()
    cursor.close()
    conn.close()

def get_all_images():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM images ORDER BY timestamp DESC")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows