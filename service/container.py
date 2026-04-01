from .gmail.auth import GmailAuth

_gmail_auth: GmailAuth =GmailAuth()
_timer_service =None
_gmail_service =None

def get_timer(loop=None):
    from .timer.timer import TimerService
    global _timer_service
    if _timer_service is None:
        if loop is None:
            raise RuntimeError("Service not initialized")
        _timer_service = TimerService(loop)
    return _timer_service

def get_gmail_service(creds=None,loop=None):
    from .gmail.service import GmailService
    global _gmail_service
    if _gmail_service is None:
        if (creds is None) or (loop is None):
            raise RuntimeError("Services not initialized")
        _gmail_service = GmailService(creds,loop)
    return _gmail_service


def get_gmail_auth() -> GmailAuth:
    global _gmail_auth
    if _gmail_auth is None:
        _gmail_auth = GmailAuth()
    return _gmail_auth