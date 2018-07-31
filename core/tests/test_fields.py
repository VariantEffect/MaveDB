import json

from django.test import TestCase

from .. import fields


class TestParseCharList(TestCase):
    def test_parse_char_list_returns_list_loaded_by_json(self):
        result = fields.parse_char_list("['hello', 'world']")
        expected = json.loads("[\"hello\", \"world\"]")
        self.assertEqual(result, expected)
        
    def test_parse_char_passthrough_on_list_set_tuple(self):
        expected = ['hello', 'world']
        result = fields.parse_char_list(expected)
        self.assertEqual(result, expected)
        
        expected = ('hello', 'world')
        result = fields.parse_char_list(expected)
        self.assertEqual(result, list(expected))
        
        expected = {'hello', 'world'}
        result = fields.parse_char_list(expected)
        self.assertEqual(result, list(expected))
        
    def test_returns_list_non_json_string(self):
        expected = ['hello']
        result = fields.parse_char_list('hello')
        self.assertEqual(result, expected)
        
        expected = [1]
        result = fields.parse_char_list('1')
        self.assertEqual(result, expected)


class TestCSVCharField(TestCase):
    def test_clean_returns_list(self):
        field = fields.CSVCharField(max_length=None, required=False)
        result = field.clean("['hello', 'world']")
        self.assertListEqual(result, ['hello', 'world'])
        
    def test_cleaning_none_returns_falsey(self):
        field = fields.CSVCharField(max_length=None, required=False)
        result = field.clean(None)
        self.assertFalse(result)