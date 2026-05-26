from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials


def upload_backup(file_path):

    credentials = Credentials(
        token=None,
        refresh_token='YOUR_REFRESH_TOKEN',
        token_uri='https://oauth2.googleapis.com/token',
        client_id='CLIENT_ID',
        client_secret='CLIENT_SECRET'
    )

    drive = build('drive', 'v3', credentials=credentials)

    media = MediaFileUpload(file_path)

    drive.files().create(
        body={'name': 'patients_backup.xlsx'},
        media_body=media
    ).execute()