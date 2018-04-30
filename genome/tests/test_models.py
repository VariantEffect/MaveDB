from django.test import TestCase
from django.core.exceptions import ValidationError

from metadata.factories import (
    EnsemblIdentifierFactory, RefseqIdentifierFactory
)

from ..models import WildTypeSequence
from ..factories import (
    TargetGeneFactory,
    ReferenceMapFactory,
    ReferenceGenomeFactory,
    GenomicIntervalFactory,
    WildTypeSequenceFactory
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

    def test_format_species_name_captializes(self):
        ref = ReferenceGenomeFactory()
        self.assertIn(
            ref.get_species_name().capitalize(),
            ref.format_species_name_html()
        )

    def test_format_species_name_html_capitalises(self):
        ref = ReferenceGenomeFactory()
        expected = "<i>{}</i>".format(ref.get_species_name().capitalize())
        self.assertEqual(ref.format_species_name_html(), expected)


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
