from enum import Enum

from django import forms as forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import ugettext

from core.mixins import NestedEnumMixin
from ..forms.base import DatasetModelForm
from ..models.base import DatasetModel
from ..models.experiment import Experiment
from ..models.experimentset import ExperimentSet


class ErrorMessages(NestedEnumMixin, Enum):
    """ScoreSet field specific error messages."""

    class Field(Enum):
        invalid_choice = ugettext(
            forms.ModelChoiceField.default_error_messages["invalid_choice"]
        )

    class ExperimentSet(Enum):
        public_experiment = ugettext(
            "Changing the parent Experiment Set of "
            "a public Experiment is not supported."
        )


class ExperimentForm(DatasetModelForm):
    """
    TODO: Docstring
    """

    class Meta(DatasetModel.Meta):
        model = Experiment
        fields = DatasetModelForm.Meta.fields + ("experimentset",)

    def __init__(self, *args, **kwargs):
        self.field_order = ("experimentset",) + self.FIELD_ORDER
        # If an experimentset is passed in we can used to it to seed initial
        # replaces and m2m field selections.
        self.experimentset = None
        if "experimentset" in kwargs:
            self.experimentset = kwargs.pop("experimentset")
        super().__init__(*args, **kwargs)

        if self.instance.pk is None:
            self.fields["experimentset"] = forms.ModelChoiceField(
                queryset=None,
                required=False,
                widget=forms.Select(attrs={"class": "form-control"}),
            )
            self.fields["experimentset"].label = "Experiment set"
        else:
            self.fields.pop("experimentset", None)

        self.fields["abstract_text"].help_text = (
            "A plain text or markdown abstract relating to the study "
            "conducted. Click the preview button "
            "to view a rendered preview of what other users will "
            "see once you publish your submission."
        )
        self.fields["method_text"].help_text = (
            "A plain text or markdown method describing experimental "
            "design and data collection. Click the preview button "
            "to view a rendered preview of what other users will "
            "see once you publish your submission."
        )

        for field in ("experimentset",):
            if field in self.fields:
                self.fields[field].widget.attrs.update(**{"class": "select2"})

        self.set_experimentset_options()

    # -------------- Setup ------------------------------------------------ #
    def set_experimentset_options(self):
        if "experimentset" in self.fields:
            admin_instances = self.user.profile.administrator_experimentsets()
            editor_instances = self.user.profile.editor_experimentsets()
            choices = set(
                [i.pk for i in admin_instances.union(editor_instances)]
            )

            # Prevent attaching a regular experiment to a meta-analysis
            # experimentset
            choices_qs = (
                ExperimentSet.non_meta_analyses()
                .filter(pk__in=choices)
                .order_by("urn")
            )
            self.fields["experimentset"].queryset = choices_qs
            self.fields["experimentset"].widget.choices = [
                ("", self.fields["experimentset"].empty_label)
            ] + [(e.pk, "{}".format(e.urn)) for e in choices_qs.all()]

            if self.experimentset is not None:
                choices_qs = ExperimentSet.objects.filter(
                    pk__in=[self.experimentset.pk]
                ).order_by("urn")
                self.fields["experimentset"].queryset = choices_qs
                self.fields["experimentset"].widget.choices = (
                    (
                        self.experimentset.pk,
                        "{}".format(self.experimentset.urn),
                    ),
                )
                self.fields["experimentset"].initial = self.experimentset

    # -------------- Data cleaning ---------------------------------------- #
    def clean_experimentset(self):
        experimentset = self.cleaned_data.get("experimentset", None)
        existing_experimentset = self.instance.parent
        if existing_experimentset is not None and self.instance.pk is not None:
            if experimentset is not None:
                if (
                    existing_experimentset.urn != experimentset
                    and not self.instance.private
                ):
                    raise ValidationError(
                        "Changing the parent Experiment Set of "
                        "a public Experiment is not supported."
                    )
        return experimentset

    # -------------- Saving ------------------------------------------------ #
    @transaction.atomic
    def save(self, commit=True):
        instance = super().save(commit=commit)

        if not self.data.get("experimentset"):
            parent = instance.experimentset
            parent.set_created_by(self.user, propagate=False)
            parent.set_modified_by(self.user, propagate=False)

            if commit:
                parent.save()

        return instance


class ExperimentEditForm(ExperimentForm):
    """
    A subset of `ExperimentForm` for editing instances. Follows the same
    logic as `ExperimentForm`
    """

    def __init__(self, *args, **kwargs):
        if "instance" not in kwargs:
            raise ValueError(
                "An existing instance is required to instantiate "
                "an edit form."
            )
        super().__init__(*args, **kwargs)
        self.edit_mode = True

        # Might be popped already
        self.fields.pop("experimentset", None)
