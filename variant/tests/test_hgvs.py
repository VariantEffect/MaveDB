from django.test import TestCase
from django.core.exceptions import ValidationError

from ..hgvs import (
    infer_type, Event, Level, is_multi, validate_multi_variant,
    validate_single_variants
)


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
        self.assertEqual(Event.DELINS, infer_type('c.(?_-1)_(*1_?)del'))
        self.assertEqual(Event.DELINS, infer_type('r.6_8del'))
        self.assertEqual(Event.DELINS, infer_type('p.Val7=/del'))


class TestIsMulti(TestCase):
    pass


class TestValidateMulti(TestCase):
    pass


class TestValidateSingle(TestCase):
    pass