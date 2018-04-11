from django import forms as forms
from django.db import transaction


from metadata.validators import (
    validate_ensembl_identifier,
    validate_ensembl_list,
    validate_refseq_identifier,
    validate_refseq_list
)


from .validators import (
    validate_interval_start_lteq_end,
    validate_wildtype_sequence,
    validate_annotation_is_not_a_second_primary,
    validate_gene_name,
    validate_genome_short_name,
    validate_interval_is_not_a_duplicate,
    validate_species_name,
    validate_strand,
    validate_target_has_one_primary_annotation,
    validate_annotation_has_unique_reference_genome,
    validate_reference_genome_has_one_external_identifier,
)
from .models import (
    TargetGene,
    Annotation,
    ReferenceGenome,
    Interval,
    WildTypeSequence,
)


class TargetGeneForm(forms.Form):
    pass


class IntervalForm(forms.ModelForm):
    pass


class ReferenceGenomeForm(forms.ModelForm):
    pass
