import os
from pathlib import Path

from dotenv import dotenv_values
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


config = dotenv_values(".env")

GMAIL_MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
SCOPES = [GMAIL_MODIFY_SCOPE, CALENDAR_SCOPE]

OAUTH_CLIENT_PATH = Path(config.get("GOOGLE_OAUTH_CLIENT_PATH") or "./.gcp_keys/OAuthClient.json")
USER_TOKEN_PATH = Path(config.get("GOOGLE_USER_TOKEN_PATH") or "./.gcp_keys/token.json")
REDIRECT_URI = config.get("GOOGLE_OAUTH_REDIRECT_URI") or "https://nairoki.dev"


class GoogleAuth:
    """OAuth credentials shared by every Google service in this bot."""

    def __init__(self):
        self.flow = None

    def get_creds(self):
        """Return valid credentials, refreshing them when possible."""
        if not USER_TOKEN_PATH.exists():
            return None

        try:
            # Load the scopes recorded in the token itself. Passing SCOPES here
            # would make an old Gmail-only token look Calendar-capable.
            creds = Credentials.from_authorized_user_file(str(USER_TOKEN_PATH))
        except (ValueError, OSError):
            return None

        # An old Gmail-only token must be re-authorized for Calendar access.
        if not creds.has_scopes(SCOPES):
            return None
        if creds.valid:
            return creds
        if not (creds.expired and creds.refresh_token):
            return None

        try:
            creds.refresh(Request())
            self._save(creds)
            return creds
        except Exception as exc:
            print(f"Google token refresh failed: {exc}")
            return None

    def interactive_creds(self, authorization_response: str) -> bool:
        if self.flow is None:
            return False
        try:
            self.flow.fetch_token(authorization_response=authorization_response.strip())
            creds = self.flow.credentials
            self._save(creds)
            self.flow = None
            return bool(creds.valid and creds.has_scopes(SCOPES))
        except Exception as exc:
            print(f"Google OAuth callback failed: {exc}")
            return False

    def create_cred_url(self) -> str:
        # Local development uses an HTTPS callback whose final URL is pasted into
        # Discord. Do not globally enable insecure OAuth transport.
        self.flow = InstalledAppFlow.from_client_secrets_file(
            str(OAUTH_CLIENT_PATH),
            SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        auth_url, _ = self.flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
        return auth_url

    @staticmethod
    def required_scopes() -> tuple[str, ...]:
        return tuple(SCOPES)

    def _save(self, creds: Credentials) -> None:
        USER_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Credentials contain secrets; only the current OS user may read them.
        fd = os.open(USER_TOKEN_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as token:
            token.write(creds.to_json())
