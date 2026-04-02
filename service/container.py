_gmail_auth=None
_timer_service =None
_gmail_service =None
_loop=None

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
    from .gmail.service import GmailService
    global _gmail_service,_loop
    if _gmail_service is None:
        if (creds is None) or (_loop is None):
            raise RuntimeError("Services not initialized")
        _gmail_service = GmailService(creds,_loop)
    return _gmail_service


def get_gmail_auth():
    from .gmail.auth import GmailAuth
    global _gmail_auth
    if _gmail_auth is None:
        _gmail_auth = GmailAuth()
    return _gmail_auth