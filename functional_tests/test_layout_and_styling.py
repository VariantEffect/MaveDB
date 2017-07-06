
"""
Functional testing suite that will test that templates are loading
correctly and css/javascript is functioning as intended from the perspective
of a prospective user.
"""

from .base import FunctionalTest


class LayoutAndStylingTest(FunctionalTest):
    
    def test_base_template_layout_and_styling(self):
        # Farva opens a new browser, eager to try the new MAVEDB website.
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1024, 768)

        # The first thing he notices are the lovely navigation bars at the top
        # and bottom of the page.
        header = self.browser.find_element_by_id('navHeader')
        footer = self.browser.find_element_by_id('navFooter')

        # Farva, briefly stuck in a moment of awe caused by the unparalleled
        # beauty of the navigation bar, finally falls back to the realm of
        # reality. He sees links to 'MaveDB', 'Search', 'Upload', 'Help' and
        # 'Login/Register' pages contained within the navigation header.
