

import django.forms as forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from main.fields import ModelSelectMultipleField
from main.models import ExternalAccession, Keyword, TargetOrganism

from .models import Experiment, ExperimentSet


class ExperimentForm(forms.ModelForm):
    """
    Docstring
    """
    class Meta:
        model = Experiment
        fields = (
            'experimentset',
            'target',
            'target_organism',
            'wt_sequence',
            'sra_id',
            'doi_id',
            'keywords',
            'external_accessions',
            'abstract',
            'method_desc',
        )

    def __init__(self, *args, **kwargs):
        super(ExperimentForm, self).__init__(*args, **kwargs)
        self.fields["target"].widget = forms.TextInput(
            attrs={
                "class": "form-control",
            }
        )
        self.fields["sra_id"].widget = forms.TextInput(
            attrs={
                "class": "form-control",
            }
        )
        self.fields["doi_id"].widget = forms.TextInput(
            attrs={
                "class": "form-control",
            }
        )

        self.fields["wt_sequence"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "style": "height:250px;width:100%"
            }
        )
        self.fields["abstract"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "style": "height:250px;width:100%"
            }
        )
        self.fields["method_desc"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "style": "height:250px;width:100%"
            }
        )

        # This needs to be in `__init__` because otherwise it is created as
        # a class variable at import time.
        self.fields["keywords"] = ModelSelectMultipleField(
            klass=Keyword,
            text_key="text",
            queryset=None,
            required=False,
            widget=forms.widgets.SelectMultiple(
                attrs={
                    "class": "form-control select2 select2-token-select",
                    "style": "width:100%;height:50px;"
                }
            )
        )
        self.fields["external_accessions"] = ModelSelectMultipleField(
            klass=ExternalAccession,
            text_key="text",
            queryset=None,
            required=False,
            widget=forms.widgets.SelectMultiple(
                attrs={
                    "class": "form-control select2 select2-token-select",
                    "style": "width:100%;height:50px;"
                }
            )
        )
        self.fields["target_organism"] = ModelSelectMultipleField(
            klass=TargetOrganism,
            text_key="text",
            queryset=None,
            required=False,
            widget=forms.widgets.Select(
                attrs={
                    "class": "form-control select2 select2-token-select",
                    "style": "width:50%;height:auto;"
                }
            )
        )
        self.fields["keywords"].queryset = Keyword.objects.all()
        self.fields["external_accessions"].queryset = \
            ExternalAccession.objects.all()
        self.fields["target_organism"].queryset = TargetOrganism.objects.all()

    def save(self, commit=True):
        super(ExperimentForm, self).save(commit=commit)
        if commit:
            self.process_and_save_all()
        else:
            self.save_m2m = self.process_and_save_all
        return self.instance

    def process_and_save_all(self):
        """
        This will saved all changes made to the instance. Keywords not
        present in the form submission will be removed, new keywords will
        be created in the database and all keywords in the upload form will
        be added to the instance's keyword m2m field.
        """
        if not (self.is_bound and self.is_valid()):
            return None
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate." % (
                    self.instance._meta.object_name,
                    'created' if self.instance._state.adding else 'changed',
                )
            )

        self.instance.save()

        if "keywords" in self.fields:
            self.save_new_m2m("keywords")
            self.instance.update_keywords(
                self.all_m2m("keywords")
            )
        if "external_accessions" in self.fields:
            self.save_new_m2m("external_accessions")
            self.instance.update_external_accessions(
                self.all_m2m("external_accessions")
            )
        if "target_organism" in self.fields:
            self.save_new_m2m("target_organism")
            self.instance.update_target_organism(
                self.all_m2m("target_organism")
            )

        self.instance.save()
        return self.instance

    def save_new_m2m(self, field_name):
        """
        Save new m2m instances that were created during the clean process.
        """
        if self.is_bound and self.is_valid():
            for instance in self.new_m2m(field_name):
                instance.save()

    def new_m2m(self, field_name):
        """
        Return a list of keywords that were created during the clean process.
        """
        if field_name not in self.fields:
            raise ValueError(
                '{} is not a field in this form.'.format(field_name)
            )
        return self.fields[field_name].new_instances

    def all_m2m(self, field_name):
        """
        Return a list of all keywords found during the cleaning process
        """
        if self.is_bound and self.is_valid():
            not_new = [i for i in self.cleaned_data.get(field_name, [])]
            new = self.new_m2m(field_name)
            return new + not_new


class ExperimentEditForm(ExperimentForm):
    """
    A subset of `ExperimentForm` for editiing instances. Follows the same
    logic as `ExperimentForm`
    """
    experimentset = None
    target = None
    wt_sequence = None

    class Meta:
        model = Experiment
        fields = (
            'experimentset',  # excluded
            'target',  # excluded
            'target_organism',  # excluded
            'wt_sequence',  # excluded
            'sra_id',
            'doi_id',
            'keywords',
            'external_accessions',
            'abstract',
            'method_desc',
        )

    def __init__(self, *args, **kwargs):
        super(ExperimentEditForm, self).__init__(*args, **kwargs)
        self.fields.pop('target_organism')
        self.fields.pop('target')
        self.fields.pop('wt_sequence')
        self.fields.pop('experimentset')
