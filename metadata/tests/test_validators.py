from django.test import TestCase
from django.core.exceptions import ValidationError

from ..validators import (
    validate_doi_identifier,
    validate_doi_list,
    validate_keyword,
    validate_keyword_list,
    validate_pubmed_identifier,
    validate_pubmed_list,
    validate_sra_identifier,
    validate_sra_list
)


class TestDOIValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid DOI as well as detecting correct DOIs
    """
    def test_ve_invalid_doi(self):
        with self.assertRaises(ValidationError):
            validate_doi_identifier('doi: 10.1016')

    def test_ve_invalid_doi_in_list(self):
        with self.assertRaises(ValidationError):
            validate_doi_list(
                ['doi: 10.1016', '10.1016/j.cels.2018.01.015'])


class TestPubmedValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid PubMed as well as detecting correct PubMeds
    """
    def test_ve_invalid_pmid(self):
        with self.assertRaises(ValidationError):
            validate_pubmed_identifier('0.1')

    def test_ve_invalid_pmid_in_list(self):
        with self.assertRaises(ValidationError):
            validate_pubmed_list(['1234', '0.1'])


class TestSRAValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid SRAs as well as detecting correct SRAs
    """
    def test_ve_invalid_sra(self):
        with self.assertRaises(ValidationError):
            validate_sra_identifier('SRXP0001')

    def test_ve_invalid_sra_in_list(self):
        with self.assertRaises(ValidationError):
            validate_sra_list(['SRX3407686', 'SRXPPPPP0001'])

    def test_passes_valid_bioproject_sra(self):
        self.fail("Write this test.")

    def test_passes_valid_run_sra(self):
        self.fail("Write this test.")

    def test_passes_valid_study_sra(self):
        self.fail("Write this test.")

    def test_passes_valid_experiment_sra(self):
        self.fail("Write this test.")


class TestEnsemblValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid Ensembl as well as detecting correct Ensembl ids.
    """
    def test_ve_invalid_ensembl_id(self):
        self.fail("Write this test.")

    def test_ve_invalid_ensembl_list(self):
        self.fail("Write this test.")

    def test_passes_valid_gene(self):
        self.fail("Write this test.")

    def test_passes_valid_protein(self):
        self.fail("Write this test.")

    def test_passes_valid_genome(self):
        self.fail("Write this test.")

    def test_passes_valid_exon(self):
        self.fail("Write this test.")

    def test_passes_valid_transcript(self):
        self.fail("Write this test.")


class TestRefSeqValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid RefSeq as well as detecting correct RefSeq ids.
    """
    def test_ve_invalid_refseq_id(self):
        self.fail("Write this test.")

    def test_ve_invalid_refseq_list(self):
        self.fail("Write this test.")

    def test_passes_valid_genomic_id(self):
        self.fail("Write this test.")

    def test_passes_valid_protein_id(self):
        self.fail("Write this test.")

    def test_passes_valid_mrna_id(self):
        self.fail("Write this test.")

    def test_passes_valid_rna_id(self):
        self.fail("Write this test.")

    def test_passes_valid_complete_genome(self):
        self.fail("Write this test.")


class TestUniprotValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid Uniprot as well as detecting correct Uniprot ids.
    """
    def test_ve_invalid_uniprot_id(self):
        self.fail("Write this test.")

    def test_ve_invalid_uniprot_list(self):
        self.fail("Write this test.")

    def test_passes_valid_uniprot_id(self):
        self.fail("Write this test.")


class TestKeywordValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid input.
    """
    def test_ve_invalid_keyword(self):
        with self.assertRaises(ValidationError):
            validate_keyword(555)

    def test_ve_invalid_keyword_in_list(self):
        with self.assertRaises(ValidationError):
            validate_keyword_list(['protein', 555])
