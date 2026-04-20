from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
gauth.LocalWebserverAuth()

drive = GoogleDrive(gauth)


def get_or_create_folder(folder_name):
    file_list = drive.ListFile({
        'q': f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()

    if file_list:
        return file_list[0]['id']

    folder = drive.CreateFile({
        'title': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    })
    folder.Upload()
    return folder['id']


def upload_to_drive(file_path, file_name, camera_id):
    folder_name = f"Camera_{camera_id}"
    folder_id = get_or_create_folder(folder_name)

    file = drive.CreateFile({
        'title': file_name,
        'parents': [{'id': folder_id}]
    })
    file.SetContentFile(file_path)
    file.Upload()

    print(f"Uploaded to Drive → {folder_name}/{file_name}")