from django import forms

from core.utilities import is_null

from .fields import FlexibleModelChoiceField
from .validators import (
    validate_uniprot_identifier,
    validate_refseq_identifier,
    validate_ensembl_identifier,
)
from .models import (
    UniprotIdentifier, EnsemblIdentifier, RefseqIdentifier,
    UniprotOffset, RefseqOffset, EnsemblOffset
)


class BaseIdentifierWithOffsetForm(forms.ModelForm):
    id_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['offset'].required = False
        self.fields['identifier'] = FlexibleModelChoiceField(
            klass=self.id_class,
            to_field_name="identifier",
            required=False,
            queryset=self.id_class.objects.all(),
            widget=forms.Select(
                attrs={"class": "select2 select2-token-select"},
            ),
        )
        # Re-order the fields manually. Setting field order before `super`
        # won't work because 'identifier' is created and entered into the
        # fields OrderedDict afterwards.
        offset_field = self.fields.pop("offset")
        identifier_field = self.fields.pop("identifier")
        self.fields["identifier"] = identifier_field
        self.fields["offset"] = offset_field
        self.fields["offset"].label = "Wild-type offset"

        instance = kwargs.get('instance', None)
        if hasattr(instance, 'pk') and instance.pk is not None:
            self.fields['identifier'].initial = instance.identifier
            self.fields['offset'].initial = instance.offset

    def clean_identifier(self):
        identifier = self.cleaned_data.get("identifier", None)
        if identifier and str(identifier.identifier).strip() == "":
            return None
        if identifier:
            value = identifier.identifier
            # Nothing was submitted. Should still be a valid form since
            # no input was supplied.
            if value is None:
                return value
            if self.id_class == RefseqIdentifier:
                validate_refseq_identifier(value)
            elif self.id_class == UniprotIdentifier:
                validate_uniprot_identifier(value)
            elif self.id_class == EnsemblIdentifier:
                validate_ensembl_identifier(value)
            return identifier
        else:
            return None

    def is_blank(self):
        identifier = self.cleaned_data.get('identifier', None)
        return identifier is None

    def save(self, target=None, commit=True):
        if self.errors:
            return super().save(commit=commit)
        # Don't attempt a save if identifier is None. This will cause
        # a database IntegrityError so return None instead.
        identifier = self.cleaned_data.get('identifier', None)
        if commit and not self.is_blank():
            if target is not None:
                self.instance.target = target
            if self.instance.pk is None and target is None:
                raise ValueError(
                    "Cannot save an AnnotationOffset model without a "
                    "valid target instance."
                )
            identifier.save()
            self.instance.identifier = identifier
            return super().save(commit=commit)
        elif commit and self.is_blank():
            # User has chosen to delete the annoation by supplying a blank
            if self.instance.pk is not None:
                self.instance.delete()
            return None
        else:
            if not self.is_blank():
                return super().save(commit=commit)
            return None


class UniprotOffsetForm(BaseIdentifierWithOffsetForm):
    id_class = UniprotIdentifier

    class Meta:
        model = UniprotOffset
        fields = ('offset',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identifier'].label = "UniProt identifier"


class RefseqOffsetForm(BaseIdentifierWithOffsetForm):
    id_class = RefseqIdentifier

    class Meta:
        model = RefseqOffset
        fields = ('offset',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identifier'].label = "RefSeq identifier"


class EnsemblOffsetForm(BaseIdentifierWithOffsetForm):
    id_class = EnsemblIdentifier

    class Meta:
        model = EnsemblOffset
        fields = ('offset',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identifier'].label = "Ensembl identifier"
