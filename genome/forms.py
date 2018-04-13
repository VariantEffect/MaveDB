from django import forms as forms
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.core.exceptions import ValidationError

from nested_formset import (
    BaseNestedFormset, BaseNestedModelForm, nestedformset_factory
)

from .validators import (
    validate_interval_start_lteq_end,
    validate_wildtype_sequence,
    validate_gene_name,
    validate_at_least_one_annotation,
    validate_unique_intervals,
    validate_annotation_has_unique_reference_genome,
    validate_one_primary_annotation
)

from .models import (
    TargetGene,
    Annotation,
    ReferenceGenome,
    Interval,
    WildTypeSequence,
)

BOOTSTRAP_CLASS = 'form-control'


# TargetGene
# ------------------------------------------------------------------------ #
class TargetGeneForm(forms.ModelForm):
    """
    Form for validating the fields required to instantiate the following:

        - :class:`WildTypeSequence`
        - :class:`TargetGene`

    The wildtype sequence will be created from `wt_sequence` and then
    associated with the :class:`TargetGene` instance that will be created
    upon saving.
    """
    class Meta:
        model = TargetGene
        fields = ('name', )

    wt_sequence = forms.CharField(
        label='Target wild-type sequence',
        required=True,
        widget=forms.Textarea(attrs={'class': BOOTSTRAP_CLASS}),
        validators=[validate_wildtype_sequence],
        error_messages={
            'required': 'You must supply a wild-type sequence for your target.'
        },
    )

    def __init__(self, *args, **kwargs):
        self.field_order = ('name', 'wt_sequence')
        super().__init__(*args, **kwargs)

        self.fields['name'].label = 'Target name'
        self.fields['name'].validators = [validate_gene_name]
        self.fields['name'].widget = forms.Textarea(
            attrs={'class': BOOTSTRAP_CLASS})
        self.fields['name'].error_messages.update(
            {'required': 'You must supply a name for your target.'})

    def save(self, commit=True):
        if commit:
            self.wt_sequence.save()
            self.instance.wt_sequence = self.wt_sequence
        instance = super().save(commit=commit)
        return instance

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            wt_sequence = cleaned_data['wt_sequence']
            self.wt_sequence = WildTypeSequence(sequence=wt_sequence)
        return cleaned_data


# Annotation
# ------------------------------------------------------------------------ #
class AnnotationForm(BaseNestedModelForm):
    """
    The annotation form

    Parameters
    ----------
    annotations : `tuple`
        A tuple of annotations to validate the instance this form will create
        against. Useful for validating all annotations specify unique
        references.

    intervals : `tuple`
        A tuple of valid intervals to associate with the annotation.
    """
    class Meta:
        model = Annotation
        fields = ('is_primary', 'genome',)

    def __init__(self, *args, **kwargs):
        self.field_order = ('is_primary', 'genome',)
        super().__init__(*args, **kwargs)

        genome_field = self.fields['genome']
        genome_field.widget.attrs.update({"class": BOOTSTRAP_CLASS})
        genome_field.requried = True
        genome_field.queryset = ReferenceGenome.objects.all()

        is_primary_field = self.fields['is_primary']
        is_primary_field.widget.attrs.update({"class": BOOTSTRAP_CLASS})

    def dummy_instance(self):
        if self.errors:
            return None
        return Annotation(
            genome=self.cleaned_data.get('genome'),
            is_primary=self.cleaned_data.get('is_primary'),
        )

    def save(self, commit=True):
        genome = self.cleaned_data['genome']
        instance = super().save(commit=commit)
        instance.set_genome(genome)
        instance.save()
        return instance


class AnnotationFormSet(BaseNestedFormset):
    """
    Formset for handling the case where you have parent-child-grandchild
    relationship which needs to be repeated multiple times.

    Example:
        A target has multiple annotations and an annotation has multiple
        intervals.
    """
    def has_errors(self):
        if isinstance(self.errors, list):
            return any(len(dict_) for dict_ in self.errors)
        else:
            return bool(self.errors)

    def clean(self):
        if not self.has_errors():
            annotations = [form.dummy_instance() for form in self.forms]
            validate_at_least_one_annotation(annotations)
            validate_annotation_has_unique_reference_genome(annotations)
            validate_one_primary_annotation(annotations)


# Interval
# ------------------------------------------------------------------------ #
class IntervalForm(forms.ModelForm):
    """
    Form for validating interval input and instantiating a valid instance.
    """
    class Meta:
        model = Interval
        fields = ('start', 'end', 'chromosome', 'strand')

    def __init__(self, *args, **kwargs):
        self.field_order = ('start', 'end', 'chromosome', 'strand')
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.required = True
            field.widget.attrs.update({'class': BOOTSTRAP_CLASS})

    def dummy_instance(self):
        if self.errors:
            return None
        return Interval(
            start=self.cleaned_data.get('start'),
            end=self.cleaned_data.get('end'),
            chromosome=self.cleaned_data.get('chromosome'),
            strand=self.cleaned_data.get('strand'),
        )

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        else:
            start = cleaned_data['start']
            end = cleaned_data['end']
            validate_interval_start_lteq_end(start, end)
            return cleaned_data

    def save(self, commit=True):
        annotation = self.cleaned_data['annotation']
        instance = super().save(commit=commit)
        instance.set_annotation(annotation)
        instance.save()
        return instance


class IntervalFormSet(BaseInlineFormSet):
    """
    Formset which will validate multiple intervals against each other
    to ensure uniqueness.
    """
    def has_errors(self):
        if isinstance(self.errors, list):
            return any(len(dict_) for dict_ in self.errors)
        else:
            return bool(self.errors)

    def clean(self):
        if not self.has_errors():
            intervals = [form.dummy_instance() for form in self.forms]
            if not intervals:
                raise ValidationError(
                    "You must specify at least one interval for each "
                    "reference annotation."
                )
            validate_unique_intervals(intervals)


NestedAnnotationFormSet = nestedformset_factory(
    TargetGene,
    Annotation,
    form=AnnotationForm,
    formset=AnnotationFormSet,
    fields=('genome', 'is_primary',),
    extra=0, min_num=1, validate_min=True,
    nested_formset=inlineformset_factory(
        Annotation,
        Interval,
        form=IntervalForm,
        formset=IntervalFormSet,
        extra=0, min_num=1, validate_min=True,
    )
)
