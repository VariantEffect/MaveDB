from django.test import TestCase
from django.forms import formset_factory
from django.forms.formsets import (
    TOTAL_FORM_COUNT, INITIAL_FORM_COUNT,
    MIN_NUM_FORM_COUNT, MAX_NUM_FORM_COUNT,
)

from dataset.constants import nan_col_values

from ..factories import (
    TargetGeneFactory,
    ReferenceMapFactory,
    ReferenceGenomeFactory,
    GenomicIntervalFactory
)
from ..models import GenomicInterval
from ..forms import (
    GenomicIntervalForm,
    GenomicIntervaLFormSet,
    BaseGenomicIntervalFormSet,
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

    # def test_can_save_all_formset_instances(self):
    #     rm = ReferenceMapFactory()
    #     data = self.test_data()
    #     formset = GenomicIntervaLFormSet(data=data)
    #     self.assertTrue(formset.is_valid())
    #     intervals = formset.save(reference_map=rm)
    #     for i, interval in enumerate(intervals):
    #         start = int(data.get("{}-{}-start".format(self.prefix(), i)))
    #         end = int(data.get("{}-{}-end".format(self.prefix(), i)))
    #         strand = data.get("{}-{}-strand".format(self.prefix(), i))
    #         chromosome = data.get("{}-{}-chromosome".format(self.prefix(), i))
    #         self.assertEqual(interval.reference_map, rm)
    #         self.assertEqual(interval.start, start)
    #         self.assertEqual(interval.end, end)
    #         self.assertEqual(interval.strand, strand)
    #         self.assertEqual(interval.chromosome, chromosome)

    def test_validation_error_non_unique_intervals(self):
        data = self.test_data()
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
        data = self.test_data()
        data["%s-1-start" % self.prefix()] = "1"
        data["%s-1-end" % self.prefix()] = "2"
        data["%s-1-chromosome" % self.prefix()] = "chr2"
        data["%s-1-strand" % self.prefix()] = ""
        formset = GenomicIntervaLFormSet(data=data)
        self.assertFalse(formset.is_valid())

    def test_initial_forms_correct(self):
        g1 = GenomicIntervalFactory()
        g2 = GenomicIntervalFactory()
        g3 = GenomicIntervalFactory()
        queryset = GenomicInterval.objects.all()
        data = self.management_form()
        data[INITIAL_FORM_COUNT] = queryset.count()
        data[TOTAL_FORM_COUNT] = queryset.count() + 2  # extra
        formset = GenomicIntervaLFormSet(queryset=queryset, data=data)
        for form in formset:
            if form.instance.pk:
                self.assertTrue(form.is_valid())

    def test_initial_forms_will_update(self):
        FormSet = formset_factory(
            form=GenomicIntervalForm, formset=BaseGenomicIntervalFormSet,
            extra=0, min_num=1, validate_min=True,
        )
        g1 = GenomicIntervalFactory()
        g2 = GenomicIntervalFactory()
        g3 = GenomicIntervalFactory()
        queryset = GenomicInterval.objects.all()
        data = self.test_data()
        data[INITIAL_FORM_COUNT] = 0
        data[TOTAL_FORM_COUNT] = queryset.count()
        formset = FormSet(data, queryset=queryset)
        self.assertTrue(formset.is_valid())
        print(formset)

        intervals = formset.save()
        for i, interval in enumerate(intervals):
            start = int(data.get("{}-{}-start".format(self.prefix(), i)))
            end = int(data.get("{}-{}-end".format(self.prefix(), i)))
            strand = data.get("{}-{}-strand".format(self.prefix(), i))
            chromosome = data.get("{}-{}-chromosome".format(self.prefix(), i))
            self.assertEqual(interval.start, start)
            self.assertEqual(interval.end, end)
            self.assertEqual(interval.strand, strand)
            self.assertEqual(interval.chromosome, chromosome)
