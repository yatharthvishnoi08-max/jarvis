"""Owner-authorized Gmail and Calendar access. The gateway only reads metadata."""
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
)
CONFIG = Path(os.environ.get("JARVIS_CONFIG_DIR", Path.home() / ".config" / "jarvis"))
CLIENT = CONFIG / "google-desktop.json"
TOKEN = CONFIG / "google-owner.json"
_token_lock = Lock()


def save_token(credentials):
    CONFIG.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=CONFIG, delete=False, encoding="utf-8") as f:
        f.write(credentials.to_json())
    os.replace(f.name, TOKEN)


def connect():
    if not CLIENT.is_file():
        raise SystemExit(f"Save the Jarvis Desktop OAuth client JSON at {CLIENT} first.")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES, autogenerate_code_verifier=True)
    credentials = flow.run_local_server(host="127.0.0.1", port=0, timeout_seconds=300,
        authorization_prompt_message=None, success_message="Jarvis authorization received. You can close this tab.",
        prompt="consent", access_type="offline")
    if not credentials.refresh_token or not credentials.has_scopes(SCOPES):
        raise SystemExit("Google authorization was incomplete.")
    save_token(credentials)


def read_workspace():
    with _token_lock:
        credentials = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
        if not credentials.valid:
            credentials.refresh(Request())
            save_token(credentials)
    with AuthorizedSession(credentials) as http:
        def get(url, **params):
            response = http.get(url, params=params, timeout=12)
            response.raise_for_status()
            return response.json()

        base = "https://gmail.googleapis.com/gmail/v1/users/me/threads"
        threads = get(base, q="in:inbox newer_than:7d -category:promotions -category:social", maxResults=25)
        inbox = []
        for entry in threads.get("threads", []):
            thread = get(f"{base}/{entry['id']}", format="metadata", metadataHeaders=["Subject", "From"])
            messages = thread.get("messages", [])
            if not messages:
                continue
            latest = max(messages, key=lambda m: int(m.get("internalDate", 0)))
            labels = latest.get("labelIds", [])
            if "SENT" in labels or "INBOX" not in labels:
                continue
            headers = {h["name"].lower(): h["value"] for h in latest.get("payload", {}).get("headers", [])}
            inbox.append({"id":entry["id"], "title":headers.get("subject") or "(No subject)",
                          "version":latest.get("id", latest.get("internalDate", "")),
                          "preview":latest.get("snippet", ""), "sender":headers.get("from", ""), "unread":"UNREAD" in labels})
        now = datetime.now(timezone.utc)
        calendar = get("https://www.googleapis.com/calendar/v3/calendars/primary/events",
                       singleEvents="true", orderBy="startTime", timeMin=now.isoformat(),
                       timeMax=(now+timedelta(days=7)).isoformat(), maxResults=30,
                       fields="items(id,summary,start,end,status,transparency)")
        events = [{"id":e["id"], "title":e.get("summary", "Busy"),
                   "end":e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                   "start":e["start"].get("dateTime") or e["start"].get("date")}
                  for e in calendar.get("items", []) if e.get("status") != "cancelled" and e.get("start") and e.get("transparency") != "transparent"]
    return {"inbox":inbox, "events":events, "checked_at":now.isoformat()}


if __name__ == "__main__":
    connect()
    print("Google connected on this device.")
