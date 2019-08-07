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
    validate_sra_list,
    validate_uniprot_list,
    validate_uniprot_identifier,
    validate_refseq_identifier,
    validate_refseq_list,
    validate_genome_identifier,
    validate_ensembl_identifier,
    validate_ensembl_list,
)


class TestDOIValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid DOI as well as detecting correct DOIs
    """

    def test_ve_invalid_doi(self):
        with self.assertRaises(ValidationError):
            validate_doi_identifier("doi: 10.1016")

    def test_ve_invalid_doi_in_list(self):
        with self.assertRaises(ValidationError):
            validate_doi_list(["doi: 10.1016", "10.1016/j.cels.2018.01.015"])


class TestGenomeValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid Genome assemblies as well as detecting correct ones.
    """

    def test_ve_invalid(self):
        with self.assertRaises(ValidationError):
            validate_genome_identifier("GCF_000146045")

    def test_passes_valid(self):
        validate_genome_identifier("GCF_000001405.11")
        validate_genome_identifier("GCA_000001405.11")


class TestPubmedValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid PubMed as well as detecting correct PubMeds
    """

    def test_ve_invalid_pmid(self):
        with self.assertRaises(ValidationError):
            validate_pubmed_identifier("0.1")

    def test_ve_invalid_pmid_in_list(self):
        with self.assertRaises(ValidationError):
            validate_pubmed_list(["1234", "0.1"])

    def test_passes_valid_id(self):
        validate_pubmed_identifier("29103961")


class TestSRAValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid SRAs as well as detecting correct SRAs
    """

    def test_ve_invalid_sra(self):
        with self.assertRaises(ValidationError):
            validate_sra_identifier("SRXP0001")

    def test_ve_invalid_sra_in_list(self):
        with self.assertRaises(ValidationError):
            validate_sra_list(["SRX3407686", "SRXPPPPP0001"])

    def test_passes_valid_id(self):
        validate_sra_identifier("SRX3407687")


class TestEnsemblValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid Ensembl as well as detecting correct Ensembl ids.
    """

    def test_ve_invalid_id(self):
        with self.assertRaises(ValidationError):
            validate_ensembl_identifier("ENVS00000010404")

    def test_ve_invalid_list(self):
        with self.assertRaises(ValidationError):
            validate_ensembl_list(["ENSG00000143384", "NO_155436.1"])

    def test_passes_valid_id(self):
        validate_ensembl_identifier("ENSG00000143384")


class TestRefSeqValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid RefSeq as well as detecting correct RefSeq ids.
    """

    def test_ve_invalid_id(self):
        with self.assertRaises(ValidationError):
            validate_refseq_identifier("NX_155436.1")

    def test_ve_invalid_list(self):
        with self.assertRaises(ValidationError):
            validate_refseq_list(["NR_155436.1", "NO_155436.1"])

    def test_passes_valid_id(self):
        validate_refseq_identifier("NR_155436.1")


class TestUniprotValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid Uniprot as well as detecting correct Uniprot ids.
    """

    def test_ve_invalid_uniprot_id(self):
        with self.assertRaises(ValidationError):
            validate_uniprot_identifier("P123")

    def test_ve_invalid_uniprot_list(self):
        with self.assertRaises(ValidationError):
            validate_keyword_list(["protein", 555])

    def test_passes_valid_uniprot_id(self):
        validate_uniprot_identifier("P01133")


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
            validate_keyword_list(["protein", 555])
