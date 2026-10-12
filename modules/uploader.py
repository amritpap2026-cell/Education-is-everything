"""Fully automated YouTube publishing."""
import json, os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _credentials():
    token_path = Path(os.getenv("YOUTUBE_TOKEN_FILE", "youtube-token.json"))
    client_path = Path(os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json"))
    credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES) if token_path.exists() else None
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        if not client_path.exists():
            raise RuntimeError(f"Missing {client_path}. Download from Google Cloud Console.")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
        credentials = flow.run_local_server(port=0)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def upload(video_path: str, title: str, description: str, tags: list[str], privacy: str = "private") -> dict:
    youtube = build("youtube", "v3", credentials=_credentials())
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": list(dict.fromkeys(tags))[:500],
            "categoryId": "27",
            "defaultLanguage": "en",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]
    result = {"id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}
    Path("output").mkdir(exist_ok=True)
    Path("output/youtube-upload.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"   ✓ Uploaded: {result['url']}")
    return result