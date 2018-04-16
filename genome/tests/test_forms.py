from django.test import TestCase

from accounts.factories import UserFactory
from accounts.permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_contributor,
    assign_user_as_instance_viewer
)

from dataset.constants import nan_col_values

from ..models import Annotation, Interval, WildTypeSequence
from ..factories import (
    TargetGeneFactory,
    AnnotationFactory,
    ReferenceGenomeFactory,
    IntervalFactory
)

from ..forms import (
    IntervalForm,
    IntervalFormSet,
    AnnotationForm,
    AnnotationFormSet,
    TargetGeneForm
)


class TestIntervalForm(TestCase):
    """
    Tests that :class:`IntervalForm` raises the appropriate errors when
    invalid input is supplied; and can update existing instances.
    """
    def test_ve_end_less_than_start(self):
        data = {
            'start': 2, 'end': 1,
            'chromosome': 'chrX', 'strand': 'F',
        }
        self.assertFalse(IntervalForm(data=data).is_valid())

    def test_ve_partially_filled_out_form(self):
        data = {
            'start': '', 'end': 1,
            'chromosome': 'chrX', 'strand': 'F',
        }
        self.assertFalse(IntervalForm(data=data).is_valid())

        data = {
            'start': 1, 'end': '',
            'chromosome': 'chrX', 'strand': 'F',
        }
        self.assertFalse(IntervalForm(data=data).is_valid())

    def test_ve_chromosome_null_value(self):
        for value in nan_col_values:
            data = {
                'start': 1, 'end': 2,
                'chromosome': value, 'strand': 'F',
            }
            self.assertFalse(IntervalForm(data=data).is_valid())

    def test_ve_strand_null_value(self):
        for value in nan_col_values:
            data = {
                'start': 1, 'end': 2,
                'chromosome': 'chr21', 'strand': value,
            }
            self.assertFalse(IntervalForm(data=data).is_valid())

    def test_updates_existing(self):
        data = {
            'start': 1, 'end': 2,
            'chromosome': 'chr21', 'strand': 'F',
        }
        instance = IntervalFactory()
        instance = IntervalForm(data=data, instance=instance).save(commit=True)
        self.assertEqual(instance.serialise(), data)


class TestAnnotationForm(TestCase):
    """
    Tests that :class:`AnnotationForm` raises the appropriate errors when
    invalid input is supplied; and can update existing instances.
    """
    def test_ve_selected_genome_does_not_exist(self):
        data = {'genome': 1, 'is_primary': True}
        form = AnnotationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_ve_no_selected_genome(self):
        data = {'genome': 1, 'is_primary': True}
        form = AnnotationForm(data=data)
        self.assertFalse(form.is_valid())

    def test_updates_existing(self):
        ref = ReferenceGenomeFactory()
        instance = AnnotationFactory()
        data = {'genome': ref.pk, 'is_primary': True}
        form = AnnotationForm(data=data, instance=instance)
        instance = form.save(commit=True)
        self.assertEqual(instance.is_primary_annotation(), data['is_primary'])
        self.assertEqual(instance.get_reference_genome(), ref)


class TestTargetGeneForm(TestCase):
    """
    Tests that :class:`TargetGeneForm` raises the appropriate errors when
    invalid input is supplied; and can update existing instances.
    """
    def setUp(self):
        self.user = UserFactory()

    def test_ve_null_wt_sequence(self):
        for v in nan_col_values:
            data = {'wt_sequence': v, 'name': 'brca1'}
            form = TargetGeneForm(user=self.user, data=data)
            self.assertFalse(form.is_valid())

    def test_ve_non_nucleotide_sequence(self):
        data = {'wt_sequence': 'fhfa', 'name': 'brca1'}
        form = TargetGeneForm(user=self.user, data=data)
        self.assertFalse(form.is_valid())

    def test_ve_null_name(self):
        for v in nan_col_values:
            data = {'wt_sequence': 'atcg', 'name': v}
            form = TargetGeneForm(user=self.user, data=data)
            self.assertFalse(form.is_valid())

    def test_initial_sets_wt_sequence_field(self):
        instance = TargetGeneFactory()
        form = TargetGeneForm(user=self.user, instance=instance)
        self.assertEqual(
            form.fields['wt_sequence'].initial,
            instance.get_wt_sequence_string()
        )
        self.assertEqual(
            form.existing_wt_sequence,
            instance.get_wt_sequence()
        )

    def test_private_targets_hidden_if_user_has_no_permissions(self):
        instance = TargetGeneFactory()
        instance.scoreset.private = True
        instance.scoreset.save()

        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields['target'].queryset.count(), 0)

    def test_private_targets_shown_if_user_has_permissions(self):
        instance = TargetGeneFactory()
        instance.scoreset.private = True
        instance.scoreset.save()

        assign_user_as_instance_admin(self.user, instance.scoreset)
        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields['target'].queryset.count(), 1)

        assign_user_as_instance_contributor(self.user, instance.scoreset)
        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields['target'].queryset.count(), 1)

        assign_user_as_instance_viewer(self.user, instance.scoreset)
        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields['target'].queryset.count(), 1)

    def test_public_targets_shown_as_options(self):
        instance = TargetGeneFactory()
        instance.scoreset.private = False
        instance.scoreset.save()

        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields['target'].queryset.count(), 1)

    def test_save_sets_wt_sequence(self):
        data = {'wt_sequence': 'atcg', 'name': 'brca1'}
        form = TargetGeneForm(user=self.user, data=data)
        instance = form.save(commit=True)
        self.assertIsNotNone(instance.get_wt_sequence_string())
        self.assertEqual(instance.get_wt_sequence_string(), 'ATCG')

    def test_updates_existing_wt_sequence(self):
        instance = TargetGeneFactory()
        wt = instance.get_wt_sequence()
        data = {'name': 'JAK', 'wt_sequence': 'CCCC'}
        form = TargetGeneForm(user=self.user, data=data, instance=instance)
        instance = form.save(commit=True)
        self.assertEqual(instance.get_name(), data['name'])
        self.assertEqual(
            instance.get_wt_sequence_string(),
            data['wt_sequence'].upper())
        self.assertEqual(instance.get_wt_sequence(), wt)
        self.assertEqual(WildTypeSequence.objects.count(), 1)


class TestIntervalFormSet(TestCase):
    """
    Test the :class:`IntervalFormSet` can validate intervals against each other
    to detect repeated intervals and can modify inital querysets.
    """
    pass


class TestAnnotationFormSet(TestCase):
    """
    Test the :class:`AnnotationFormSet` can validate intervals against each
    other to detect repeated intervals and can modify inital querysets.
    """
    pass