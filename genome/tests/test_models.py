from django.test import TestCase

from metadata.factories import (
    EnsemblIdentifierFactory, RefseqIdentifierFactory
)

from ..factories import (
    TargetGeneFactory,
    AnnotationFactory,
    ReferenceGenomeFactory,
    IntervalFactory,
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
    Tests instance and class methods for :class:`Interval`
    """
    def test_get_start_adds_offset(self):
        interval = IntervalFactory()
        self.assertEqual(interval.start + 1, interval.get_start(offset=1))

    def test_get_end_adds_offset(self):
        interval = IntervalFactory()
        self.assertEqual(interval.end + -1, interval.get_end(offset=-1))

    def test_strand_returned_as_uppercase(self):
        interval = IntervalFactory(strand='f')
        self.assertEqual(interval.get_strand(), 'F')


class TestReferenceGenomeModel(TestCase):
    """
    Tests instance and class methods for :class:`ReferenceGenome`
    """
    def test_get_identifier_instance_returns_ensemble_as_default(self):
        ref = ReferenceGenomeFactory(
            refseq_id=RefseqIdentifierFactory(),
            ensembl_id=EnsemblIdentifierFactory()
        )
        self.assertEqual(ref.get_identifier_instance(), ref.get_ensembl_id())

    def test_get_id_methods_return_none_if_no_associations(self):
        ref = ReferenceGenomeFactory()
        self.assertIsNone(ref.get_identifier())
        self.assertIsNone(ref.get_identifier_url())
        self.assertIsNone(ref.get_identifier_instance())

    def test_format_species_name_captializes(self):
        ref = ReferenceGenomeFactory()
        self.assertIn(
            ref.get_species_name().capitalize(),
            ref.format_species_name_html()
        )


class TestAnnotationModel(TestCase):
    """
    Tests instance and class methods for :class:`Annotation`
    """
    def test_set_is_primary_saves_annotation(self):
        ann = AnnotationFactory()
        ann.get_genome().set_is_primary(False)
        ann.get_genome().save()
        ann.refresh_from_db()
        self.assertEqual(ann.is_primary_annotation(), False)

    def test_does_not_have_genome_if_genome_is_none(self):
        ann = AnnotationFactory()
        ann.genome = None
        self.assertFalse(ann.has_genome())
        self.assertIsNone(ann.get_genome())


class TestTargetGene(TestCase):
    """
    Tests instance and class methods for :class:`TargetGene`
    """
    def test_does_not_have_wt_sequence_if_is_none(self):
        target = TargetGeneFactory()
        target.wt_sequence = None
        self.assertFalse(target.has_wt_sequence())
        self.assertIsNone(target.get_wt_sequence())

    def test_get_primary_reference_defaults_to_first_in_alpha_order(self):
        target = TargetGeneFactory()
        annotations = [
            AnnotationFactory(target=target),
            AnnotationFactory(target=target),
        ]
        annotations[1].get_genome().short_name = 'aaa'
        annotations[1].get_genome().save()
        self.assertEqual(
            target.get_primary_reference(), annotations[1].get_genome())

    def test_can_get_ref_genomes(self):
        target = TargetGeneFactory()
        self.assertEqual(target.get_reference_genomes().count(), 0)

        AnnotationFactory(target=target)
        self.assertEqual(target.get_reference_genomes().count(), 1)
