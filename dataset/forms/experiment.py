from django import forms as forms
from django.db import transaction
from django.core.exceptions import ValidationError

from ..forms.base import DatasetModelForm
from ..models.base import DatasetModel
from ..models.experiment import Experiment
from ..models.experimentset import ExperimentSet


class ExperimentForm(DatasetModelForm):
    """
    Docstring
    """
    class Meta(DatasetModel.Meta):
        model = Experiment
        fields = DatasetModelForm.Meta.fields + (
            'experimentset',
        )

    def __init__(self, *args, **kwargs):
        self.field_order = ('experimentset',) + self.FIELD_ORDER
        super().__init__(*args, **kwargs)

        self.fields['experimentset'] = forms.ModelChoiceField(
            queryset=None, required=False, widget=forms.Select(
                attrs={"class": "form-control"})
        )
        self.set_experimentset_options()

    def clean(self):
        cleaned_data = super().clean()
        experimentset = cleaned_data.get('experimentset', None)
        if 'experimentset' in self.fields and self.instance.pk is not None:
            if self.instance.experimentset != experimentset:
                raise ValidationError(
                    "MaveDB does not currently support changing a "
                    "previously assigned Experiment Set.")

    @transaction.atomic
    def save(self, commit=True):
        return super().save(commit=commit)

    def set_experimentset_options(self):
        if 'experimentset' in self.fields:
            choices = self.user.profile.contributor_experimentsets()
            choices_qs = ExperimentSet.objects.filter(
                pk__in=set([i.pk for i in choices])).order_by("urn")
            self.fields["experimentset"].queryset = choices_qs

    @classmethod
    def from_request(cls, request, instance):
        form = super().from_request(request, instance)
        if 'experimentset' in form.fields:
            choices_qs = ExperimentSet.objects.filter(
                pk__in=[instance.experimentset.pk]).order_by("urn")
            form.fields["experimentset"].queryset = choices_qs
            form.fields["experimentset"].initial = instance.experimentset
        return form


class ExperimentEditForm(ExperimentForm):
    """
    A subset of `ExperimentForm` for editiing instances. Follows the same
    logic as `ExperimentForm`
    """
    def __init__(self, *args, **kwargs):
        if 'instance' not in kwargs:
            raise ValueError(
                "An existing instance is required to instantiate "
                "an edit form.")
        super().__init__(*args, **kwargs)
        self.edit_mode = True
        self.fields.pop('experimentset')
