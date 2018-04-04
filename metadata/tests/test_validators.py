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


class TestExternalIdentifierValidators(TestCase):
    """
    Tests that each validator throws the appropriate :class:`ValidationError`
    when passed invalid input.
    """
    def test_ve_invalid_doi(self):
        with self.assertRaises(ValidationError):
            validate_doi_identifier('doi: 10.1016')

    def test_ve_invalid_doi_in_list(self):
        with self.assertRaises(ValidationError):
            validate_doi_list(
                ['doi: 10.1016', '10.1016/j.cels.2018.01.015'])

    def test_ve_invalid_sra(self):
        with self.assertRaises(ValidationError):
            validate_sra_identifier('SRXP0001')

    def test_ve_invalid_sra_in_list(self):
        with self.assertRaises(ValidationError):
            validate_sra_list(['SRX3407686', 'SRXP0001'])

    def test_ve_invalid_pmid(self):
        with self.assertRaises(ValidationError):
            validate_pubmed_identifier('0.1')

    def test_ve_invalid_pmid_in_list(self):
        with self.assertRaises(ValidationError):
            validate_pubmed_list(['1234', '0.1'])

    def test_ve_invalid_keyword(self):
        with self.assertRaises(ValidationError):
            validate_keyword(555)

    def test_ve_invalid_keyword_in_list(self):
        with self.assertRaises(ValidationError):
            validate_keyword_list(['protein', 555])
