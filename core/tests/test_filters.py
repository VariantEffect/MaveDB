from django.test import TestCase

from metadata import factories as meta_factories

from .. import filters


class TestCSVCharFilter(TestCase):
    def setUp(self):
        self.kw1 = meta_factories.KeywordFactory()
        self.kw2 = meta_factories.KeywordFactory()
        self.kw3 = meta_factories.KeywordFactory()
        self.queryset = meta_factories.KeywordFactory._meta.model.objects.all()
        self.filter = filters.CSVCharFilter(
            field_name="text", lookup_expr="iexact"
        )

    def test_filter_single_value(self):
        qs = self.filter.filter(self.queryset, self.kw1.text)
        self.assertEqual(qs.count(), 1)
        self.assertIn(self.kw1, qs)

    def test_filter_comma_sep_values(self):
        value = ",".join([self.kw1.text, self.kw2.text])
        qs = self.filter.filter(self.queryset, value)
        self.assertEqual(qs.count(), 2)
        self.assertIn(self.kw1, qs)
        self.assertIn(self.kw2, qs)

    def test_does_not_split_quoted(self):
        value = '{},"{},{}"'.format(
            self.kw1.text, self.kw2.text, self.kw3.text
        )
        qs = self.filter.filter(self.queryset, value)
        self.assertEqual(qs.count(), 1)
        self.assertIn(self.kw1, qs)

    def test_returns_all_no_value(self):
        qs = self.filter.filter(self.queryset, "")
        self.assertEqual(qs.count(), 3)
