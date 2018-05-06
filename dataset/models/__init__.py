from django.core.exceptions import ObjectDoesNotExist

__all__ = [
    "experiment",
    'experimentset',
    'scoreset',
    'get_model_by_urn',
]


def get_model_by_urn(urn):
    from variant.models import Variant
    from .scoreset import ScoreSet
    from .experiment import Experiment
    from .experimentset import ExperimentSet
    
    for model in [ScoreSet, Experiment, ExperimentSet, Variant]:
        if model.objects.filter(urn=urn).exists():
            return model.objects.get(urn=urn)
    raise ObjectDoesNotExist("No model found with urn {}.".format(urn))