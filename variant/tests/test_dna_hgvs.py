from django.test import TestCase
from django.core.exceptions import ValidationError

from ..validators.hgvs.dna import (
    validate_substitution,
    validate_deletion,
    validate_delins,
    validate_insertion,
)


class TestEventValidators(TestCase):
    def test_valid_substitutions_pass(self):
        validate_substitution('123A>G')
        for c in 'cngm':
            validate_substitution('{}.123A>G'.format(c))
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
        
    def test_validation_error_ref_same_as_new(self):
        with self.assertRaises(ValidationError):
            validate_substitution('1A>A')
        
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
        for c in 'cngm':
            validate_deletion('{}.123delA'.format(c))
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
        for c in 'cngm':
            validate_insertion('{}.123_124insA'.format(c))
        
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
        validate_delins('*?_45+1delinsC')
        validate_delins('?_?delinsC')
        validate_delins('142_144delinsTGG')
        validate_delins('9002_9009delinsTTT')
        validate_delins('9002_9009delins(5)')
        for c in 'cngm':
            validate_delins('{}.123_127delinsA'.format(c))
        
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
