from django.test import TestCase
from django.forms.formsets import (
    TOTAL_FORM_COUNT, INITIAL_FORM_COUNT,
    MIN_NUM_FORM_COUNT, MAX_NUM_FORM_COUNT,
)

from dataset.constants import nan_col_values

from ..factories import (
    ReferenceMapFactory,
    TargetGeneFactory,
    ReferenceGenomeFactory,
    GenomicIntervalFactory
)
from ..models import GenomicInterval, ReferenceMap
from ..forms import create_genomic_interval_formset


GenomicIntervaLFormSet = create_genomic_interval_formset(
    extra=2, min_num=1, can_delete=False
)


class TestGenomicIntervalFormset(TestCase):
    @staticmethod
    def prefix():
        return 'form'

    @staticmethod
    def management_form():
        return {
            'form-' + TOTAL_FORM_COUNT: 3,
            'form-' + INITIAL_FORM_COUNT: 0,
            'form-' + MIN_NUM_FORM_COUNT: 1,
            'form-' + MAX_NUM_FORM_COUNT: 1000
        }

    @staticmethod
    def test_data():
        prefix = 'form'
        dict_ = {
            # Form 1
            '{}-0-start'.format(prefix): '1',
            '{}-0-end'.format(prefix): '2',
            '{}-0-chromosome'.format(prefix): 'chr1',
            '{}-0-strand'.format(prefix): '+',
            # Form 2
            '{}-1-start'.format(prefix): '2',
            '{}-1-end'.format(prefix): '3',
            '{}-1-chromosome'.format(prefix): 'chr2',
            '{}-1-strand'.format(prefix): '-',
            # Form 3
            '{}-2-start'.format(prefix): '3',
            '{}-2-end'.format(prefix): '4',
            '{}-2-chromosome'.format(prefix): 'chr3',
            '{}-2-strand'.format(prefix): '+',
        }
        dict_.update(TestGenomicIntervalFormset.management_form())
        return dict_

    def test_can_save_all_formset_instances(self):
        rm = ReferenceMapFactory()
        data = self.test_data()
        formset = GenomicIntervaLFormSet(data=data)
        self.assertTrue(formset.is_valid())
        intervals = formset.save(reference_map=rm)
        for i, interval in enumerate(intervals):
            start = int(data.get("{}-{}-start".format(self.prefix(), i)))
            end = int(data.get("{}-{}-end".format(self.prefix(), i)))
            strand = data.get("{}-{}-strand".format(self.prefix(), i))
            chromosome = data.get("{}-{}-chromosome".format(self.prefix(), i))
            self.assertEqual(interval.reference_map, rm)
            self.assertEqual(interval.start, start)
            self.assertEqual(interval.end, end)
            self.assertEqual(interval.strand, strand)
            self.assertEqual(interval.chromosome, chromosome)

    def test_validation_error_non_unique_intervals(self):
        data = self.test_data()
        data["%s-1-start" % self.prefix()] = 1
        data["%s-1-end" % self.prefix()] = 2
        data["%s-1-chromosome" % self.prefix()] = 'chr1'
        data["%s-1-strand" % self.prefix()] = '+'
        formset = GenomicIntervaLFormSet(data=data)
        self.assertFalse(formset.is_valid())
        self.assertTrue(formset.non_form_errors)

    def test_empty_formset_has_no_initial_data(self):
        formset = GenomicIntervaLFormSet()
        self.assertEqual(formset.queryset.count(), 0)
        self.assertFalse(formset.initial_forms)

    def test_invalid_less_than_one_form(self):
        data = self.management_form()
        data["%s-1-start" % self.prefix()] = 1
        data["%s-1-end" % self.prefix()] = 2
        data["%s-1-chromosome" % self.prefix()] = 'chr1'
        data["%s-1-strand" % self.prefix()] = '+'
        formset = GenomicIntervaLFormSet(data=data)
        self.assertFalse(formset.is_valid())
        self.assertTrue(formset.non_form_errors)

    def test_invalid_unfilled_forms(self):
        data = self.test_data()
        data["%s-1-start" % self.prefix()] = ""
        data["%s-1-end" % self.prefix()] = ""
        data["%s-1-chromosome" % self.prefix()] = ""
        data["%s-1-strand" % self.prefix()] = ""
        formset = GenomicIntervaLFormSet(data=data)
        self.assertFalse(formset.is_valid())

    def test_invalid_partial_forms(self):
        for value in nan_col_values:
            data = self.test_data()
            data["%s-1-start" % self.prefix()] = "1"
            data["%s-1-end" % self.prefix()] = "2"
            data["%s-1-chromosome" % self.prefix()] = "chr2"
            data["%s-1-strand" % self.prefix()] = value
            formset = GenomicIntervaLFormSet(data=data)
            self.assertFalse(formset.is_valid())

    def test_initial_forms_from_queryset_are_valid(self):
        g1 = GenomicIntervalFactory()
        g2 = GenomicIntervalFactory()
        g3 = GenomicIntervalFactory()

        queryset = GenomicInterval.objects.all()
        data = self.test_data()
        data['form-' + INITIAL_FORM_COUNT] = queryset.count()
        data['form-' + TOTAL_FORM_COUNT] = queryset.count() + 2  # extra
        data['form-0-id'] = g1.pk
        data['form-1-id'] = g2.pk
        data['form-2-id'] = g3.pk
        formset = GenomicIntervaLFormSet(data, queryset=queryset)

        self.assertEqual(formset.initial_form_count(), 3)
        self.assertEqual(formset.total_form_count(), 5)
        for form in formset.forms:
            if form.instance.pk:
                self.assertTrue(form.is_valid())

    def test_initial_forms_will_update(self):
        g1 = GenomicIntervalFactory()
        g2 = GenomicIntervalFactory()
        g3 = GenomicIntervalFactory()
        queryset = GenomicInterval.objects.all()

        data = self.test_data()
        data['form-' + INITIAL_FORM_COUNT] = 3
        data['form-' + TOTAL_FORM_COUNT] = 3
        data['form-0-id'] = g1.pk
        data['form-1-id'] = g2.pk
        data['form-2-id'] = g3.pk

        formset = GenomicIntervaLFormSet(data, queryset=queryset)
        self.assertTrue(formset.is_valid())

        intervals = formset.save()
        self.assertTrue(GenomicInterval.objects.count(), 3)
        for i, interval in enumerate(intervals):
            start = int(data.get("{}-{}-start".format(self.prefix(), i)))
            end = int(data.get("{}-{}-end".format(self.prefix(), i)))
            strand = data.get("{}-{}-strand".format(self.prefix(), i))
            chromosome = data.get("{}-{}-chromosome".format(self.prefix(), i))
            self.assertEqual(interval.start, start)
            self.assertEqual(interval.end, end)
            self.assertEqual(interval.strand, strand)
            self.assertEqual(interval.chromosome, chromosome)

    def test_can_reset_reference_map(self):
        rm = ReferenceMapFactory()
        g1 = GenomicIntervalFactory()
        g2 = GenomicIntervalFactory()
        g3 = GenomicIntervalFactory()
        queryset = GenomicInterval.objects.all()

        data = self.test_data()
        data['form-' + INITIAL_FORM_COUNT] = 3
        data['form-' + TOTAL_FORM_COUNT] = 3
        data['form-0-id'] = g1.pk
        data['form-1-id'] = g2.pk
        data['form-2-id'] = g3.pk

        formset = GenomicIntervaLFormSet(data, queryset=queryset)
        self.assertTrue(formset.is_valid())

        intervals = formset.save(reference_map=rm)
        self.assertTrue(GenomicInterval.objects.count(), 3)
        for i, interval in enumerate(intervals):
            start = int(data.get("{}-{}-start".format(self.prefix(), i)))
            end = int(data.get("{}-{}-end".format(self.prefix(), i)))
            strand = data.get("{}-{}-strand".format(self.prefix(), i))
            chromosome = data.get("{}-{}-chromosome".format(self.prefix(), i))
            self.assertEqual(interval.start, start)
            self.assertEqual(interval.end, end)
            self.assertEqual(interval.strand, strand)
            self.assertEqual(interval.chromosome, chromosome)
            self.assertEqual(interval.reference_map, rm)

    def test_value_error_save_new_with_no_ref_map(self):
        data = self.test_data()
        formset = GenomicIntervaLFormSet(data=data)
        self.assertTrue(formset.is_valid())
        with self.assertRaises(ValueError):
            formset.save(reference_map=None)

    def test_value_error_save_with_unsaved_rm(self):
        data = self.test_data()
        rm = ReferenceMap()
        rm.target = TargetGeneFactory()
        rm.genome = ReferenceGenomeFactory()
        formset = GenomicIntervaLFormSet(data=data)
        self.assertTrue(formset.is_valid())
        with self.assertRaises(ValueError):
            formset.save(reference_map=rm)
