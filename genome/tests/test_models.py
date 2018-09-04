from django.test import TestCase
from django.db.models.deletion import ProtectedError

from metadata.models import UniprotOffset, RefseqOffset, EnsemblOffset
from metadata.factories import RefseqOffsetFactory, UniprotOffsetFactory, EnsemblOffsetFactory

from ..models import (
    WildTypeSequence, ReferenceGenome, GenomicInterval,
    ReferenceMap, TargetGene,
)

from ..factories import (
    TargetGeneFactory,
    ReferenceMapFactory,
    ReferenceGenomeFactory,
    GenomicIntervalFactory,
    WildTypeSequenceFactory,
    TargetGeneWithReferenceMapFactory,
    ReferenceMapWithIntervalsFactory
)


class TestWildTypeSequenceModel(TestCase):
    """
    Tests instance and class methods for :class:`WildTypeSequence`
    """
    def test_sequence_returned_as_uppercase(self):
        wt = WildTypeSequenceFactory(sequence='atcg')
        self.assertEqual(wt.get_sequence(), 'ATCG')

    def test_sequence_saved_in_uppercase(self):
        wt = WildTypeSequenceFactory(sequence='atcg')
        self.assertEqual(wt.sequence, 'ATCG')

    def test_cannot_delete_when_associated_with_a_target(self):
        gene = TargetGeneFactory()
        with self.assertRaises(ProtectedError):
            gene.wt_sequence.delete()


class TestIntervalModel(TestCase):
    """
    Tests instance and class methods for :class:`GenomicInterval`
    """
    def test_get_start_adds_offset(self):
        interval = GenomicIntervalFactory()
        self.assertEqual(interval.start + 1, interval.get_start(offset=1))

    def test_get_end_adds_offset(self):
        interval = GenomicIntervalFactory()
        self.assertEqual(interval.end + -1, interval.get_end(offset=-1))

    def test_strand_returned_as_uppercase(self):
        interval = GenomicIntervalFactory(strand='f')
        self.assertEqual(interval.get_strand(), 'F')


class TestReferenceGenomeModel(TestCase):
    """
    Tests instance and class methods for :class:`ReferenceGenome`
    """

    def test_get_id_methods_return_none_if_no_association(self):
        ref = ReferenceGenomeFactory(genome_id=None)
        self.assertIsNone(ref.get_identifier())
        self.assertIsNone(ref.get_identifier_url())
        self.assertIsNone(ref.get_identifier_instance())

    def test_format_organism_name_captializes(self):
        ref = ReferenceGenomeFactory()
        self.assertIn(
            ref.get_organism_name().capitalize(),
            ref.format_organism_name_html()
        )

    def test_format_organism_name_html_capitalises(self):
        ref = ReferenceGenomeFactory()
        expected = "<i>{}</i>".format(ref.get_organism_name().capitalize())
        self.assertEqual(ref.format_organism_name_html(), expected)

    def test_delete_identifier_sets_field_as_none(self):
        genome = ReferenceGenomeFactory()
        self.assertIsNotNone(genome.genome_id)

        genome.genome_id.delete()
        genome = ReferenceGenome.objects.first()
        self.assertIsNone(genome.genome_id)

    def test_cannot_delete_genome_associated_with_a_map(self):
        map = ReferenceMapFactory()
        with self.assertRaises(ProtectedError):
            map.genome.delete()


class TestReferenceMapModel(TestCase):
    """
    Tests instance and class methods for :class:`ReferenceMap`
    """
    def test_set_is_primary_does_not_save_reference_map(self):
        ann = ReferenceMapFactory()
        ann.set_is_primary(False)
        ann.refresh_from_db()
        self.assertEqual(ann.is_primary_reference_map(), True)

    def test_can_get_intervals_when_there_are_no_associations(self):
        ann = ReferenceMapFactory()
        self.assertIsNotNone(ann.get_intervals())

    def test_delete_does_not_delete_genome(self):
        map = ReferenceMapFactory()
        self.assertEqual(ReferenceGenome.objects.count(), 1)
        map.delete()
        self.assertEqual(ReferenceGenome.objects.count(), 1)

    def test_delete_cascades_over_intervals(self):
        map = ReferenceMapWithIntervalsFactory()
        self.assertEqual(GenomicInterval.objects.count(), 3)
        map.delete()
        self.assertEqual(GenomicInterval.objects.count(), 0)


class TestTargetGene(TestCase):
    """
    Tests instance and class methods for :class:`TargetGene`
    """
    def test_does_not_have_wt_sequence_if_is_none(self):
        target = TargetGeneFactory()
        target.wt_sequence = None
        self.assertIsNone(target.get_wt_sequence())

    def test_set_wt_sequence_with_instance_does_not_delete_exisiting(self):
        target = TargetGeneFactory()
        wt = WildTypeSequenceFactory()

        target.set_wt_sequence(wt)
        self.assertEqual(WildTypeSequence.objects.count(), 2)

        target.save()
        self.assertEqual(WildTypeSequence.objects.count(), 2)
        self.assertEqual(target.get_wt_sequence(), wt)

    def test_can_get_ref_genomes(self):
        target = TargetGeneFactory()
        self.assertEqual(target.get_reference_genomes().count(), 0)

        ReferenceMapFactory(target=target)
        self.assertEqual(target.get_reference_genomes().count(), 1)

    def test_delete_deletes_maps(self):
        gene = TargetGeneWithReferenceMapFactory()
        self.assertEqual(ReferenceMap.objects.count(), 1)
        gene.delete()
        self.assertEqual(ReferenceMap.objects.count(), 0)

    def test_delete_deletes_wt_seq(self):
        gene = TargetGeneFactory()
        self.assertEqual(WildTypeSequence.objects.count(), 1)
        gene.delete()
        self.assertEqual(WildTypeSequence.objects.count(), 0)

    def test_delete_identifier_sets_field_as_none(self):
        gene = TargetGeneFactory()
        self.assertIsNotNone(gene.uniprot_id)
        self.assertIsNotNone(gene.refseq_id)
        self.assertIsNotNone(gene.ensembl_id)

        gene.uniprot_id.delete()
        gene.refseq_id.delete()
        gene.ensembl_id.delete()

        gene = TargetGene.objects.first()
        self.assertIsNone(gene.uniprot_id)
        self.assertIsNone(gene.refseq_id)
        self.assertIsNone(gene.ensembl_id)

    def test_delete_cascades_over_annotations(self):
        gene = TargetGeneFactory()
        UniprotOffsetFactory(target=gene)
        RefseqOffsetFactory(target=gene)
        EnsemblOffsetFactory(target=gene)

        self.assertEqual(UniprotOffset.objects.count(), 1)
        self.assertEqual(RefseqOffset.objects.count(), 1)
        self.assertEqual(EnsemblOffset.objects.count(), 1)

        gene.delete()
        self.assertEqual(UniprotOffset.objects.count(), 0)
        self.assertEqual(RefseqOffset.objects.count(), 0)
        self.assertEqual(EnsemblOffset.objects.count(), 0)

    def test_deleted_offset_sets_field_to_none(self):
        gene = TargetGeneFactory()
        offset = UniprotOffsetFactory(target=gene)
        self.assertIsNotNone(gene.get_uniprot_offset_annotation())
        offset.delete()
        self.assertIsNone(gene.get_uniprot_offset_annotation())

        offset = RefseqOffsetFactory(target=gene)
        self.assertIsNotNone(gene.get_refseq_offset_annotation())
        offset.delete()
        self.assertIsNone(gene.get_refseq_offset_annotation())

        offset = EnsemblOffsetFactory(target=gene)
        self.assertIsNotNone(gene.get_ensembl_offset_annotation())
        offset.delete()
        self.assertIsNone(gene.get_ensembl_offset_annotation())
