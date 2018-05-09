from django.test import TestCase


from ..factories import UniprotOffsetFactory
from ..serializers import UniprotOffsetSerializer


class TestAnnotationOffsetSerializer(TestCase):

    def test_representation_combines_both_offset_and_identifier_representations(self):
        offset = UniprotOffsetFactory(offset=10)
        data = UniprotOffsetSerializer(offset).data
        self.assertEqual(data['offset'], 10)
        self.assertEqual(data['identifier'], offset.identifier.identifier)
        self.assertEqual(data['url'], offset.identifier.url)
        self.assertEqual(data['dbversion'], offset.identifier.dbversion)
        self.assertEqual(data['dbname'], offset.identifier.dbname)
