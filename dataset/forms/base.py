from django import forms as forms
from django.db import transaction

from accounts.permissions import assign_superusers_as_admin
from metadata.fields import FlexibleModelMultipleChoiceField

from metadata.models import (
    Keyword, SraIdentifier, DoiIdentifier, PubmedIdentifier
)

from metadata.validators import (
    validate_keyword_list, validate_sra_list,
    validate_doi_list, validate_pubmed_list
)

from ..models.base import DatasetModel


class DatasetModelForm(forms.ModelForm):
    """
    Base form handling the fields present in :class:`.models.DatasetModel`.

    Handles validation of :class:`metadata.models.ExternalIdentifiers`,
    including the creation of new identifiers when supplied identifiers do not
    match any in the database.

    Parameters
    ----------
    user : :class:`User`
        The user instance that this form is served to.
    """
    FIELD_ORDER = (
        'title',
        'short_description',
        'abstract_text',
        'method_text',
        'keywords',
        'doi_ids',
        'sra_ids',
        'pubmed_ids',
    )

    class Meta:
        model = DatasetModel
        fields = (
            'abstract_text',
            'method_text',
            "short_description",
            "title",
            'keywords',
            'doi_ids',
            'pubmed_ids',
            'sra_ids',
        )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        self.fields['short_description'].widget = forms.Textarea(
            attrs={'cols': "40", 'rows': "4"}
        )
        self.fields['short_description'].help_text = \
            "A short plain text description limited to 500 characters."
        self.fields['title'].widget = forms.TextInput()
        self.fields['abstract_text'].widget = forms.Textarea()
        self.fields['method_text'].widget = forms.Textarea()
        self.fields['keywords'] = FlexibleModelMultipleChoiceField(
            klass=Keyword, to_field_name='text',
            label='Keywords', required=False,
            queryset=Keyword.objects.all(), widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"}
            )
        )
        self.fields['sra_ids'] = FlexibleModelMultipleChoiceField(
            klass=SraIdentifier, to_field_name='identifier',
            label='SRA Identifiers', required=False,
            queryset=SraIdentifier.objects.all(),
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"}
            )
        )
        self.fields['doi_ids'] = FlexibleModelMultipleChoiceField(
            klass=DoiIdentifier, to_field_name='identifier',
            label='DOI Identifiers', required=False,
            queryset=DoiIdentifier.objects.all(),
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"}
            )
        )
        self.fields['pubmed_ids'] = FlexibleModelMultipleChoiceField(
            klass=PubmedIdentifier, to_field_name='identifier',
            label='PubMed Identifiers', required=False,
            queryset=PubmedIdentifier.objects.all(),
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"}
            )
        )
        self.fields['keywords'].validators.append(validate_keyword_list)
        self.fields['sra_ids'].validators.append(validate_sra_list)
        self.fields['doi_ids'].validators.append(validate_doi_list)
        self.fields['pubmed_ids'].validators.append(validate_pubmed_list)

    def clean_keywords(self):
        return self.cleaned_data.get('keywords', [])

    def clean_sra_ids(self):
        return self.cleaned_data.get('sra_ids', [])

    def clean_doi_ids(self):
        return self.cleaned_data.get('doi_ids', [])

    def clean_pubmed_ids(self):
        return self.cleaned_data.get('pubmed_ids', [])

    def _save_m2m(self):
        # Save all instances before calling super() so that all new instances
        # are in the database before m2m relationships are created.
        for m2m_field in DatasetModel.M2M_FIELD_NAMES:
            if m2m_field in self.fields:
                for instance in self.cleaned_data.get(m2m_field, []):
                    instance.save()
                self.instance.clear_m2m(m2m_field)
        super()._save_m2m()  # super() will create new m2m relationships

    # Make this atomic since new m2m instances will need to be saved.
    @transaction.atomic
    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            instance.set_modified_by(self.user)
            if not hasattr(self, 'edit_mode') and not instance.created_by:
                instance.set_created_by(self.user)
            instance.save()
            assign_superusers_as_admin(instance)
        return instance

    def m2m_instances_for_field(self, field_name, return_new=True):
        if field_name not in self.fields:
            raise ValueError(
                '{} is not a field in this form.'.format(field_name)
            )
        entries = self.cleaned_data.get(field_name, [])
        existing_entries = [i for i in entries if i.pk is not None]
        if return_new:
            new_entries = [i for i in entries if i.pk is None]
            return existing_entries + new_entries
        return existing_entries

    @classmethod
    def from_request(cls, request, instance, prefix=None, initial=None):
        if request.method == "POST":
            form = cls(
                user=request.user, data=request.POST,
                files=request.FILES, instance=instance,
                prefix=prefix, initial=initial
            )
        else:
            form = cls(
                user=request.user, instance=instance,
                prefix=prefix, initial=initial
            )
        return form
