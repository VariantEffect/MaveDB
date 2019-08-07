from datetime import datetime, timedelta
from numpy import NaN

from django.conf import settings
from django.test import TestCase, mock

from core.utilities import null_values_list

from accounts.factories import UserFactory
from dataset.factories import ScoreSetFactory
from dataset import constants

from ..utilities import notify_admins, is_null, format_delta, base_url


class TestBaseUrl(TestCase):
    class MockHTTPRequest:
        def is_secure(self):
            return False

    class MockHTTPSRequest:
        def is_secure(self):
            return True

    def test_adds_https_secure(self):
        self.assertIn("https:", base_url(request=self.MockHTTPSRequest()))

    def test_adds_http_not_secure(self):
        self.assertIn("http:", base_url(request=self.MockHTTPRequest()))

    def test_adds_http_no_request(self):
        self.assertIn("http:", base_url(request=self.MockHTTPRequest()))


class TestNotifyAdmins(TestCase):
    @mock.patch("core.tasks.send_mail.apply_async")
    def test_send_admin_email_emails_all_admins(self, patch):
        user1 = UserFactory()
        user1.is_superuser = True
        user1.save()

        user2 = UserFactory()
        user2.is_superuser = True
        user2.save()

        obj = ScoreSetFactory()

        notify_admins(user1, obj)
        patch.assert_called()
        self.assertEqual(patch.call_count, 2)
        exptected = "http://{}/scoreset/{}/".format(settings.BASE_URL, obj.urn)
        self.assertIn(exptected, patch.call_args[1]["kwargs"]["message"])


class TestIsNull(TestCase):
    def test_detects_null(self):
        for c in null_values_list:
            self.assertTrue(is_null(c))

    def test_detects_none(self):
        self.assertTrue(is_null(None))

    def test_detects_nan(self):
        self.assertTrue(is_null(NaN))

    def test_detects_empty(self):
        self.assertTrue(is_null("  "))

    def test_false_non_null_value(self):
        self.assertFalse(is_null("hello world"))


class TestFormatDelta(TestCase):
    def test_correctly_deduces_today(self):
        ta = datetime.now()
        res = format_delta(ta)
        self.assertIn("today", res)

    def test_correctly_deduces_elapsed_days_unit(self):
        ta = datetime.now()
        tb = ta + timedelta(days=1)
        res = format_delta(ta, tb)
        self.assertIn("day", res)

    def test_correctly_deduces_elapsed_years_unit(self):
        ta = datetime.now()
        tb = ta + timedelta(days=450)
        res = format_delta(ta, tb)
        self.assertIn("year", res)

    def test_correctly_deduces_elapsed_months_unit(self):
        ta = datetime.now()
        tb = ta + timedelta(days=32)
        res = format_delta(ta, tb)
        self.assertIn("month", res)

    def test_correctly_deduces_elapsed_weeks_unit(self):
        ta = datetime.now()
        tb = ta + timedelta(days=8)
        res = format_delta(ta, tb)
        self.assertIn("week", res)

    def test_correctly_deduces_plurality(self):
        ta = datetime.now()
        tb = ta + timedelta(days=2)
        res = format_delta(ta, tb)
        self.assertIn("days", res)
