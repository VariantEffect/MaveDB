from django.test import TestCase

from metadata.factories import (
    UniprotOffsetFactory, EnsemblOffsetFactory, RefseqOffsetFactory
)
from ..factories import TargetGeneFactory, ReferenceMapWithIntervalsFactory
from ..serializers import TargetGeneSerializer, ReferenceMapSerializer


class TestTargetGeneSerializer(TestCase):

    def test_serializes_name_and_sequence(self):
        targetgene = TargetGeneFactory()
        data = TargetGeneSerializer(targetgene).data
        self.assertEqual(data['wt_sequence']['sequence'],
                         targetgene.wt_sequence.sequence)
        self.assertEqual(data['name'], targetgene.name)

    def test_uses_uniprot_offset_serializer(self):
        targetgene = TargetGeneFactory()
        uniprot = targetgene.uniprot_id
        offset = UniprotOffsetFactory(target=targetgene, identifier=uniprot)
        data = TargetGeneSerializer(targetgene).data

        self.assertEqual(data['uniprot']['offset'], offset.offset)
        self.assertEqual(data['uniprot']['identifier'], uniprot.identifier)
        self.assertEqual(data['uniprot']['url'], uniprot.url)
        self.assertEqual(data['uniprot']['dbversion'], uniprot.dbversion)
        self.assertEqual(data['uniprot']['dbname'], uniprot.dbname)

    def test_uses_refseq_offset_serializer(self):
        targetgene = TargetGeneFactory()
        id_ = targetgene.refseq_id
        offset = RefseqOffsetFactory(target=targetgene, identifier=id_)
        data = TargetGeneSerializer(targetgene).data

        self.assertEqual(data['refseq']['offset'], offset.offset)
        self.assertEqual(data['refseq']['identifier'], id_.identifier)
        self.assertEqual(data['refseq']['url'], id_.url)
        self.assertEqual(data['refseq']['dbversion'], id_.dbversion)
        self.assertEqual(data['refseq']['dbname'], id_.dbname)

    def test_uses_ensembl_offset_serializer(self):
        targetgene = TargetGeneFactory()
        id_ = targetgene.ensembl_id
        offset = EnsemblOffsetFactory(target=targetgene, identifier=id_)
        data = TargetGeneSerializer(targetgene).data

        self.assertEqual(data['ensembl']['offset'], offset.offset)
        self.assertEqual(data['ensembl']['identifier'], id_.identifier)
        self.assertEqual(data['ensembl']['url'], id_.url)
        self.assertEqual(data['ensembl']['dbversion'], id_.dbversion)
        self.assertEqual(data['ensembl']['dbname'], id_.dbname)


class TestReferenceMapSerializer(TestCase):

    def test_reference_maps_hide_intervals(self):
        rm = ReferenceMapWithIntervalsFactory()
        data = ReferenceMapSerializer(rm).data
        self.assertNotIn('intervals', data)
        self.assertNotIn('is_primary', data)