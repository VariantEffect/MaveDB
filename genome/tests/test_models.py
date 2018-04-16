from django.test import TestCase
from django.core.exceptions import ValidationError

from metadata.factories import (
    EnsemblIdentifierFactory, RefseqIdentifierFactory
)

from ..models import WildTypeSequence
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

    def test_serialisation(self):
        wt = WildTypeSequenceFactory(sequence='atcg')
        self.assertEqual({'sequence': wt.get_sequence()}, wt.serialise())


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

    def test_serialisation(self):
        interval = IntervalFactory()
        self.assertEqual(
            {
                'start': interval.get_start(),
                'end': interval.get_end(),
                'chromosome': interval.get_chromosome(),
                'strand': interval.get_strand()
            },
            interval.serialise()
        )


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

    def test_format_species_name_html_capitalises(self):
        ref = ReferenceGenomeFactory()
        expected = "<i>{}</i>".format(ref.get_species_name().capitalize())
        self.assertEqual(ref.format_species_name_html(), expected)

    def test_serialisation_serialises_name_and_species(self):
        ref = ReferenceGenomeFactory()
        dict_ = ref.serialise()
        self.assertEqual(dict_['short_name'], ref.get_short_name())
        self.assertEqual(dict_['species_name'], ref.get_species_name())

    def test_serialisation_when_eids_are_none(self):
        ref = ReferenceGenomeFactory()
        dict_ = ref.serialise()
        self.assertIsNone(
            dict_['external_identifiers']['ensembl']['identifier'])
        self.assertIsNone(
            dict_['external_identifiers']['ensembl']['url'])

        self.assertIsNone(
            dict_['external_identifiers']['refseq']['identifier'])
        self.assertIsNone(
            dict_['external_identifiers']['refseq']['url'])

    def test_serialisation_when_eids_are_not_none(self):
        ref = ReferenceGenomeFactory()
        ensembl = EnsemblIdentifierFactory()
        refseq = RefseqIdentifierFactory()
        ref.ensembl_id = ensembl
        ref.refseq_id = refseq
        ref.save()

        dict_ = ref.serialise()
        self.assertEqual(
            dict_['external_identifiers']['ensembl']['identifier'],
            ensembl.identifier
        )
        self.assertEqual(
            dict_['external_identifiers']['ensembl']['url'],
            ensembl.url
        )

        self.assertEqual(
            dict_['external_identifiers']['refseq']['identifier'],
            refseq.identifier
        )
        self.assertEqual(
            dict_['external_identifiers']['refseq']['url'],
            refseq.url
        )


class TestAnnotationModel(TestCase):
    """
    Tests instance and class methods for :class:`Annotation`
    """
    def test_set_is_primary_does_not_save_annotation(self):
        ann = AnnotationFactory()
        ann.set_is_primary(False)
        ann.refresh_from_db()
        self.assertEqual(ann.is_primary_annotation(), True)

    def test_does_not_have_genome_if_genome_is_none(self):
        ann = AnnotationFactory()
        ann.genome = None
        ann.save()
        self.assertIsNone(ann.get_reference_genome())

    def test_can_get_intervals_when_there_are_no_associations(self):
        ann = AnnotationFactory()
        self.assertIsNotNone(ann.get_intervals())

    def test_empty_list_no_intervals_in_serialisation(self):
        ann = AnnotationFactory()
        dict_ = ann.serialise()
        expected = {
            'intervals': [],
            'reference_genome': ann.get_reference_genome().serialise(),
            'primary': ann.is_primary_annotation()
        }
        self.assertEqual(expected, dict_)

    def test_list_of_serialised_intervals_if_associations_exist(self):
        annotation = AnnotationFactory()
        interval = IntervalFactory(annotation=annotation)
        dict_ = annotation.serialise()
        self.assertEqual(dict_['intervals'], [interval.serialise()])

    def test_reference_genome_none_if_no_association(self):
        ann = AnnotationFactory(genome=None)
        dict_ = ann.serialise()
        self.assertIsNone(dict_['reference_genome'])


class TestTargetGene(TestCase):
    """
    Tests instance and class methods for :class:`TargetGene`
    """
    def test_does_not_have_wt_sequence_if_is_none(self):
        target = TargetGeneFactory()
        target.wt_sequence = None
        self.assertIsNone(target.get_wt_sequence())

    def test_ve_set_invalid_sequence(self):
        target = TargetGeneFactory()
        with self.assertRaises(ValidationError):
            target.set_wt_sequence('gggg')

    def test_ae_set_sequence_with_str_when_no_attached_sequences(self):
        target = TargetGeneFactory(wt_sequence=None)
        with self.assertRaises(AttributeError):
            target.set_wt_sequence('atcg')

    def test_set_wt_sequence_with_instance_deletes_exisiting(self):
        target = TargetGeneFactory()
        wt = WildTypeSequenceFactory()

        target.set_wt_sequence(wt)
        self.assertEqual(WildTypeSequence.objects.count(), 2)

        target.save()
        self.assertEqual(WildTypeSequence.objects.count(), 1)
        self.assertEqual(target.get_wt_sequence(), wt)

    def test_set_wt_sequence_with_string_only_sets_existing_sequence(self):
        target = TargetGeneFactory()
        wt = WildTypeSequenceFactory()

        target.set_wt_sequence(wt.sequence)
        self.assertEqual(WildTypeSequence.objects.count(), 2)

        target.save()
        self.assertEqual(WildTypeSequence.objects.count(), 2)
        self.assertNotEqual(target.get_wt_sequence(), wt)
        self.assertEqual(target.get_wt_sequence_string(), wt.get_sequence())

    def test_can_get_ref_genomes(self):
        target = TargetGeneFactory()
        self.assertEqual(target.get_reference_genomes().count(), 0)

        AnnotationFactory(target=target)
        self.assertEqual(target.get_reference_genomes().count(), 1)

    def test_wt_seq_is_none_in_serialisation_if_no_association(self):
        targetgene = TargetGeneFactory(wt_sequence=None)
        self.assertIsNone(targetgene.serialise()['wt_sequence'])

    def test_empty_list_annotations_if_no_associations(self):
        target = TargetGeneFactory()
        annotation = AnnotationFactory(target=target)
        dict_ = target.serialise()
        self.assertEqual(dict_['annotations'], [annotation.serialise()])
