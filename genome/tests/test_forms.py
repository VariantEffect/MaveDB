from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError

from accounts.factories import UserFactory

from dataset.constants import nan_col_values
from metadata.factories import (
    EnsemblIdentifierFactory, RefseqIdentifierFactory
)

from ..factories import (
    TargetGeneFactory,
    AnnotationFactory,
    ReferenceGenomeFactory,
    IntervalFactory,
    WildTypeSequenceFactory
)
from ..forms import (
    IntervalForm,
    AnnotationForm,
    TargetGeneForm
)