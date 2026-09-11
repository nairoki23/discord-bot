from dotenv import dotenv_values


config = dotenv_values(".env")

_google_auth = None
_timer_service = None
_gmail_service = None
_google_calendar_service = None
_loop = None

def set_loop(loop):
    global _loop
    _loop=loop
def get_timer():

    from .timer.timer import TimerService
    global _timer_service,_loop
    if _timer_service is None:
        if _loop is None:
            raise RuntimeError("Service not initialized")
        _timer_service = TimerService(_loop)
    return _timer_service

def get_gmail_service(creds=None):
    from .google.gmail import GmailService
    global _gmail_service,_loop
    if _gmail_service is None:
        if (creds is None) or (_loop is None):
            raise RuntimeError("Services not initialized")
        _gmail_service = GmailService(creds,_loop)
    return _gmail_service


def get_google_auth():
    from .google import GoogleAuth
    global _google_auth
    if _google_auth is None:
        _google_auth = GoogleAuth()
    return _google_auth


def get_google_calendar_service():
    """Return the shared Google Calendar service.

    Calendar and Gmail deliberately share the same GoogleAuth instance, so a
    refreshed OAuth credential is immediately available to both integrations.
    """
    from .google.calendar import GoogleCalendarService

    global _google_calendar_service
    if _google_calendar_service is None:
        auth = get_google_auth()
        _google_calendar_service = GoogleCalendarService(
            auth.get_creds,
            calendar_id=config.get("GOOGLE_CALENDAR_ID") or "primary",
            timezone=config.get("GOOGLE_CALENDAR_TIMEZONE") or "Asia/Tokyo",
        )
    return _google_calendar_service
