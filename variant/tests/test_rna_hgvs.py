from django.test import TestCase
from django.core.exceptions import ValidationError

from ..hgvs.rna import (
    validate_substitution,
    validate_deletion,
    validate_delins,
    validate_insertion,
    single_variant_re,
    multi_variant_re,
)


class TestVariantRegexPatterns(TestCase):
    def test_single_var_re_matches_each_event(self):
        self.assertIsNotNone(
            single_variant_re.fullmatch('r.123a>g'))
        self.assertIsNotNone(
            single_variant_re.fullmatch('r.=/6_8del'))
        self.assertIsNotNone(
            single_variant_re.fullmatch('r.2949_2950ins[2950-30_2950-12;2950-4_2950-1]'))
        self.assertIsNotNone(
            single_variant_re.fullmatch('r.9002_9009delins(5)'))
    
    def test_multi_var_re_matches_each_event(self):
        self.assertIsNotNone(
            multi_variant_re.fullmatch(
                'r.[123a>g;19del;'
                '2949_2950ins[2950-30_2950-12;2950-4_2950-1];'
                '9002_9009delins(5)]'
            ))
        self.assertIsNotNone(
            multi_variant_re.fullmatch(
                'r.[123a>g,19del,'
                '2949_2950ins[2950-30_2950-12;2950-4_2950-1],'
                '9002_9009delins(5)]'
            ))
        
        # Non-multi should be none
        self.assertIsNone(multi_variant_re.fullmatch('r.[123=;]'))
        self.assertIsNone(multi_variant_re.fullmatch('r.[123=,]'))
        self.assertIsNone(multi_variant_re.fullmatch('r.[123a>g]'))


class TestEventValidators(TestCase):
    def test_valid_substitutions_pass(self):
        validate_substitution('123a>g')
        validate_substitution('123a>x')
        validate_substitution('123a>n')
        validate_substitution('54g>h')
        validate_substitution('54=')
        validate_substitution('54=/u>c')
        validate_substitution('54=//u>c')
        validate_substitution('0')
        validate_substitution('?')
        validate_substitution('spl')
    
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
        validate_deletion('10del')
        validate_deletion('6_8del')
        validate_deletion('19_21del')
        validate_deletion('(4072_5145)del')
        validate_deletion('=/6_8del')
        validate_deletion('1704del')
    
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
