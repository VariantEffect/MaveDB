
"""
Functional testing suite that will test that the registration process works
as intended and responds appropriately to invalid input.
"""

from .base import FunctionalTest


class RegistrationFunctionalTest(FunctionalTest):

    def setUp(self):
        FunctionalTest.setUp(self)

    def test_signup_functionality(self):
        # Farva opens a new browser, eager to try the new MAVEDB website.
        self.browser.get(self.live_server_url + '/accounts/register/')
        self.browser.set_window_size(1024, 768)

        # Farva loves the new site and decides to sign-up
        form = self.browser.find_element_by_id("register-form")
        email = self.browser.find_element_by_id("email-input")
        password1 = self.browser.find_element_by_id("password-1-input")
        password2 = self.browser.find_element_by_id("password-2-input")

        # Hastily, he enters his details but miss-types his email.
        email.send_keys("farva@gmail.com")
        password1.send_keys("password")
        password2.send_keys("password")
        form.submit()

        # A red alert element pops up on the sign-up page instructing
        # Farva to correct his email address.

        # He corrects the fault but this time incorrectly enters the seconds
        # password

        # A red alert element pops up on the sign-up page instructing
        # Farva to type in matching passwords.

        # Finally, he successfully types in his information and creates a new
        # account, which redirects him to his personal profile page.

        # In an unfortunate accident involving a can of creamed corn soup,
        # Farva losses his memory from the previous day. He attempts to create
        # another account the following day.
        email.send_keys("farva@gmail.com")
        password1.send_keys("password")
        password2.send_keys("password")
        form.submit()

        # A red alert element pops up on the sign-up page instructing
        # Farva that the input email address is already in use.

        # Confused, he closes the browser and decides to contemplate life.
        