from hgvsp import Level

from django.test import TestCase
from django.core.exceptions import ValidationError

from ..validators.hgvs import validate_multi_variant, validate_single_variant
from .. import constants


class TestValidateMulti(TestCase):
    def test_error_level_not_enum(self):
        with self.assertRaises(TypeError):
            validate_multi_variant('c.[1A>G;2A>G]', level='dna')
            
    def test_can_set_level_through_argument(self):
        # Validation error when attempting to validate dna as a protein hgvs
        with self.assertRaises(ValidationError):
            validate_multi_variant('c.[1A>G;2A>G]', level=Level.PROTEIN)
            
    def test_validationerror_invalid_prefix(self):
        with self.assertRaises(ValidationError):
            validate_multi_variant('f.1A>G')
            
    def test_can_validate_protein_multi(self):
        validate_multi_variant('p.[His4_Gln5insAla;Cys28fs;Cys28delinsVal]')
        validate_multi_variant('p.[(His4_Gln5insAla);(Cys28fs);Cys28delinsVal]')
        
    def test_can_validate_dna_multi(self):
        validate_multi_variant('c.[123A>G;19del]')
        validate_multi_variant('g.[123A>G;19del]')
        validate_multi_variant('m.[123A>G;19del]')
        validate_multi_variant('n.[123A>G;19del]')
        
    def test_can_validate_rna_multi(self):
        validate_multi_variant('r.[123a>g;19del]')
        validate_multi_variant('r.[123a>g,19del]')
        
    def test_validationerror_invalid_multi(self):
        with self.assertRaises(ValidationError):
            validate_multi_variant('c.[1A>G]')
        with self.assertRaises(ValidationError):
            validate_multi_variant('r.1a>u')
            
    def test_validationerror_mixed_multi(self):
        with self.assertRaises(ValidationError):
            validate_multi_variant('c.[1A>G;Lys4Gly]')
            
    def test_passes_redefined_event(self):
        validate_multi_variant('c.[1A>G;1A>G]')
            
    def test_passes_wt_and_sy(self):
        validate_multi_variant(constants.wildtype)
        validate_multi_variant(constants.synonymous)


class TestValidateSingle(TestCase):
    def test_error_level_not_enum(self):
        with self.assertRaises(TypeError):
            validate_single_variant('c.1A>G', level='dna')
            
    def test_can_set_level_through_argument(self):
        # Validation error when attempting to validate dna as a protein hgvs
        with self.assertRaises(ValidationError):
            validate_single_variant('c.2A>G', level=Level.PROTEIN)
            
    def test_validationerror_invalid_prefix(self):
        with self.assertRaises(ValidationError):
            validate_single_variant('f.1A>G')
    
    def test_can_validate_protein(self):
        validate_single_variant('p.His4_Gln5insAla')
        validate_single_variant('p.(His4_Gln5insAla)')
    
    def test_can_validate_dna(self):
        validate_single_variant('c.123A>G')
        validate_single_variant('g.19del')
        validate_single_variant('m.19_21ins(5)')
        validate_single_variant('m.19_21insXXX')
        validate_single_variant('n.123_127delinsAAA')
    
    def test_can_validate_rna_multi(self):
        validate_single_variant('r.123a>g')
        validate_single_variant('r.19del')
    
    def test_validationerror_invalid_multi(self):
        with self.assertRaises(ValidationError):
            validate_single_variant('c.[1A>G]')
    
    def test_validationerror_invalid(self):
        with self.assertRaises(ValidationError):
            validate_single_variant('c.')
            
    def test_passes_wt_and_sy(self):
        validate_single_variant(constants.wildtype)
        validate_single_variant(constants.synonymous)
