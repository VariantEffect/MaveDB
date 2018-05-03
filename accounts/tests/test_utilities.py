from django.test import RequestFactory, TestCase
from django.core import mail

from dataset.factories import ExperimentFactory

from main.context_processors import baseurl

from variant.factories import VariantFactory

from ..factories import UserFactory
from ..utilities import notify_user


class TestNotifyUser(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_full_url_rendererd_in_template(self):
        user = UserFactory()
        request = self.factory.get("/profile/")
        request.user = user
        instance = ExperimentFactory()
        base = baseurl(request)['BASE_URL']
        notify_user(base, user, instance, 'added', 'administrator')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            '{}/experiment/{}'.format(base, instance.urn),
            mail.outbox[0].body
        )

    def test_uses_profile_email_over_user_email(self):
        user = UserFactory()
        user.profile.email = 'email@email.com'
        user.profile.save()
        request = self.factory.get("/profile/")
        request.user = user
        instance = ExperimentFactory()
        base = baseurl(request)['BASE_URL']
        notify_user(base, user, instance, 'added', 'administrator')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.profile.email, mail.outbox[0].to)

    def test_falls_back_to_user_email(self):
        user = UserFactory()
        user.profile.email = None
        user.profile.save()
        request = self.factory.get("/profile/")
        request.user = user
        instance = ExperimentFactory()
        base = baseurl(request)['BASE_URL']
        notify_user(base, user, instance, 'added', 'administrator')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].to)

    def test_skips_if_no_email(self):
        user = UserFactory()
        user.profile.email = None
        user.profile.save()
        user.email = None
        request = self.factory.get("/profile/")
        request.user = user
        instance = ExperimentFactory()
        base = baseurl(request)['BASE_URL']
        notify_user(base, user, instance, 'added', 'administrator')
        self.assertEqual(len(mail.outbox), 0)

    def test_returns_if_not_a_valid_instance(self):
        user = UserFactory()
        request = self.factory.get("/profile/")
        request.user = user
        base = baseurl(request)['BASE_URL']
        notify_user(base, user, user, 'added', 'administrator')
        self.assertEqual(len(mail.outbox), 0)

        instance = VariantFactory()
        notify_user(base, user, instance, 'added', 'administrator')
        self.assertEqual(len(mail.outbox), 0)
