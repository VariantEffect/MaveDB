from django.test import TestCase

from ..templatetags import licence_tags
from .. import models


class TestLicenceTags(TestCase):
    def test_correct_path_cc0(self):
        l = models.Licence.get_cc0()
        path = licence_tags.get_licence_logo_path(l)
        self.assertIn('cc-zero.svg', path)

    def test_correct_path_by_nc_sa(self):
        l = models.Licence.get_cc4()
        path = licence_tags.get_licence_logo_path(l)
        self.assertIn('by-nc-sa.svg', path)

    def test_error_unknown_licence(self):
        l = models.Licence.get_cc4()
        l.short_name = 'by-sa'
        with self.assertRaises(ValueError):
            licence_tags.get_licence_logo_path(l)
