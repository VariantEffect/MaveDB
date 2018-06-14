from django.test import TestCase
from django.core.exceptions import ValidationError

from ..hgvs.dna import (
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
            single_variant_re.fullmatch('c.123A>G'))
        self.assertIsNotNone(
            single_variant_re.fullmatch('g.(4071+1_4072-1)_(5154+1_5155-1)del'))
        self.assertIsNotNone(
            single_variant_re.fullmatch('n.240_241insAGG'))
        self.assertIsNotNone(
            single_variant_re.fullmatch('m.9002_9009delins(5)'))
        
    def test_multi_var_re_matches_each_event(self):
        self.assertIsNotNone(
            multi_variant_re.fullmatch(
                'c.[123A>G;19del;'
                '240_241insAGG;9002_9009delins(5)]'
            ))
        self.assertIsNotNone(
            multi_variant_re.fullmatch(
                'g.[123=/A>G;19delT;'
                '240_241insAGG;9002_9009delins(5)]'
            ))
        self.assertIsNotNone(
            multi_variant_re.fullmatch(
                'm.[123=;(?_-1)_(*1_?)del;'
                '(?_-245)_(31+1_32-1)del;9002_9009delinsGGG]'
            ))
        self.assertIsNotNone(
            multi_variant_re.fullmatch(
                'n.[54=//T>C;*183+45_186del;'
                '32717298_32717299ins(100);6775delinsGA]'
            ))
        
        # Non-multi should be none
        self.assertIsNone(multi_variant_re.fullmatch('c.[123=;]'))
        self.assertIsNone(multi_variant_re.fullmatch('c.[123A>G]'))
        

class TestEventValidators(TestCase):
    def test_valid_substitutions_pass(self):
        validate_substitution('123A>G')
        validate_substitution('123A>X')
        validate_substitution('123A>N')
        validate_substitution('*123A>G')
        validate_substitution('-123A>G')
        validate_substitution('-123+45A>G')
        validate_substitution('*123-45A>G')
        validate_substitution('93+1G>T')
        validate_substitution('54G>H')
        validate_substitution('54=')
        validate_substitution('54=/T>C')
        validate_substitution('54=//T>C')
        
    def test_error_invalid_substitutions(self):
        with self.assertRaises(ValidationError):
            validate_substitution("")
        with self.assertRaises(ValidationError):
            validate_substitution("A>G")
        with self.assertRaises(ValidationError):
            validate_substitution('*A>G')
        with self.assertRaises(ValidationError):
            validate_substitution('1A>A')
        with self.assertRaises(ValidationError):
            validate_substitution('12A=G')
        with self.assertRaises(ValidationError):
            validate_substitution('12A>E')
        with self.assertRaises(ValidationError):
            validate_substitution('12A<E')
        with self.assertRaises(ValidationError):
            validate_substitution('12>A')
        with self.assertRaises(ValidationError):
            validate_substitution('+12A>G')
        
    def test_valid_deletions_pass(self):
        validate_deletion('19del')
        validate_deletion('19delT')
        validate_deletion('19_21del')
        validate_deletion('*183_186+48del')
        validate_deletion('*183+45_186del')
        validate_deletion('1704+1del')
        validate_deletion('4072-1234_5155-246del')
        validate_deletion('(4071+1_4072-1)_(5154+1_5155-1)del')
        validate_deletion('720_991del')
        validate_deletion('(?_-245)_(31+1_32-1)del')
        validate_deletion('(?_-1)_(*1_?)del')
        validate_deletion('19_21=/del')
        validate_deletion('19_21del=//del')
        
    def test_error_invalid_deletions(self):
        with self.assertRaises(ValidationError):
            validate_deletion('19delR')
        with self.assertRaises(ValidationError):
            validate_deletion('')
        with self.assertRaises(ValidationError):
            validate_deletion('delA')
        with self.assertRaises(ValidationError):
            validate_deletion('4071+1_4072-1_5154+1_5155-1del')
        with self.assertRaises(ValidationError):
            validate_deletion('(?_-1)_(+1_?)del')
        with self.assertRaises(ValidationError):
            validate_deletion('1704+1delAAA')
        with self.assertRaises(ValidationError):
            validate_deletion('19_21del(5)')
        with self.assertRaises(ValidationError):
            validate_deletion('19_21delTTT')
        
    def test_valid_insertions_pass(self):
        validate_insertion('169_170insA')
        validate_insertion('240_241insAGG')
        validate_insertion('761_762insNNNNN')
        validate_insertion('32717298_32717299ins(100)')
        validate_insertion('761_762insN')
        validate_insertion('(222_226)insG')
        
    def test_error_invalid_insertions(self):
        with self.assertRaises(ValidationError):
            validate_insertion('19insR')
        with self.assertRaises(ValidationError):
            validate_insertion('')
        with self.assertRaises(ValidationError):
            validate_insertion('insA')
        with self.assertRaises(ValidationError):
            validate_insertion('(4071+1_4072)-(1_5154+1_5155-1)ins')
        with self.assertRaises(ValidationError):
            validate_insertion('(?_-1)_(+1_?)ins')
        with self.assertRaises(ValidationError):
            validate_insertion('1704+1insAAA')
            
    def test_valid_delins_passes(self):
        validate_delins('6775delinsGA')
        validate_delins('6775_6777delinsC')
        validate_delins('?_6777delinsC')
        validate_delins('?_?delinsC')
        validate_delins('142_144delinsTGG')
        validate_delins('9002_9009delinsTTT')
        validate_delins('9002_9009delins(5)')
        
    def test_error_invalid_delins(self):
        with self.assertRaises(ValidationError):
            validate_delins('19delinsR')
        with self.assertRaises(ValidationError):
            validate_delins('')
        with self.assertRaises(ValidationError):
            validate_delins('delinsA')
        with self.assertRaises(ValidationError):
            validate_delins('(4071+1_4072)-(1_5154+1_5155-1)delins')
        with self.assertRaises(ValidationError):
            validate_delins('(?_-1)_(+1_?)delins')
        with self.assertRaises(ValidationError):
            validate_delins('*?_45+1delinsC')
