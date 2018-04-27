from django import forms
from django.core.exceptions import ValidationError

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
                attrs={"class": "shit select2 select2-token-select"}
            ),
        )
        # Re-order the fields manually. Setting field order before `super`
        # won't work because 'identifier' is created and entered into the
        # fields OrderedDict afterwards.
        offset_field = self.fields.pop("offset")
        identifier_field = self.fields.pop("identifier")
        self.fields["identifier"] = identifier_field
        self.fields["offset"] = offset_field

        if 'instance' in kwargs:
            self.fields['identifier'].initial = kwargs['instance'].identifier
            self.fields['offset'].initial = kwargs['instance'].offset

    def clean_identifier(self):
        identifier = self.cleaned_data.get("identifier", None)
        if identifier and not is_null(identifier.identifier):
            value = identifier.identifier
            if self.id_class == RefseqIdentifier:
                validate_refseq_identifier(value)
            elif self.id_class == UniprotIdentifier:
                validate_uniprot_identifier(value)
            elif self.id_class == EnsemblIdentifier:
                validate_ensembl_identifier(value)
            return identifier
        else:
            return None

    def save(self, target=None, commit=True):
        if self.errors:
            return super().save(commit=commit)
        # Don't attempt a save if identifier is None. This will cause
        # a database IntegrityError so return None instead.
        identifier = self.cleaned_data.get('identifier', None)
        if commit and identifier is not None:
            if target is not None:
                self.instance.target = target
            if self.instance.pk is None and target is None:
                raise ValueError(
                    "Cannot save an AnnotationOffset model without a "
                    "valid target instance."
                )
            if self.instance.pk is None and identifier is None:
                raise ValueError(
                    "Cannot save an AnnotationOffset model without a "
                    "valid identifier instance."
                )
            self.instance.identifier = identifier
            return super().save(commit=commit)
        elif commit and identifier is None:
            return None
        else:
            if identifier is not None:
                return super().save(commit=commit)
            else:
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
