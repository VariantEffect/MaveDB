from django.test import TestCase
from django.core.exceptions import ValidationError

from core.utilities import null_values_list

from ..validators import hgvs
from .. import constants


class TestValidateMulti(TestCase):
    def test_validationerror_invalid_prefix(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_multi_variant("f.1A>G")

    def test_can_validate_protein_multi(self):
        hgvs.validate_multi_variant(
            "p.[His4_Gln5insAla;Cys28fs;Cys28delinsVal]"
        )
        hgvs.validate_multi_variant(
            "p.[(His4_Gln5insAla);(Cys28fs);Cys28delinsVal]"
        )

    def test_can_validate_dna_multi(self):
        hgvs.validate_multi_variant("c.[123A>G;19del]")
        hgvs.validate_multi_variant("g.[123A>G;19del]")
        hgvs.validate_multi_variant("m.[123A>G;19del]")
        hgvs.validate_multi_variant("n.[123A>G;19del]")

    def test_validationerror_invalid_multi(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_multi_variant("c.[1A>G]")
        with self.assertRaises(ValidationError):
            hgvs.validate_multi_variant("r.[1a>u,2a>u]")

    def test_validationerror_mixed_multi(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_multi_variant("c.[1A>G;Lys4Gly]")

    def test_passes_redefined_event(self):
        hgvs.validate_multi_variant("c.[1A>G;1A>G]")

    def test_passes_wt_and_sy(self):
        hgvs.validate_multi_variant(constants.wildtype)
        hgvs.validate_multi_variant(constants.synonymous)


class TestValidateSingle(TestCase):
    def test_validationerror_invalid_prefix(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_single_variant("f.1A>G")

    def test_can_validate_protein(self):
        hgvs.validate_single_variant("p.His4_Gln5insAla")
        hgvs.validate_single_variant("p.(His4_Gln5insAla)")

    def test_can_validate_dna(self):
        hgvs.validate_single_variant("c.123A>G")
        hgvs.validate_single_variant("g.19del")
        hgvs.validate_single_variant("m.19_21ins(5)")
        hgvs.validate_single_variant("m.19_21insXXX")
        hgvs.validate_single_variant("n.123_127delinsAAA")

    def test_does_not_validate_rna(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_single_variant("r.123a>g")
        with self.assertRaises(ValidationError):
            hgvs.validate_multi_variant("r.[19del,20del]")

    def test_validationerror_invalid_multi(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_single_variant("c.[1A>G]")

    def test_validationerror_invalid(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_single_variant("c.")

    def test_passes_wt_and_sy(self):
        hgvs.validate_single_variant(constants.wildtype)
        hgvs.validate_single_variant(constants.synonymous)


class TestValidateHgvsString(TestCase):
    def test_passes_on_null(self):
        for v in null_values_list:
            hgvs.validate_hgvs_string(v)

    def test_error_not_str(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string(1.0)

    def test_error_unknown_level(self):
        with self.assertRaises(ValueError):
            hgvs.validate_hgvs_string("c.1A>G", column="random")

    def test_error_level_does_not_match_tx(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string("g.G4L", column="tx")

    def test_error_nt_is_not_g_when_tx_present(self):
        hgvs.validate_hgvs_string("c.1A>G", column="nt", tx_present=False)
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string("c.1A>G", column="nt", tx_present=True)

    def test_error_level_does_not_match_nt(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string("p.G4L", column="nt")

    def test_error_level_does_not_match_pro(self):
        with self.assertRaises(ValidationError):
            hgvs.validate_hgvs_string("c.1A>G", column="p")

    def test_passes_on_special_types(self):
        hgvs.validate_hgvs_string(constants.wildtype)
        hgvs.validate_hgvs_string(constants.synonymous)

    def test_validates_valid_hgvs(self):
        hgvs.validate_hgvs_string("c.1A>G", column="nt", tx_present=False)
        hgvs.validate_hgvs_string("g.1A>G", column="nt", tx_present=True)
        hgvs.validate_hgvs_string("c.1A>G", column="tx")
        hgvs.validate_hgvs_string("p.G4L", column="p")
