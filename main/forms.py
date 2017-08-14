
import datetime

from django import forms
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse

from .models import (
    Keyword, ExternalAccession,
    TargetOrganism, ReferenceMapping
)


class KeywordForm(forms.ModelForm):
    """
    Keyword `ModelForm` to be instantiated with a dictionary or an
    existing instance.
    """
    class Meta:
        model = Keyword
        fields = ("text", )


class ExternalAccessionForm(forms.ModelForm):
    """
    ExternalAccession `ModelForm` to be instantiated with a dictionary or an
    existing instance.
    """
    class Meta:
        model = ExternalAccession
        fields = ("text",)


class TargetOrganismForm(forms.ModelForm):
    """
    TargetOrganism `ModelForm` to be instantiated with a dictionary or an
    existing instance.
    """
    class Meta:
        model = TargetOrganism
        fields = ("text",)


class ReferenceMappingForm(forms.ModelForm):
    """
    ReferenceMapping `ModelForm` to be instantiated with a dictionary or an
    existing instance. Performs additional cleaned to ensure the mapping
    ranges are valid intervals.
    """
    class Meta:
        model = ReferenceMapping
        fields = (
            "reference",
            "is_alternate",
            "target_start",
            "target_end",
            "reference_start",
            "reference_end"
        )

    def clean(self):
        cleaned_data = super(ReferenceMappingForm, self).clean()
        target_start = cleaned_data.get("target_start", 0)
        target_end = cleaned_data.get("target_end", 0)
        reference_start = cleaned_data.get("reference_start", 0)
        reference_end = cleaned_data.get("reference_end", 0)

        if target_start >= target_end:
            self.add_error("target_start", ValidationError(
                _("Target start must be less than target end."),
            ))
        if reference_start >= reference_end:
            self.add_error("reference_start", ValidationError(
                _("Reference start must be less than reference end."),
            ))

        return cleaned_data
