from django.test import TestCase
from django.core.exceptions import ValidationError

from dataset import constants

from ..hgvs import (
    infer_type, Event, Level, is_multi, validate_multi_variant,
    validate_single_variants, infer_level
)


class TestInferLevel(TestCase):
    def test_infers_protein(self):
        self.assertEqual(Level.PROTEIN, infer_level('p'))
        
    def test_infers_dna(self):
        self.assertEqual(Level.DNA, infer_level('c'))
        self.assertEqual(Level.DNA, infer_level('n'))
        self.assertEqual(Level.DNA, infer_level('g'))
        self.assertEqual(Level.DNA, infer_level('m'))
        
    def test_infers_rna(self):
        self.assertEqual(Level.RNA, infer_level('r'))

    def test_infers_none(self):
        self.assertEqual(None, infer_level('t'))
        
    def test_none_null_value(self):
        for v in constants.nan_col_values:
            self.assertIsNone(infer_level(v))
    

class TestInferType(TestCase):
    def test_infers_substitution(self):
        self.assertEqual(Event.SUBSTITUTION, infer_type('c.1A>G'))
        self.assertEqual(Event.SUBSTITUTION, infer_type('r.1a>u'))
        self.assertEqual(Event.SUBSTITUTION, infer_type('p.Gly4Leu'))
        
    def test_infers_insertion(self):
        self.assertEqual(Event.INSERTION, infer_type('c.240_241insAGG'))
        self.assertEqual(Event.INSERTION, infer_type('r.2949_2950insaaa'))
        self.assertEqual(Event.INSERTION, infer_type('p.Arg78_Gly79ins23'))
        
    def test_infers_deletion(self):
        self.assertEqual(Event.DELETION, infer_type('c.(?_-1)_(*1_?)del'))
        self.assertEqual(Event.DELETION, infer_type('r.6_8del'))
        self.assertEqual(Event.DELETION, infer_type('p.Val7=/del'))
        
    def test_infers_delins(self):
        self.assertEqual(Event.DELINS, infer_type('c.6775delinsGA'))
        self.assertEqual(Event.DELINS, infer_type('r.?_?delinsc'))
        self.assertEqual(Event.DELINS, infer_type('p.C28_L29delinsTG'))

    def test_infers_frame_shift(self):
        self.assertEqual(Event.FRAME_SHIFT, infer_type('Glu5ValfsTer5'))
        self.assertEqual(Event.FRAME_SHIFT, infer_type('p.Ile327Argfs*?'))
        
    def test_none_null_value(self):
        for v in constants.nan_col_values:
            self.assertIsNone(infer_type(v))


class TestIsMulti(TestCase):
    def test_detects_multi_variant(self):
        self.assertTrue(is_multi('c.[123A>G;19del]'))
        self.assertTrue(is_multi('n.[123A>G;19del]'))
        self.assertTrue(is_multi('g.[123A>G;19del]'))
        self.assertTrue(is_multi('m.[123A>G;19del]'))
        
        self.assertTrue(is_multi('r.[123a>g;19del]'))
        self.assertTrue(is_multi('r.[123a>g,19del]'))
        
        self.assertTrue(is_multi('p.[His4_Gln5insAla;Cys28fs;Cys28delinsVal]'))
        
    def test_single_variant_returns_false(self):
        self.assertFalse(is_multi('c.123A>G'))
        self.assertFalse(is_multi('r.19del'))
        self.assertFalse(is_multi(
            'r.2949_2950ins[2950-30_2950-12;2950-4_2950-1]'))
        self.assertFalse(is_multi('p.His4_Gln5insAla'))
        self.assertFalse(is_multi('p.(His4_Gln5insAla)'))
        
    def test_incomplete_multi_returns_false(self):
        self.assertFalse(is_multi('r.[123a>g;19del;]'))
        self.assertFalse(is_multi('r.[123a>g,19del,]'))
        self.assertFalse(is_multi('c.[123a>g]'))
        self.assertFalse(is_multi('c.[]'))
        self.assertFalse(is_multi('g.[]'))
        self.assertFalse(is_multi('n.[]'))
        self.assertFalse(is_multi('m.[]'))
        self.assertFalse(is_multi('r.[]'))
        self.assertFalse(is_multi('p.[]'))
        
    def test_mixed_multi_variant_returns_false(self):
        self.assertFalse(is_multi('c.[1A>G;Lys4Gly]'))


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
            
    def test_validationerror_redefined_event(self):
        with self.assertRaises(ValidationError):
            validate_multi_variant('c.[1A>G;1A>G]')
            
    def test_passes_wt_and_sy(self):
        validate_multi_variant('_wt')
        validate_multi_variant('_sy')


class TestValidateSingle(TestCase):
    def test_error_level_not_enum(self):
        with self.assertRaises(TypeError):
            validate_single_variants('c.1A>G', level='dna')
            
    def test_can_set_level_through_argument(self):
        # Validation error when attempting to validate dna as a protein hgvs
        with self.assertRaises(ValidationError):
            validate_single_variants('c.2A>G', level=Level.PROTEIN)
            
    def test_validationerror_invalid_prefix(self):
        with self.assertRaises(ValidationError):
            validate_single_variants('f.1A>G')
    
    def test_can_validate_protein(self):
        validate_single_variants('p.His4_Gln5insAla')
        validate_single_variants('p.(His4_Gln5insAla)')
    
    def test_can_validate_dna(self):
        validate_single_variants('c.123A>G')
        validate_single_variants('g.19del')
        validate_single_variants('m.19_21ins(5)')
        validate_single_variants('m.19_21insXXX')
        validate_single_variants('n.123_127delinsAAA')
    
    def test_can_validate_rna_multi(self):
        validate_single_variants('r.123a>g')
        validate_single_variants('r.19del')
    
    def test_validationerror_invalid_multi(self):
        with self.assertRaises(ValidationError):
            validate_single_variants('c.[1A>G]')
    
    def test_validationerror_invalid(self):
        with self.assertRaises(ValidationError):
            validate_single_variants('c.')
            
    def test_passes_wt_and_sy(self):
        validate_single_variants('_wt')
        validate_single_variants('_sy')