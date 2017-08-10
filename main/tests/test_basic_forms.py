
from django.test import TestCase
from django.core.exceptions import ValidationError

from experiment.models import Experiment

from main.models import (
    Keyword, TargetOrganism,
    ExternalAccession, ReferenceMapping
)

from main.forms import (
    KeywordForm, TargetOrganismForm,
    ExternalAccessionForm, ReferenceMappingForm
)


class TestKeywordForm(TestCase):

    def test_can_save_from_form(self):
        form = KeywordForm(data={"text": "keyword 1"})
        form.save()
        model = Keyword.objects.all()[0]
        self.assertEqual(model.text, "keyword 1")

    def test_can_initialise_form_with_instance_and_save(self):
        model = Keyword.objects.create(text="test")
        form = KeywordForm(data={"text": "test_2"}, instance=model)
        self.assertTrue(form.is_valid())
        form.save()
        model.refresh_from_db()
        self.assertEqual(model.text, "test_2")

    def test_blank_not_valid(self):
        form = KeywordForm(data={"text": ""})
        self.assertFalse(form.is_valid())

    def test_null_not_valid(self):
        form = KeywordForm(data={"text": None})
        self.assertFalse(form.is_valid())

    def test_non_unique_not_valid(self):
        Keyword.objects.create(text="keyword")
        form = KeywordForm(data={"text": "keyword"})
        self.assertFalse(form.is_valid())


class TestExternalAccessionForm(TestCase):

    def test_can_save_from_form(self):
        form = ExternalAccessionForm(data={"text": "test"})
        form.save()
        model = ExternalAccession.objects.all()[0]
        self.assertEqual(model.text, "test")

    def test_can_initialise_form_with_instance_and_save(self):
        model = ExternalAccession.objects.create(text="test")
        form = ExternalAccessionForm(data={"text": "test_2"}, instance=model)
        self.assertTrue(form.is_valid())
        form.save()
        model.refresh_from_db()
        self.assertEqual(model.text, "test_2")

    def test_blank_not_valid(self):
        form = ExternalAccessionForm(data={"text": ""})
        self.assertFalse(form.is_valid())

    def test_null_not_valid(self):
        form = ExternalAccessionForm(data={"text": None})
        self.assertFalse(form.is_valid())

    def test_non_unique_not_valid(self):
        ExternalAccession.objects.create(text="test")
        form = ExternalAccessionForm(data={"text": "test"})
        self.assertFalse(form.is_valid())


class TestTargetOrganismForm(TestCase):

    def test_can_save_from_form(self):
        form = TargetOrganismForm(data={"text": "test"})
        form.save()
        model = TargetOrganism.objects.all()[0]
        self.assertEqual(model.text, "test")

    def test_can_initialise_form_with_instance_and_save(self):
        model = TargetOrganism.objects.create(text="test")
        form = TargetOrganismForm(data={"text": "test_2"}, instance=model)
        self.assertTrue(form.is_valid())
        form.save()
        model.refresh_from_db()
        self.assertEqual(model.text, "test_2")

    def test_blank_not_valid(self):
        form = TargetOrganismForm(data={"text": ""})
        self.assertFalse(form.is_valid())

    def test_null_not_valid(self):
        form = TargetOrganismForm(data={"text": None})
        self.assertFalse(form.is_valid())

    def test_non_unique_not_valid(self):
        TargetOrganism.objects.create(text="test")
        form = TargetOrganismForm(data={"text": "test"})
        self.assertFalse(form.is_valid())


class TestReferenceMappingForm(TestCase):

    def setUp(self):
        self.experiment = Experiment.objects.create(
            target="brca1", wt_sequence="atcg"
        )
        self.base_data = {
            "reference": "test",
        }

    def make_test_data(self, ts, te, rs, re):
        data = self.base_data.copy()
        data["target_start"] = ts
        data["target_end"] = te
        data["reference_start"] = rs
        data["reference_end"] = re
        return data

    def test_can_initialise_form_with_instance_and_save(self):
        model = ReferenceMapping.objects.create(
            **self.make_test_data(0, 10, 0, 10)
        )
        form = ReferenceMappingForm(
            data=self.make_test_data(2, 10, 0, 10),
            instance=model
        )
        self.assertTrue(form.is_valid())
        form.save()
        model.refresh_from_db()
        self.assertEqual(model.target_start, 2)

    def test_can_save_from_form(self):
        form = ReferenceMappingForm(data=self.make_test_data(0, 10, 0, 10))
        form.save()
        model = ReferenceMapping.objects.all()[0]
        self.assertEqual(model.reference, "test")
        self.assertEqual(model.is_alternate, False)
        self.assertEqual(model.target_start, 0)
        self.assertEqual(model.target_end, 10)
        self.assertEqual(model.reference_start, 0)
        self.assertEqual(model.reference_end, 10)

    def test_not_valid_negative_target_start(self):
        form = ReferenceMappingForm(data=self.make_test_data(-1, 10, 0, 10))
        self.assertFalse(form.is_valid())

    def test_not_valid_negative_target_end(self):
        form = ReferenceMappingForm(data=self.make_test_data(-20, -10, 0, 10))
        self.assertFalse(form.is_valid())

    def test_not_valid_negative_ref_start(self):
        form = ReferenceMappingForm(data=self.make_test_data(0, 10, -1, 10))
        self.assertFalse(form.is_valid())

    def test_not_valid_negative_ref_end(self):
        form = ReferenceMappingForm(data=self.make_test_data(0, 10, -20, -10))
        self.assertFalse(form.is_valid())

    def test_not_valid_start_gt_end(self):
        form = ReferenceMappingForm(data=self.make_test_data(20, 10, 0, 10))
        self.assertFalse(form.is_valid())
        form = ReferenceMappingForm(data=self.make_test_data(0, 10, 20, 10))
        self.assertFalse(form.is_valid())

    def test_blank_not_valid(self):
        data = self.make_test_data(0, 10, 0, 10)
        data['reference'] = ""
        form = TargetOrganismForm(data=data)
        self.assertFalse(form.is_valid())

    def test_null_not_valid(self):
        data = self.make_test_data(0, 10, 0, 10)
        data['reference'] = None
        form = TargetOrganismForm(data=data)
        self.assertFalse(form.is_valid())
