from django.test import TestCase

from ..templatetags import list_tags


class TestIsInTag(TestCase):
   def test_returns_true_in_container(self):
       self.assertTrue(list_tags.is_in('a', 'abc'))
       
   def test_returns_false_not_in_container(self):
       self.assertFalse(list_tags.is_in('a', 'bbc'))
       
   def test_formats_for_javascript(self):
       self.assertEqual('true', list_tags.is_in('a', 'abc', javascript=True))
       self.assertEqual('false', list_tags.is_in('a', 'bbc', javascript=True))