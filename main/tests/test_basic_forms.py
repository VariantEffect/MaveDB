
from django.test import TestCase
from django.core.exceptions import ValidationError

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

    def test_cannot_save_blank_input(self):
        form = KeywordForm(data={"text": ""})
        self.assertFalse(form.is_valid())
