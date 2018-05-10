import reversion
from reversion.models import Version

from django.test import TestCase

from accounts.factories import UserFactory

from metadata.factories import (
    KeywordFactory,
    PubmedIdentifierFactory,
    SraIdentifierFactory,
    DoiIdentifierFactory,
)

from dataset import factories

from ..utilities.versioning import track_changes, revert


class TestVersionControl(TestCase):

    def test_new_version_NOT_created_when_there_are_no_changes(self):
        instance = factories.ScoreSetWithTargetFactory()
        self.assertEqual(Version.objects.count(), 0)

        track_changes(instance, None)
        self.assertEqual(Version.objects.count(), 1)

        track_changes(instance, None)
        self.assertEqual(Version.objects.count(), 1)

    def test_new_version_created_if_fields_have_changed(self):
        instance = factories.ScoreSetWithTargetFactory()
        self.assertEqual(Version.objects.count(), 0)

        track_changes(instance, None)
        self.assertEqual(Version.objects.count(), 1)

        instance.abstract_text = ""
        instance.save()
        track_changes(instance, None)
        self.assertEqual(Version.objects.count(), 2)

    def test_formats_comment_with_field_name_and_user(self):
        with reversion.create_revision():
            instance = factories.ScoreSetWithTargetFactory()

        instance.abstract_text = ""
        instance.keywords.clear()
        instance.save()
        user = UserFactory()

        with reversion.create_revision():
            track_changes(instance, user)
            self.assertIn(user.username, reversion.get_comment())
            self.assertIn('abstract_text', reversion.get_comment())
            self.assertIn('keywords', reversion.get_comment())

    def test_revert_also_reverts_m2m_fields(self):
        original = factories.ScoreSetWithTargetFactory()
        with reversion.create_revision():
            original.save()

        original_kw = original.keywords.first()
        original_pm = original.pubmed_ids.first()
        original_sra = original.sra_ids.first()
        original_doi = original.doi_ids.first()

        kw = KeywordFactory()
        while kw.text == original_kw.text:
            kw = KeywordFactory()

        pm = PubmedIdentifierFactory()
        while pm.id == original_pm.id:
            pm = PubmedIdentifierFactory()

        sra = SraIdentifierFactory()
        while sra.id == original_sra.id:
            sra = SraIdentifierFactory()

        doi = DoiIdentifierFactory()
        while doi.id == original_doi.id:
            doi = DoiIdentifierFactory()

        original.abstract_text = ""
        original.keywords.add(kw)
        original.add_identifier(pm)
        original.add_identifier(doi)
        original.add_identifier(sra)
        original.save()

        instance = revert(original)
        self.assertNotIn(kw, instance.keywords.all())
        self.assertNotIn(sra, instance.sra_ids.all())
        self.assertNotIn(doi, instance.doi_ids.all())
        self.assertNotIn(pm, instance.pubmed_ids.all())

        self.assertIn(original_kw, instance.keywords.all())
        self.assertIn(original_sra, instance.sra_ids.all())
        self.assertIn(original_doi, instance.doi_ids.all())
        self.assertIn(original_pm, instance.pubmed_ids.all())

        self.assertEqual(original.abstract_text, instance.abstract_text)

    def test_revert_saves_new_revision(self):
        original = factories.ScoreSetWithTargetFactory()
        with reversion.create_revision():
            original.save()

        self.assertEqual(Version.objects.count(), 1)
        revert(original)
        self.assertEqual(Version.objects.count(), 2)

    def test_revert_adds_comment(self):
        original = factories.ScoreSetWithTargetFactory()
        with reversion.create_revision():
            original.save()

        prev = Version.objects.get_for_object(original)[0]
        revert(original)
        new = Version.objects.get_for_object(original)[0]

        self.assertIn(str(prev.revision.user), new.revision.comment)
        self.assertIn(str(prev.revision.date_created), new.revision.comment)
        self.assertIn(str(prev.revision.id), new.revision.comment)