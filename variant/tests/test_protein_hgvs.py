from django.test import TestCase
from django.core.exceptions import ValidationError

from ..hgvs.protein import (
    validate_substitution,
    validate_deletion,
    validate_delins,
    validate_insertion,
    validate_frame_shift,
    single_variant_re,
    multi_variant_re,
)


class TestVariantRegexPatterns(TestCase):
    def test_single_var_re_matches_each_event(self):
        self.assertIsNotNone(None)
    
    def test_multi_var_re_matches_each_event(self):
        self.assertIsNotNone(None)


class TestEventValidators(TestCase):
    def test_valid_substitutions_pass(self):
        validate_substitution('Trp24Cys')
        validate_substitution('Cys188=')
        validate_substitution('Trp24*')
        validate_substitution('Trp24Ter')
        validate_substitution('Trp24?')
        validate_substitution('Trp24=/Cys')
        validate_substitution('0')
        validate_substitution('?')
        
    
    def test_error_invalid_substitutions(self):
        with self.assertRaises(ValidationError):
            validate_substitution("")
        with self.assertRaises(ValidationError):
            validate_substitution("a>g")
        with self.assertRaises(ValidationError):
            validate_substitution('*a>g')
        with self.assertRaises(ValidationError):
            validate_substitution('1a>a')
        with self.assertRaises(ValidationError):
            validate_substitution('12a=g')
        with self.assertRaises(ValidationError):
            validate_substitution('12a>E')
        with self.assertRaises(ValidationError):
            validate_substitution('12a<E')
        with self.assertRaises(ValidationError):
            validate_substitution('12-1>a')
        with self.assertRaises(ValidationError):
            validate_substitution('+12a>g')
    
    def test_valid_deletions_pass(self):
        validate_deletion('Val7del')
        validate_deletion('Lys23_Val25del')
        validate_deletion('Trp4del')
        validate_deletion('Gly2_Met46del')
        validate_deletion('Val7=/del')
    
    def test_error_invalid_deletions(self):
        with self.assertRaises(ValidationError):
            validate_deletion('19delR')
        with self.assertRaises(ValidationError):
            validate_deletion('')
        with self.assertRaises(ValidationError):
            validate_deletion('dela')
        with self.assertRaises(ValidationError):
            validate_deletion('4071+1_4072-1_5154+1_5155-1del')
        with self.assertRaises(ValidationError):
            validate_deletion('(?_-1)_(+1_?)del')
        with self.assertRaises(ValidationError):
            validate_deletion('1704+1delaaa')
        with self.assertRaises(ValidationError):
            validate_deletion('19_21del(5)')
        with self.assertRaises(ValidationError):
            validate_deletion('19_21deluuu')
    
    def test_valid_insertions_pass(self):
        validate_insertion('426_427insa')
        validate_insertion('756_757insuacu')
        validate_insertion('(222_226)insg')
        validate_insertion('549_550insn')
        validate_insertion('761_762insnnnnn')
        validate_insertion('761_762ins(5)')
        validate_insertion('2949_2950ins[2950-30_2950-12;2950-4_2950-1]')
    
    def test_error_invalid_insertions(self):
        with self.assertRaises(ValidationError):
            validate_insertion('19insR')
        with self.assertRaises(ValidationError):
            validate_insertion('')
        with self.assertRaises(ValidationError):
            validate_insertion('insa')
        with self.assertRaises(ValidationError):
            validate_insertion('(4071+1_4072)-(1_5154+1_5155-1)ins')
        with self.assertRaises(ValidationError):
            validate_insertion('(?_-1)_(+1_?)ins')
        with self.assertRaises(ValidationError):
            validate_insertion('1704+1insaaa')
    
    def test_valid_delins_passes(self):
        validate_delins('6775delinsga')
        validate_delins('6775_6777delinsc')
        validate_delins('?_6777delinsc')
        validate_delins('?_?delinsc')
        validate_delins('142_144delinsugg')
        validate_delins('9002_9009delinsuuu')
        validate_delins('9002_9009delins(5)')

    def test_error_invalid_delins(self):
        with self.assertRaises(ValidationError):
            validate_delins('19delinsR')
        with self.assertRaises(ValidationError):
            validate_delins('')
        with self.assertRaises(ValidationError):
            validate_delins('delinsa')
        with self.assertRaises(ValidationError):
            validate_delins('(4071+1_4072)-(1_5154+1_5155-1)delins')
        with self.assertRaises(ValidationError):
            validate_delins('(?_-1)_(+1_?)delins')
        with self.assertRaises(ValidationError):
            validate_delins('*?_45+1delinsc')
    
    # TODO: Write these.
    def test_valid_frameshift_passes(self):
        validate_frame_shift('6775delinsga')
        validate_frame_shift('6775_6777delinsc')
        validate_frame_shift('?_6777delinsc')
        validate_frame_shift('?_?delinsc')
        validate_frame_shift('142_144delinsugg')
        validate_frame_shift('9002_9009delinsuuu')
        validate_frame_shift('9002_9009delins(5)')

    def test_error_invalid_frameshift(self):
        with self.assertRaises(ValidationError):
            validate_frame_shift('19delinsR')
        with self.assertRaises(ValidationError):
            validate_frame_shift('')
        with self.assertRaises(ValidationError):
            validate_frame_shift('delinsa')
        with self.assertRaises(ValidationError):
            validate_frame_shift('(4071+1_4072)-(1_5154+1_5155-1)delins')
        with self.assertRaises(ValidationError):
            validate_frame_shift('(?_-1)_(+1_?)delins')
        with self.assertRaises(ValidationError):
            validate_frame_shift('*?_45+1delinsc')

