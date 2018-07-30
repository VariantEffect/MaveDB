import idutils
import metapub

from django.db import IntegrityError
from django.test import TestCase

from genome.factories import TargetGeneFactory, ReferenceGenomeFactory
from dataset.factories import ExperimentFactory, ScoreSetFactory, ExperimentSetFactory

from ..models import Keyword
from ..factories import (
    KeywordFactory, DoiIdentifierFactory,
    PubmedIdentifierFactory, SraIdentifierFactory,
    UniprotIdentifierFactory, EnsemblIdentifierFactory,
    RefseqIdentifierFactory, GenomeIdentifierFactory,
    UniprotOffsetFactory, RefseqOffsetFactory, EnsemblOffsetFactory,
    UniprotOffset, RefseqOffset, EnsemblOffset
)


class TestM2MRelationships(TestCase):
    """
    Tests that M2M relationships behave as expected. Uses :class:`Keyword`
    as the driver of :class:`..models.ExternalIdentifier`
    """
    def setUp(self):
        self.exp_1 = ExperimentFactory()
        self.exp_1.keywords.clear()
        self.exp_1.save()
        self.exp_2 = ExperimentFactory()
        self.exp_2.keywords.clear()
        self.exp_2.save()

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
        count_before = Keyword.objects.count()
        self.exp_1.delete()
        count_after = Keyword.objects.count()
        self.assertEqual(count_after, count_before)

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
            Keyword(text=keyword.text).save()

    def test_cannot_create_with_null_text(self):
        with self.assertRaises(IntegrityError):
            KeywordFactory(text=None)

    def test_is_attached_if_member_of_experiment(self):
        dataset = ExperimentFactory()
        dataset.experimentset.keywords.clear()
        dataset.experimentset.save()

        kw = dataset.keywords.first()
        self.assertTrue(kw.is_attached())
        dataset.delete()
        self.assertFalse(kw.is_attached())

    def test_is_attached_if_member_of_scoreset(self):
        dataset = ScoreSetFactory()
        dataset.experiment.keywords.clear()
        dataset.experiment.save()
        dataset.experiment.experimentset.keywords.clear()
        dataset.experiment.experimentset.save()

        kw = dataset.keywords.first()
        self.assertTrue(kw.is_attached())
        dataset.delete()
        self.assertFalse(kw.is_attached())

    def test_is_attached_if_member_of_experimentset(self):
        dataset = ExperimentSetFactory()
        kw = dataset.keywords.first()
        self.assertTrue(kw.is_attached())
        dataset.delete()
        self.assertFalse(kw.is_attached())
        
    def test_get_association_count(self):
        kw = KeywordFactory(text='blahblahblah')
        self.assertEqual(kw.get_association_count(), 0)
        
        exps = ExperimentSetFactory()
        _ = [kw.delete() for kw in exps.keywords.all()]
        exps.keywords.add(kw)
        self.assertEqual(kw.get_association_count(), 1)
        
        exp = ExperimentFactory()
        _ = [kw.delete() for kw in exp.keywords.all()]
        exp.keywords.add(kw)
        self.assertEqual(kw.get_association_count(), 2)
        
        scs = ScoreSetFactory()
        _ = [kw.delete() for kw in scs.keywords.all()]
        scs.keywords.add(kw)
        self.assertEqual(kw.get_association_count(), 3)
        
        exps.keywords.clear()
        exp.keywords.clear()
        scs.keywords.clear()
        self.assertEqual(kw.get_association_count(), 0)
        
        
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

    def test_is_attached_if_member_of_experiment(self):
        dataset = ExperimentFactory()
        dataset.experimentset.doi_ids.clear()
        dataset.experimentset.save()

        obj = dataset.doi_ids.first()
        self.assertTrue(obj.is_attached())
        dataset.delete()
        self.assertFalse(obj.is_attached())

    def test_is_attached_if_member_of_scoreset(self):
        dataset = ScoreSetFactory()
        dataset.experiment.doi_ids.clear()
        dataset.experiment.save()
        dataset.experiment.experimentset.doi_ids.clear()
        dataset.experiment.experimentset.save()

        obj = dataset.doi_ids.first()
        self.assertTrue(obj.is_attached())
        dataset.delete()
        self.assertFalse(obj.is_attached())

    def test_is_attached_if_member_of_experimentset(self):
        dataset = ExperimentSetFactory()

        obj = dataset.doi_ids.first()
        self.assertTrue(obj.is_attached())
        dataset.delete()
        self.assertFalse(obj.is_attached())


class TestSraIdentidier(TestCase):
    """
    Tests basic :class:`SraIdentifier` functionality, specifically that the
    `save` and `format_url` methods handle SRA instances correctly.
    """
    def test_format_url_creates_bioproject_ncbi_url(self):
        sra = SraIdentifierFactory(identifier='PRJNA362734')
        expected_url = (
            "http://www.ebi.ac.uk/ena/data/view/{}".format(sra.identifier)
        )
        self.assertEqual(sra.url, expected_url)

    def test_format_url_creates_study_ncbi_url(self):
        sra = SraIdentifierFactory(identifier='SRP3407687')
        expected_url = (
            "http://www.ebi.ac.uk/ena/data/view/{id}".format(id=sra.identifier)
        )
        self.assertEqual(sra.url, expected_url)

    def test_format_url_creates_experiment_ncbi_url(self):
        sra = SraIdentifierFactory(identifier='SRX3407687')
        expected_url = (
            "http://www.ebi.ac.uk/ena/data/view/{}".format(sra.identifier)
        )
        self.assertEqual(sra.url, expected_url)

    def test_format_url_creates_run_ncbi_url(self):
        sra = SraIdentifierFactory(identifier='SRR3407687')
        expected_url = (
            "http://www.ebi.ac.uk/ena/data/view/{id}".format(id=sra.identifier)
        )
        self.assertEqual(sra.url, expected_url)

    def test_save_sets_dbname_as_SRA(self):
        sra = SraIdentifierFactory()
        self.assertEqual(sra.dbname, sra.DATABASE_NAME)

    def test_is_attached_if_member_of_experiment(self):
        dataset = ExperimentFactory()
        dataset.experimentset.sra_ids.clear()
        dataset.experimentset.save()

        obj = dataset.sra_ids.first()
        self.assertTrue(obj.is_attached())
        dataset.delete()
        self.assertFalse(obj.is_attached())

    def test_is_attached_if_member_of_scoreset(self):
        dataset = ScoreSetFactory()
        dataset.experiment.sra_ids.clear()
        dataset.experiment.save()
        dataset.experiment.experimentset.sra_ids.clear()
        dataset.experiment.experimentset.save()

        obj = dataset.sra_ids.first()
        self.assertTrue(obj.is_attached())
        dataset.delete()
        self.assertFalse(obj.is_attached())

    def test_is_attached_if_member_of_experimentset(self):
        dataset = ExperimentSetFactory()
        obj = dataset.sra_ids.first()
        self.assertTrue(obj.is_attached())
        dataset.delete()
        self.assertFalse(obj.is_attached())


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
        pubmed = PubmedIdentifierFactory(reference_html=None)
        fetch = metapub.PubMedFetcher()
        article = fetch.article_by_pmid(pubmed.identifier)
        self.assertEqual(pubmed.reference_html, article.citation_html)

    def test_save_sets_dbname_as_PubMeD(self):
        pm = PubmedIdentifierFactory()
        self.assertEqual(pm.dbname, pm.DATABASE_NAME)

    def test_is_attached_if_member_of_experiment(self):
        dataset = ExperimentFactory()
        dataset.experimentset.pubmed_ids.clear()
        dataset.experimentset.save()

        obj = dataset.pubmed_ids.first()
        self.assertTrue(obj.is_attached())
        dataset.delete()
        self.assertFalse(obj.is_attached())

    def test_is_attached_if_member_of_scoreset(self):
        dataset = ScoreSetFactory()
        dataset.experiment.pubmed_ids.clear()
        dataset.experiment.save()
        dataset.experiment.experimentset.pubmed_ids.clear()
        dataset.experiment.experimentset.save()

        obj = dataset.pubmed_ids.first()
        self.assertTrue(obj.is_attached())
        dataset.delete()
        self.assertFalse(obj.is_attached())

    def test_is_attached_if_member_of_experimentset(self):
        dataset = ExperimentSetFactory()
        obj = dataset.pubmed_ids.first()
        self.assertTrue(obj.is_attached())
        dataset.delete()
        self.assertFalse(obj.is_attached())


class TestUniProtIdentifier(TestCase):

    def test_format_url_creates_url(self):
        obj = UniprotIdentifierFactory()
        url = obj.format_url()
        expected_url = idutils.to_url(obj.identifier, obj.IDUTILS_SCHEME)
        self.assertEqual(expected_url, url)

    def test_is_attached_if_associated_with_a_target(self):
        tg = TargetGeneFactory()
        obj = tg.uniprot_id
        self.assertTrue(obj.is_attached())
        tg.delete()
        self.assertFalse(obj.is_attached())

    def test_delete_deletes_associated_offset(self):
        offset = UniprotOffsetFactory()
        self.assertEqual(UniprotOffset.objects.count(), 1)
        offset.identifier.delete()
        self.assertEqual(UniprotOffset.objects.count(), 0)


class TestRefSeqIdentifier(TestCase):

    def test_format_url_creates_url(self):
        obj = RefseqIdentifierFactory()
        url = obj.format_url()
        expected_url = idutils.to_url(obj.identifier, obj.IDUTILS_SCHEME)
        self.assertEqual(expected_url, url)

    def test_is_attached_if_associated_with_a_target(self):
        tg = TargetGeneFactory()
        obj = tg.refseq_id
        self.assertTrue(obj.is_attached())
        tg.delete()
        self.assertFalse(obj.is_attached())

    def test_delete_deletes_associated_offset(self):
        offset = RefseqOffsetFactory()
        self.assertEqual(RefseqOffset.objects.count(), 1)
        offset.identifier.delete()
        self.assertEqual(RefseqOffset.objects.count(), 0)


class TestEnsemblIdentifier(TestCase):

    def test_format_url_creates_url(self):
        obj = EnsemblIdentifierFactory()
        url = obj.format_url()
        expected_url = idutils.to_url(obj.identifier, obj.IDUTILS_SCHEME)
        self.assertEqual(expected_url, url)

    def test_is_attached_if_associated_with_a_target(self):
        tg = TargetGeneFactory()
        obj = tg.ensembl_id
        self.assertTrue(obj.is_attached())
        tg.delete()
        self.assertFalse(obj.is_attached())

    def test_delete_deletes_associated_offset(self):
        offset = EnsemblOffsetFactory()
        self.assertEqual(EnsemblOffset.objects.count(), 1)
        offset.identifier.delete()
        self.assertEqual(EnsemblOffset.objects.count(), 0)


class TestGenomeIdentifier(TestCase):
    def test_format_url_creates_url(self):
        obj = GenomeIdentifierFactory()
        url = obj.format_url()
        expected_url = idutils.to_url(obj.identifier, obj.IDUTILS_SCHEME)
        self.assertEqual(expected_url, url)

    def test_is_attached_if_associated_with_a_genome(self):
        genome = ReferenceGenomeFactory()
        obj = genome.genome_id
        self.assertTrue(obj.is_attached())
        genome.delete()
        self.assertFalse(obj.is_attached())