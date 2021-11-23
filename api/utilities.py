from dataset.models import Experiment, ScoreSet
from dataset.serializers import (
    ExperimentSerializer,
    ScoreSetSerializer,
)
from variant.models import Variant
from variant.serializers import VariantSerializer

def format_variant_get_response(variant_urn, offset, limit):
    '''
    This function assumes a check has already been done on the existence of a
    Variant object with the urn of variant_urn exists in the database with a
    corresponding ScoreSet and, in turn, Experiment object.

    Format the variant response data so it looks like:
    {
        'experiment': {
            ...RELEVANT_EXPERIMENT_KEYS
            'scoreset': {
                ...RELEVANT_SCORESET_KEYS
                'variants': [
                    {
                        ...RELEVANT_VARIANT_KEYS
                    },
                    ...
                ]
            }
        }
    }
    '''
    # Fetch the original variant object
    variant = Variant.objects.get(urn=variant_urn)
    variant_dict = VariantSerializer(variant).data

    # If only asking for one variant, only provide the exact match.
    if limit == 1:
        all_variants = [variant]
    elif limit < 0:
        variant_urn_prefix = variant_urn.split('#')[0]
        all_variants = Variant.objects.order_by('urn') \
            .filter(urn__startswith=variant_urn_prefix)
    # Else, get the rest of the variants, which are the ones with a matching
    # urn prefix.
    else:
        variant_urn_prefix = variant_urn.split('#')[0]
        all_variants = Variant.objects.order_by('urn') \
            .filter(urn__startswith=variant_urn_prefix)[offset:limit]
    variants_response_list = []
    for v in all_variants:
        v_dict = VariantSerializer(v).data
        v_response_keys = ['urn', 'hgvs_pro', 'data']
        v_response_dict = {}
        for key in v_response_keys:
            if key in v_dict:
                v_response_dict[key] = v_dict[key]
        variants_response_list.append(v_response_dict)

    # Format the scoreset to include the variants list
    scoreset_urn = variant.scoreset.urn
    scoreset = ScoreSet.objects.get(urn=scoreset_urn)
    scoreset_dict = ScoreSetSerializer(scoreset).data
    scoreset_response_dict = {}
    scoreset_response_keys = ['urn', 'pmid', 'keywords', 'score_ranges', 'license', 'variants']
    for key in scoreset_response_keys:
        if key in scoreset_dict:
            scoreset_response_dict[key] = scoreset_dict[key]
        elif key == 'variants':
            scoreset_response_dict[key] = variants_response_list

    # Finally, format the experiment to include the scoreset
    experiment_urn = variant.scoreset.experiment
    experiment = Experiment.objects.get(urn=experiment_urn)
    experiment_dict = ExperimentSerializer(experiment).data
    experiment_response_dict = {}
    experiment_response_keys = ['urn', 'pmid', 'keywords', 'target', 'scoreset']
    for key in experiment_response_keys:
        if key in experiment_dict:
            experiment_response_dict[key] = experiment_dict[key]
        elif key == 'target':
            experiment_response_dict[key] = scoreset_dict[key]
        elif key == 'scoreset':
            experiment_response_dict[key] = scoreset_response_dict

    response_data = {
        'experiment': experiment_response_dict
    }
    return response_data
