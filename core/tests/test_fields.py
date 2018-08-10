import json

from django.test import TestCase

from .. import fields


class TestParseJSONList(TestCase):
    def test_parse_char_list_returns_list_loaded_by_json(self):
        result = fields.parse_json_list("['hello', 'world']")
        expected = json.loads("[\"hello\", \"world\"]")
        self.assertEqual(result, expected)
        
    def test_parse_char_passthrough_on_list_set_tuple(self):
        expected = ['hello', 'world']
        result = fields.parse_json_list(expected)
        self.assertEqual(result, expected)
        
        expected = ('hello', 'world')
        result = fields.parse_json_list(expected)
        self.assertEqual(result, list(expected))
        
        expected = {'hello', 'world'}
        result = fields.parse_json_list(expected)
        self.assertEqual(result, list(expected))
        
    def test_returns_list_non_json_string(self):
        expected = ['hello']
        result = fields.parse_json_list('hello')
        self.assertEqual(result, expected)
        
        expected = [1]
        result = fields.parse_json_list('1')
        self.assertEqual(result, expected)


class TestCSVCharField(TestCase):
    def test_clean_str_repr_of_list_returns_list(self):
        field = fields.CSVCharField()
        result = field.clean("['hello', 'world']")
        self.assertListEqual(result, ['hello', 'world'])

    def test_clean_csv_returns_string_if_input_is_not_a_list_repr(self):
        field = fields.CSVCharField()
        
        result = field.clean("hello,world")
        self.assertListEqual(result, ['hello,world'])
        
        result = field.clean("hello,\"hello,world\"")
        self.assertListEqual(result, ['hello,\"hello,world\"'])

    def test_cleaning_none_returns_falsey_value(self):
        field = fields.CSVCharField(required=False)
        result = field.clean(None)
        self.assertFalse(result)
