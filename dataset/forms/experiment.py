from django import forms as forms
from django.db import transaction

from genome.models import TargetOrganism
from genome.validators import (
    validate_target_gene,
    validate_target_organism,
    validate_wildtype_sequence
)
from metadata.fields import ModelSelectMultipleField

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
            'target',
            'wt_sequence',
            'target_organism',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['experimentset'] = forms.ModelChoiceField(
            queryset=None, required=False, widget=forms.Select(
                attrs={"class": "form-control"})
        )
        self.fields['target_organism'] = ModelSelectMultipleField(
            klass=TargetOrganism, to_field_name='text',
            required=False, queryset=None, widget=forms.SelectMultiple(
                attrs={"class": "form-control select2 select2-token-select"})
        )
        self.fields['wt_sequence'].widget = forms.Textarea(
            attrs={"class": "form-control"})

        # TODO: This will become a Foreign Key field when
        # Target becomes a table
        self.fields['target'].widget = forms.TextInput(
            attrs={"class": "form-control"})

        self.fields["target"].validators.append(validate_target_gene)
        self.fields["target_organism"].validators.append(
            validate_target_organism)
        self.fields["wt_sequence"].validators.append(
            validate_wildtype_sequence)

        self.fields["target_organism"].queryset = TargetOrganism.objects.all()
        # Populate the experimentset drop down with a list of experimentsets
        # that the user for this form has write access to.
        self.set_experimentset_options()

    def clean_target_organism(self):
        return self._clean_field_name('target_organism')

    def _save_m2m(self):
        # Save all target_organism instances before calling super()
        # so that all new instances are in the database before m2m
        # relationships are created.
        if 'target_organism' in self.fields:
            for instance in self.cleaned_data.get('target_organism'):
                instance.save()
            self.instance.clear_m2m('target_organism')
        super()._save_m2m()

    @transaction.atomic
    def save(self, commit=True):
        super().save(commit=commit)

    def set_experimentset_options(self):
        if 'experimentset' in self.fields:
            choices = self.user.profile.administrator_experimentsets() + \
                      self.user.profile.contributor_experimentsets()
            choices_qs = ExperimentSet.objects.filter(
                pk__in=set([i.pk for i in choices])).order_by("urn")
            self.fields["experimentset"].queryset = choices_qs

    @classmethod
    def from_request(cls, request, instance):
        form = super().from_request(request, instance)
        form.set_experimentset_options()
        return form


class ExperimentEditForm(ExperimentForm):
    """
    A subset of `ExperimentForm` for editiing instances. Follows the same
    logic as `ExperimentForm`
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.edit_mode = True
        self.fields.pop('target_organism')
        self.fields.pop('target')
        self.fields.pop('wt_sequence')
        self.fields.pop('experimentset')