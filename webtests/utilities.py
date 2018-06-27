from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, \
    HASH_SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore


User = get_user_model()


STAGING = getattr(settings, 'STAGING', False)
PRODUCTION = getattr(settings, 'PRODUCTION', False)
STAGING_OR_PROD = STAGING or PRODUCTION
if STAGING:
    LOG_PATH = '../logs/geckodriver.log'
elif STAGING_OR_PROD:
    LOG_PATH = '/data/mavedb_project/mavedb/geckodriver.log'
else:
    LOG_PATH = './logs/geckodriver.log'
    

def authenticate_webdriver(username, password, test_class, drvr_attr):
    session_cookie = create_session_cookie(
        username=username,
        password=password
    )
    # Visit home page to trigger a Selenium setup first.
    getattr(test_class, drvr_attr).get(test_class.live_server_url)
    getattr(test_class, drvr_attr).add_cookie(session_cookie)
    getattr(test_class, drvr_attr).refresh()

    return test_class


def create_session_cookie(username, password):
    # First, create a new test user
    if User.objects.filter(username=username).count():
        user = User.objects.get(username=username)
        user.set_password(password)
        user.save()
    else:
        user = User.objects.create_user(username=username, password=password)

    # Then create the authenticated session using the new user credentials
    session = SessionStore()
    session[SESSION_KEY] = user.pk
    session[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    # Finally, create the cookie dictionary
    cookie = {
        'name': settings.SESSION_COOKIE_NAME,
        'value': session.session_key,
        'secure': False,
        'path': '/',
    }
    return cookie
