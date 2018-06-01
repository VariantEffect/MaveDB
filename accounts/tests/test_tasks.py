from django.test import RequestFactory, TestCase
from django.core import mail
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist

from dataset.factories import ExperimentFactory, ScoreSetFactory

from main.context_processors import baseurl

from variant.factories import VariantFactory

from ..factories import UserFactory
from ..tasks import notify_user_group_change, email_user, notify_user_upload_status


class TestNotifyUserGroupChangeTask(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_full_url_rendererd_in_template(self):
        user = UserFactory()
        request = self.factory.get("/profile/")
        request.user = user
        instance = ExperimentFactory()
        base = baseurl(request)['BASE_URL']
        notify_user_group_change(base, user, instance, 'added', 'administrator')
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
        notify_user_group_change(base, user, instance, 'added', 'administrator')
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
        notify_user_group_change(base, user, instance, 'added', 'administrator')
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
        notify_user_group_change(base, user, instance, 'added', 'administrator')
        self.assertEqual(len(mail.outbox), 0)

    def test_raise_error_cannot_find_instance(self):
        user = UserFactory()
        request = self.factory.get("/profile/")
        request.user = user
        base = baseurl(request)['BASE_URL']
        with self.assertRaises(ObjectDoesNotExist):
            notify_user_group_change(
                base, user, user, 'added', 'administrator')
            
    def test_retuns_if_not_instance_is_variant(self):
        user = UserFactory()
        request = self.factory.get("/profile/")
        request.user = user
        base = baseurl(request)['BASE_URL']
        
        instance = VariantFactory()
        notify_user_group_change(
            base, user, instance.urn, 'added', 'administrator')
        self.assertEqual(len(mail.outbox), 0)
        

class TestEmailUserTask(TestCase):
    def test_send_email(self):
        user1 = UserFactory()
        email_user(
            user1.pk, subject="Hello world",
            message="foo bar", from_email='someone@mail.com')
        self.assertEqual(len(mail.outbox), 1)
    
    def test_send_email_prefers_profile_email(self):
        user1 = UserFactory()
        profile = user1.profile
        profile.email = "hello@net.com"
        profile.save()
        
        email_user(
            user1.pk, subject="Hello world",
            message="foo bar", from_email='someone@mail.com')
        self.assertEqual(mail.outbox[0].to, [user1.profile.email])
    
    def test_send_email_falls_back_to_user_email(self):
        user1 = UserFactory()
        profile = user1.profile
        profile.email = None
        profile.save()
        
        email_user(
            user1.pk, subject="Hello world",
            message="foo bar", from_email='someone@mail.com')
        self.assertEqual(mail.outbox[0].to, [user1.email])
    
    def test_no_email_found_sends_no_email(self):
        user1 = UserFactory()
        user1.email = ""
        user1.save()
        
        profile = user1.profile
        profile.email = ""
        profile.save()
        
        email_user(
            user1.pk, subject="Hello world",
            message="foo bar", from_email='someone@mail.com')
        self.assertEqual(len(mail.outbox), 0)


class TestNotifyUserUploadStatusTask(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.scoreset = ScoreSetFactory()

    def test_renders_url_correctly(self):
        notify_user_upload_status.apply(kwargs=dict(
            user_pk=self.user.pk, scoreset_urn=self.scoreset.urn,
            base_url="http://base", success=True))
        expected = "http://base" + \
                   reverse("dataset:scoreset_detail", args=(self.scoreset.urn,))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(expected, mail.outbox[0].body)

    def test_delegates_correct_template_fail(self):
        notify_user_upload_status.apply(
            kwargs=dict(user_pk=self.user.pk, success=False,
                        scoreset_urn=self.scoreset.urn, base_url="http://base"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("could not be processed", mail.outbox[0].body)

    def test_delegates_correct_template_success(self):
        notify_user_upload_status.apply(kwargs=dict(
            user_pk=self.user.pk, scoreset_urn=self.scoreset.urn,
            base_url="http://base", success=True))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("has been processed successfully", mail.outbox[0].body)
