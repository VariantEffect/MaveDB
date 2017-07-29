
"""
Functional testing suite that will test that the login/logout process works
as intended and responds appropriately invalid credentials. Also tests
the process of resetting a password.
"""

from .base import FunctionalTest


class LoginLogoutFunctionalTest(FunctionalTest):

    def setUp(self):
        FunctionalTest.setUp(self)

    def test_signup_functionality(self):
        # Farva opens a new browser, eager to try the new MAVEDB website.
        self.browser.get(self.live_server_url + '/accounts/register/')
        self.browser.set_window_size(1024, 768)
