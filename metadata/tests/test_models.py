import idutils

from django.db import IntegrityError
from django.test import TestCase

from dataset.factories import ExperimentFactory

from ..models import Keyword
from ..factories import (
    KeywordFactory, DoiIdentifierFactory,
    PubmedIdentifierFactory, SraIdentifierFactory
)


class TestM2MRelationships(TestCase):
    """
    Tests that M2M relationships behave as expected. Uses :class:`Keyword`
    as the driver of :class:`..models.ExternalIdentifier`
    """
    def setUp(self):
        self.exp_1 = ExperimentFactory()
        self.exp_2 = ExperimentFactory()

    def test_can_associate_multiple_keywords_with_dataset(self):
        kw1 = KeywordFactory()
        kw2 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_1.keywords.add(kw2)
        self.assertEqual(self.exp_1.keywords.count(), 2)

    def test_can_associate_keyword_with_multiple_datasets(self):
        kw1 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_2.keywords.add(kw1)
        self.assertEqual(self.exp_1.keywords.count(), 1)
        self.assertEqual(self.exp_2.keywords.count(), 1)

    def test_cant_add_duplicate_keywords_to_dataset(self):
        kw1 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_1.keywords.add(kw1)
        self.assertEqual(self.exp_1.keywords.count(), 1)

    def test_delete_experiment_doesnt_delete_kw(self):
        kw1 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_1.delete()
        self.assertEqual(Keyword.objects.count(), 1)

    def test_deleted_keyword_removed_from_experiment_keywords(self):
        kw1 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_1.save()
        self.exp_1.refresh_from_db()
        self.assertEqual(self.exp_1.keywords.count(), 1)

        kw1.delete()
        self.exp_1.save()
        self.exp_1.refresh_from_db()
        self.assertEqual(self.exp_1.keywords.count(), 0)


class TestKeyword(TestCase):
    """
    Tests basic :class:`Keyword` functionality and checks to ensure
    database integrity is maintained (no duplicates, null text, etc).
    """
    def test_cannot_create_duplicates(self):
        keyword = KeywordFactory()
        with self.assertRaises(IntegrityError):
            KeywordFactory(text=keyword.text)

    def test_cannot_create_with_null_text(self):
        with self.assertRaises(IntegrityError):
            KeywordFactory(text=None)


class TestDoiIdentifierModel(TestCase):
    """
    Tests basic :class:`DoiIdentifier` functionality, specifically that the
    `save` and `format_url` methods handle DOI instances correctly.
    """
    def test_format_url_creates_doi_url(self):
        doi = DoiIdentifierFactory()
        url = doi.format_url()
        expected_url = idutils.to_url(doi.identifier, doi.IDUTILS_SCHEME)
        self.assertEqual(expected_url, url)

    def test_save_normalises_doi(self):
        doi = DoiIdentifierFactory()
        expected_id = idutils.normalize_pid(
            doi.identifier, doi.IDUTILS_SCHEME)
        self.assertEqual(expected_id, doi.identifier)

    def test_save_sets_dbname_as_DOI(self):
        doi = DoiIdentifierFactory()
        self.assertEqual(doi.dbname, doi.DATABASE_NAME)


class TestSraIdentidier(TestCase):
    """
    Tests basic :class:`SraIdentifier` functionality, specifically that the
    `save` and `format_url` methods handle SRA instances correctly.
    """
    def test_format_url_creates_bioproject_ncbi_url(self):
        sra = SraIdentifierFactory(identifier='PRJNA362734')
        expected_url = (
            "https://www.ncbi.nlm.nih.gov/"
            "bioproject/{id}".format(id=sra.identifier)
        )
        self.assertEqual(sra.url, expected_url)

    def test_format_url_creates_study_ncbi_url(self):
        sra = SraIdentifierFactory(identifier='SRP3407687')
        expected_url = (
            "http://trace.ncbi.nlm.nih.gov/"
            "Traces/sra/sra.cgi?study={id}"
            "".format(id=sra.identifier)
        )
        self.assertEqual(sra.url, expected_url)

    def test_format_url_creates_experiment_ncbi_url(self):
        sra = SraIdentifierFactory(identifier='SRX3407687')
        expected_url = (
            "https://www.ncbi.nlm.nih.gov/"
            "sra/{id}?report=full".format(id=sra.identifier)
        )
        self.assertEqual(sra.url, expected_url)

    def test_format_url_creates_run_ncbi_url(self):
        sra = SraIdentifierFactory(identifier='SRR3407687')
        expected_url = (
            "http://trace.ncbi.nlm.nih.gov/"
            "Traces/sra/sra.cgi?"
            "cmd=viewer&m=data&s=viewer&run={id}"
            "".format(id=sra.identifier)
        )
        self.assertEqual(sra.url, expected_url)

    def test_save_sets_dbname_as_SRA(self):
        sra = SraIdentifierFactory()
        self.assertEqual(sra.dbname, sra.DATABASE_NAME)


class TestPubmedIdentifier(TestCase):
    """
    Tests basic :class:`PubmedIdentifier` functionality, specifically that the
    `save`,`format_url` and `format_reference_html` methods handle PubMed
    instances correctly.
    """
    def test_format_url_creates_pubmed_url(self):
        pubmed = PubmedIdentifierFactory()
        url = pubmed.format_url()
        expected_url = idutils.to_url(pubmed.identifier, pubmed.IDUTILS_SCHEME)
        self.assertEqual(expected_url, url)

    def test_save_normalises_pubmed(self):
        pubmed = PubmedIdentifierFactory()
        expected_id = idutils.normalize_pid(
            pubmed.identifier, pubmed.IDUTILS_SCHEME)
        self.assertEqual(expected_id, pubmed.identifier)

    def test_format_reference_url_hyperlinks_references(self):
        self.fail(
            "Implement this when format_reference_html "
            "has been implemented"
        )

    def test_save_sets_dbname_as_PubMeD(self):
        pm = PubmedIdentifierFactory()
        self.assertEqual(pm.dbname, pm.DATABASE_NAME)
