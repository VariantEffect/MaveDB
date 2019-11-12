from django.test import TestCase
from django.core.management import call_command
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from accounts.factories import UserFactory
from dataset.factories import ScoreSetFactory
from metadata.factories import PubmedIdentifierFactory
from metadata.models import PubmedIdentifier
from dataset import constants


class TestAddPmidCommand(TestCase):
    def test_value_error_invalid_urn(self):
        with self.assertRaises(ValueError):
            call_command("addpmid", pmid="25075907", urn=None)

    def test_validation_error_invalid_pmid(self):
        instance = ScoreSetFactory()

        with self.assertRaises(ValidationError):
            call_command("addpmid", pmid="abc", urn=instance.urn)

        with self.assertRaises(ValueError):
            call_command("addpmid", pmid=None, urn=instance.urn)

    def test_retrieves_existing_pmid(self):
        instance = ScoreSetFactory()
        pmid = "25075907"
        PubmedIdentifier.objects.all().delete()
        PubmedIdentifierFactory(identifier=pmid)

        self.assertEqual(PubmedIdentifier.objects.count(), 1)
        call_command("addpmid", pmid=pmid, urn=instance.urn)

        pmid_instance = PubmedIdentifier.objects.first()
        self.assertEqual(PubmedIdentifier.objects.count(), 1)
        self.assertEqual(pmid_instance.identifier, pmid)
        self.assertIsNotNone(pmid_instance.reference_html)
        self.assertIn(pmid_instance, instance.pubmed_ids.all())

    def test_creates_new_pmid(self):
        instance = ScoreSetFactory()
        pmid = "25075907"
        PubmedIdentifier.objects.all().delete()

        self.assertEqual(PubmedIdentifier.objects.count(), 0)
        call_command("addpmid", pmid=pmid, urn=instance.urn)

        pmid_instance = PubmedIdentifier.objects.first()
        self.assertEqual(PubmedIdentifier.objects.count(), 1)
        self.assertEqual(pmid_instance.identifier, pmid)
        self.assertIsNotNone(pmid_instance.reference_html)
        self.assertIn(pmid_instance, instance.pubmed_ids.all())


class TestAddUserCommand(TestCase):
    def test_error_invalid_urn(self):
        user = UserFactory()

        with self.assertRaises(ValueError):
            call_command(
                "adduser",
                user=user.username,
                urn=None,
                role=constants.administrator,
            )

    def test_error_urn_doesnt_exist(self):
        user = UserFactory()
        with self.assertRaises(ObjectDoesNotExist):
            call_command(
                "adduser",
                user=user.username,
                urn="urn:mavedb:00000001-a-1",
                role=constants.administrator,
            )

    def test_error_invalid_username(self):
        instance = ScoreSetFactory()
        with self.assertRaises(ValueError):
            call_command(
                "adduser",
                user=None,
                urn=instance.urn,
                role=constants.administrator,
            )

    def test_error_user_doesnt_exist(self):
        instance = ScoreSetFactory()
        with self.assertRaises(ObjectDoesNotExist):
            call_command(
                "adduser",
                user="user_a",
                urn=instance.urn,
                role=constants.administrator,
            )

    def test_error_invalid_role(self):
        user = UserFactory()
        instance = ScoreSetFactory()

        with self.assertRaises(ValueError):
            call_command(
                "adduser",
                user=user.username,
                urn=instance.urn,
                role="not a role",
            )

    def test_adds_user_to_role(self):
        user = UserFactory()
        instance = ScoreSetFactory()

        call_command(
            "adduser",
            user=user.username,
            urn=instance.urn,
            role=constants.administrator,
        )
        self.assertIn(user, instance.administrators)
        self.assertNotIn(user, instance.editors)
        self.assertNotIn(user, instance.viewers)

        call_command(
            "adduser",
            user=user.username,
            urn=instance.urn,
            role=constants.editor,
        )
        self.assertIn(user, instance.editors)
        self.assertNotIn(user, instance.administrators)
        self.assertNotIn(user, instance.viewers)

        call_command(
            "adduser",
            user=user.username,
            urn=instance.urn,
            role=constants.viewer,
        )
        self.assertIn(user, instance.viewers)
        self.assertNotIn(user, instance.administrators)
        self.assertNotIn(user, instance.editors)
