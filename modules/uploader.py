"""Single-channel YouTube uploader with playlist routing."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

REDIRECT_URI = "http://localhost:8080/"

PLAYLISTS_FILE = Path("playlists.json")
TOKEN_FILE = Path(os.getenv("YOUTUBE_TOKEN_FILE", "youtube-token.json"))
CLIENT_SECRET_FILE = Path(os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json"))


def load_playlists():
    if PLAYLISTS_FILE.exists():
        return json.loads(PLAYLISTS_FILE.read_text())
    return {}


def _credentials():
    """Get or create OAuth credentials for YouTube."""
    creds = None

    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            print(f"   Token load failed: {e}")
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if not CLIENT_SECRET_FILE.exists():
            raise RuntimeError(
                f"Missing {CLIENT_SECRET_FILE}. Download OAuth credentials from Google Cloud."
            )

        print("\n" + "=" * 60)
        print("AUTHORIZATION REQUIRED")
        print("=" * 60)

        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
        flow.redirect_uri = REDIRECT_URI

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )

        print("\n1. Open this URL in your browser:\n")
        print(auth_url)
        print("\n2. Sign in with the Google account that owns your YouTube channel.")
        print("3. Grant permission for YouTube upload and playlist management.")
        print("4. After authorizing, the browser will fail to load 'localhost:8080' - that's expected.")
        print("5. Copy the ENTIRE URL from the address bar of that error page.")
        print("\n" + "=" * 60)

        redirect_response = input("\nPaste the full redirect URL here: ").strip()

        parsed = urlparse(redirect_response)
        params = parse_qs(parsed.query)

        if "code" not in params:
            print("\nError: Could not find 'code' parameter in the URL.")
            raise RuntimeError("Authorization code not found in redirect URL.")

        auth_code = params["code"][0]
        print(f"\n   Extracted authorization code: {auth_code[:20]}...")

        flow.fetch_token(code=auth_code)
        creds = flow.credentials

        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"\nToken saved to {TOKEN_FILE}")

    return creds


def upload(
    video_path,
    title,
    description,
    tags,
    language="English",
    privacy=None,
    thumbnail=None,
):
    playlists = load_playlists()
    cfg = playlists.get(language, {})
    if privacy is None:
        privacy = cfg.get("privacy", "private")

    credentials = _credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": list(dict.fromkeys(tags))[:500],
            "categoryId": cfg.get("category_id", "27"),
            "defaultLanguage": cfg.get("default_language", "en"),
            "defaultAudioLanguage": cfg.get("default_language", "en"),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    print(f"   Uploading video (language: {language}, privacy: {privacy})...")
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True),
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status and status.progress() > 0:
            print(f"   Upload: {int(status.progress() * 100)}%")

    video_id = response["id"]
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"   Uploaded: {url}")

    playlist_id = cfg.get("playlist_id", "").strip()
    if playlist_id and not playlist_id.startswith("PLpaste"):
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    }
                },
            ).execute()
            print(f"   Added to playlist: {playlist_id}")
        except Exception as e:
            print(f"   Playlist add failed: {e}")

    if thumbnail and Path(thumbnail).exists():
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail, mimetype="image/jpeg"),
            ).execute()
            print(f"   Thumbnail uploaded")
        except Exception as e:
            print(f"   Thumbnail failed: {e}")

    result = {"id": video_id, "url": url, "language": language, "privacy": privacy}
    Path("output").mkdir(exist_ok=True)
    Path(f"output/youtube-upload-{language.lower()}.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result