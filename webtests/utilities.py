from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, \
    HASH_SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore



User = get_user_model()


def authenticate_webdriver(username, password, test_class):
    session_cookie = create_session_cookie(
        username=username,
        password=password
    )
    # Visit your domain to setup Selenium.
    test_class.selenium.get(test_class.live_server_url)

    # Add the newly created session cookie to selenium webdriver.
    test_class.selenium.add_cookie(session_cookie)

    # Refresh to exchange cookies with the server.
    test_class.selenium.refresh()

    return test_class


def create_session_cookie(username, password):

    # First, create a new test user
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