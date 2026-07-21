import os
import io
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from config import GOOGLE_DRIVE_FOLDER_ID, GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH, DATA_DIR
from database import ingest_csv

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DOWNLOAD_DIR = DATA_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


def get_drive_service():
    creds = None

    if GOOGLE_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not GOOGLE_CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    "credentials.json not found. Download it from Google Cloud Console "
                    "(APIs & Services > Credentials > OAuth 2.0 Client IDs) "
                    "and place it in the backend/ directory."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GOOGLE_CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        GOOGLE_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(GOOGLE_TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def list_csv_files(folder_id: str = None) -> list[dict]:
    folder_id = folder_id or GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        return []

    service = get_drive_service()

    query = f"'{folder_id}' in parents and (mimeType='text/csv' or name contains '.csv') and trashed=false"
    results = []
    page_token = None

    while True:
        response = service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, modifiedTime, size)",
            pageToken=page_token,
            orderBy="modifiedTime desc",
        ).execute()

        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    subfolders = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces="drive",
        fields="files(id, name)",
    ).execute().get("files", [])

    for subfolder in subfolders:
        results.extend(list_csv_files(subfolder["id"]))

    return results


def download_file(service, file_id: str, filename: str) -> str:
    dest_path = DOWNLOAD_DIR / filename
    if dest_path.exists():
        return str(dest_path)

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    with open(dest_path, "wb") as f:
        f.write(fh.getvalue())

    return str(dest_path)


def sync_from_drive(folder_id: str = None) -> dict:
    folder_id = folder_id or GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        return {"status": "error", "message": "No Google Drive folder ID configured"}

    service = get_drive_service()
    csv_files = list_csv_files(folder_id)

    results = {"total_files": len(csv_files), "imported": [], "skipped": [], "errors": []}

    for file_info in csv_files:
        try:
            local_path = download_file(service, file_info["id"], file_info["name"])
            result = ingest_csv(local_path, file_info["name"])

            if result["status"] == "skipped":
                results["skipped"].append(file_info["name"])
            else:
                results["imported"].append({
                    "filename": file_info["name"],
                    "rows": result["rows_imported"],
                    "table": result["table"],
                })
        except Exception as e:
            results["errors"].append({"filename": file_info["name"], "error": str(e)})

    return results
