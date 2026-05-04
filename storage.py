from minio import Minio
from minio.error import S3Error
import os
from datetime import timedelta

# ==============================
#  CONFIG (EDIT IF NEEDED)
# ==============================
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET_NAME = "recordings"

# ==============================
#  INIT CLIENT
# ==============================
client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# ==============================
#  ENSURE BUCKET EXISTS
# ==============================
def ensure_bucket():
    try:
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
            print(f"[MINIO] Bucket created: {BUCKET_NAME}")
    except S3Error as e:
        print(f"[MINIO ERROR] Bucket check/create failed: {e}")


# ==============================
# ⬆ UPLOAD FILE
# ==============================
def upload_file(file_path):
    try:
        ensure_bucket()

        if not os.path.exists(file_path):
            print(f"[UPLOAD ERROR] File not found: {file_path}")
            return None

        file_name = os.path.basename(file_path)

        client.fput_object(
            BUCKET_NAME,
            file_name,
            file_path
        )

        print(f"[UPLOAD SUCCESS] {file_name}")
        return file_name

    except S3Error as e:
        print(f"[UPLOAD ERROR] {e}")
        return None


# ==============================
#  DELETE LOCAL FILE
# ==============================
def delete_local(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[LOCAL DELETE] {file_path}")
    except Exception as e:
        print(f"[DELETE ERROR] {e}")


# ==============================
#  GET STREAM URL (PLAYBACK)
# ==============================
def get_video_url(file_name, expiry_seconds=3600):
    try:
        url = client.presigned_get_object(
            BUCKET_NAME,
            file_name,
            expires=timedelta(seconds=expiry_seconds)
        )
        return url
    except S3Error as e:
        print(f"[URL ERROR] {e}")
        return None


# ==============================
#  LIST FILES (OPTIONAL)
# ==============================
def list_files():
    try:
        ensure_bucket()

        objects = client.list_objects(BUCKET_NAME)

        files = []
        for obj in objects:
            files.append(obj.object_name)

        return files

    except S3Error as e:
        print(f"[LIST ERROR] {e}")
        return []


# ==============================
#  DELETE FROM MINIO (OPTIONAL)
# ==============================
def delete_from_minio(file_name):
    try:
        client.remove_object(BUCKET_NAME, file_name)
        print(f"[MINIO DELETE] {file_name}")
    except S3Error as e:
        print(f"[DELETE ERROR] {e}")

if __name__ == "__main__":
    print("[TEST] Testing MinIO connection...")

    test_file = "test.txt"

    with open(test_file, "w") as f:
        f.write("test")

    result = upload_file(test_file)

    print("Upload result:", result)