"""Google Calendar integration (single business-owner account).

OAuth tokens are stored in Mongo (`google_tokens`, key='primary'). The assistant
creates/lists events on the owner's primary calendar. Connect flow runs on the
deployed domain (redirect URI must match the Google Cloud config).
"""
import os
from datetime import datetime, timezone

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")
SCOPES = ["https://www.googleapis.com/auth/calendar"]
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_TZ = "America/Montreal"


def is_configured() -> bool:
    return bool(CLIENT_ID and CLIENT_SECRET and REDIRECT_URI)


def authorization_url() -> str:
    from urllib.parse import urlencode
    params = {
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI,
        "response_type": "code", "scope": " ".join(SCOPES),
        "access_type": "offline", "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urlencode(params)


async def exchange_code(db, code: str) -> None:
    resp = requests.post(_TOKEN_URI, data={
        "code": code, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code",
    }, timeout=20).json()
    if "access_token" not in resp:
        raise RuntimeError(resp.get("error_description") or resp.get("error") or "Échec OAuth")
    await db.google_tokens.update_one(
        {"key": "primary"}, {"$set": {"key": "primary", "tokens": resp,
                                       "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)


async def is_connected(db) -> bool:
    doc = await db.google_tokens.find_one({"key": "primary"})
    return bool(doc and doc.get("tokens", {}).get("refresh_token"))


async def _creds(db):
    doc = await db.google_tokens.find_one({"key": "primary"})
    if not doc:
        return None
    tok = doc["tokens"]
    creds = Credentials(
        token=tok.get("access_token"), refresh_token=tok.get("refresh_token"),
        token_uri=_TOKEN_URI, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, scopes=SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        await db.google_tokens.update_one(
            {"key": "primary"}, {"$set": {"tokens.access_token": creds.token}})
    return creds


async def create_event(db, *, title, start, end=None, location=None, notes=None) -> dict:
    creds = await _creds(db)
    if not creds:
        raise RuntimeError("not_connected")
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    all_day = len(start) == 10  # YYYY-MM-DD
    body = {"summary": title}
    if location:
        body["location"] = location
    if notes:
        body["description"] = notes
    if all_day:
        body["start"] = {"date": start}
        body["end"] = {"date": end or start}
    else:
        body["start"] = {"dateTime": start, "timeZone": _TZ}
        body["end"] = {"dateTime": end or start, "timeZone": _TZ}
    return service.events().insert(calendarId="primary", body=body).execute()


async def list_upcoming(db, max_results: int = 10) -> list:
    creds = await _creds(db)
    if not creds:
        return []
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    res = service.events().list(
        calendarId="primary", timeMin=datetime.now(timezone.utc).isoformat(),
        maxResults=max_results, singleEvents=True, orderBy="startTime").execute()
    return res.get("items", [])
