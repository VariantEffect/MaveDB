from django.test import TestCase
from django.core.exceptions import ValidationError

from core.utilities import null_values_list

from ..validators import hgvs


class TestValidateHgvsString(TestCase):
    def test_passes_on_null(self):
        for v in null_values_list:
            hgvs.validate_hgvs_string(v)

    def test_error_not_str(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string(1.0)

    def test_error_unknown_column(self):
        with self.assertRaises(ValueError):
            hgvs.validate_hgvs_string("c.1A>G", column="random")

    def test_error_does_not_match_splice(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string("g.G4L", column="splice")

    def test_error_nt_is_not_g_when_splice_present(self):
        hgvs.validate_hgvs_string("c.1A>G", column="nt", splice_present=False)
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string(
                "c.1A>G", column="nt", splice_present=True
            )

    def test_error_does_not_match_nt(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string("p.G4L", column="nt")

    def test_error_does_not_match_pro(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string("c.1A>G", column="p")

    def test_raises_on_enrich_special_types(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string("_wt")
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string("_sy")

    def test_validates_valid_hgvs(self):
        hgvs.validate_hgvs_string("c.1A>G", column="nt", splice_present=False)
        hgvs.validate_hgvs_string("g.1A>G", column="nt", splice_present=True)
        hgvs.validate_hgvs_string("c.1A>G", column="splice")
        hgvs.validate_hgvs_string("p.(=)", column="p")
