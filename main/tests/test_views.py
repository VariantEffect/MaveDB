
"""
Testing suite for main app views
"""

from django.test import TestCase


class HomePageTest(TestCase):

    def test_uses_home_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'main/home.html')

    def test_home_page_uses_base_template(self):
        response = self.client.get('/')
        self.assertContains(response, "bodyBlock")
