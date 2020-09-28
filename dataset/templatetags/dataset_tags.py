import json
import logging

from django import template
from django.utils.safestring import mark_safe
from django.db.models import Q

from dataset import models
from dataset.models.base import DatasetModel
from dataset.models.experiment import Experiment
from dataset.models.experimentset import ExperimentSet
from dataset.models.scoreset import ScoreSet
from metadata.models import PubmedIdentifier
from accounts.permissions import user_is_anonymous

register = template.Library()
logger = logging.getLogger("django")


def get_ref_map(gene):
    """
    Safe get the first reference map for a gene. Prioritizes primary maps.

    Parameters
    ----------
    gene : `genome.models.Gene`

    Returns
    -------
    `genome.models.ReferenceMap`
    """
    reference_map = gene.get_primary_reference_map()
    if not reference_map:
        reference_map = gene.get_reference_maps().first()
    if not reference_map:
        logger.warning(
            "Could not find a reference map for {}/{}".format(
                gene.get_name(), gene.get_target().id
            )
        )
        return None
    return reference_map


@register.simple_tag
def is_score_set(instance):
    return isinstance(instance, ScoreSet)


@register.simple_tag
def is_experiment(instance):
    return isinstance(instance, Experiment)


@register.simple_tag
def is_experiment_set(instance):
    return isinstance(instance, ExperimentSet)


@register.simple_tag
def is_meta_analysis(instance):
    if isinstance(instance, DatasetModel):
        return instance.is_meta_analysis
    return False


@register.simple_tag
def is_meta_analysed(instance):
    if isinstance(instance, ScoreSet):
        return instance.meta_analysed_by.count() > 0
    return False


@register.assignment_tag
def group_targets(scoresets):
    """
    Group targets and scoresets so the front end can render unique  targets
    along with associated score sets. Grouping is based on a hash function
    implemented on `genome.models.Target`.

    Parameters
    ----------
    scoresets : Iterable[ScoreSet]
        An iterable of scoresets to group targets from.

    Returns
    -------
    tuple[`genome.models.Target`, list[`dataset.models.scoreset.ScoreSet`]]
    """
    unique_targets = {}
    hash_to_target = {}
    for scoreset in scoresets:
        hash_to_target[scoreset.get_target().hash()] = scoreset.get_target()
        if scoreset.get_target().hash() in unique_targets:
            unique_targets[scoreset.get_target().hash()].append(scoreset)
        else:
            unique_targets[scoreset.get_target().hash()] = [scoreset]
    return [
        (
            hash_to_target[hash_],
            sorted(unique_targets[hash_], key=lambda s: s.urn),
        )
        for hash_ in unique_targets.keys()
    ]


@register.simple_tag
def display_targets(
    instance,
    user,
    javascript=False,
    categories=False,
    organisms=False,
    all_fields=False,
):
    """
    Used by the search table. For a given experiment or score set, will collect
    list of target attributes to display in the table columns. For example,
    target categories, organisms and names.

    Parameters
    ----------
    instance : dataset.models.experiment.Experiment | dataset.models.scoreset.ScoreSet
    user : User
    javascript : bool, optional.
        Return a safe JSON string dump.
    categories : bool, optional.
        Return unique target categories only.
    organisms : bool, optional.
        Return unique target organisms only.
    all_fields : bool, optional.
        Return unique target names, organisms and categories.

    Returns
    -------
    tuple
    """
    targets = []
    if isinstance(instance, models.experiment.Experiment):
        children = visible_children(instance, user)
        targets = [t[0] for t in group_targets(children)]
    elif isinstance(instance, models.scoreset.ScoreSet):
        # This shouldn't happen but just in case a scoreset ends up
        # without a target, then check.
        if instance.get_target():
            ref_map = get_ref_map(instance.get_target())
            if ref_map is not None:
                # Only proceed if a ref map is present.
                targets = [instance.get_target()]
        else:
            logger.warning("NoneType gene passed by {}.".format(instance.urn))

    if not targets:
        if javascript:
            return mark_safe(json.dumps(["-"]))
        if all_fields:
            return "-", "-", "-"
        return "-"

    t_categories = [t.category for t in targets]
    t_names = [t.get_name() for t in targets]
    t_organisms = [
        get_ref_map(t).format_reference_genome_organism_html()
        if get_ref_map(t)
        else "No associated organism"
        for t in targets
    ]
    if javascript:
        if all_fields:
            return (
                mark_safe(json.dumps(t_names)),
                mark_safe(json.dumps(t_categories)),
                mark_safe(json.dumps(t_organisms)),
            )
        elif categories:
            return mark_safe(json.dumps(t_categories))
        elif organisms:
            return mark_safe(json.dumps(t_organisms))
        else:
            return mark_safe(json.dumps(t_names))

    if all_fields:
        return (
            mark_safe(", ".join(t_names)),
            mark_safe(", ".join(t_categories)),
            mark_safe(", ".join(t_organisms)),
        )
    if categories:
        return mark_safe(", ".join(t_categories))
    elif organisms:
        return mark_safe(", ".join(t_organisms))
    else:
        return mark_safe(", ".join(t_names))


@register.assignment_tag
def organise_by_target(scoresets):
    """
    Groups score sets based on their target name.

    Parameters
    ----------
    scoresets : Iterable[ScoreSet]

    Returns
    -------
    Dict[str, list[ScoreSet]]
    """
    by_target = {s.get_target().name: [] for s in scoresets}
    for scoreset in scoresets:
        name = scoreset.get_target().name
        by_target[name].append(scoreset)
    return by_target


@register.assignment_tag
def visible_children(instance, user=None):
    """
    Returns the current versions of an experiment or experiment set's children.
    Returns the latest instances viewable by the user (public,
    or private contributor).

    Parameters
    ----------
    instance : ExperimentSet | Experiment
    user : User

    Returns
    -------
    Iterable[ScoreSet]
    """
    if is_experiment_set(instance):
        return Experiment.non_meta_analyses().intersection(
            filter_visible(instance.children, user=user)
        )
    return filter_visible(instance.children, user=user)


@register.assignment_tag
def current_versions(instances, user=None):
    """
    Returns the current versions of an iterable of score sets. Returns the
    latest instances viewable by the user (public,
    or private contributor).

    Parameters
    ----------
    instances : Iterable[ScoreSet]
    user : User

    Returns
    -------
    Iterable[ScoreSet]
    """
    if instances is None:
        return []
    current = {}
    for i in instances:
        new = i.get_current_version(user)
        current[new.urn] = new
    return sorted(current.values(), key=lambda ss: ss.urn)


@register.assignment_tag
def filter_visible(instances, user=None):
    """
    Filter the visible instances for user. This means including instances which
    are not private, and private instances which the user is a contributor for.

    Parameters
    ----------
    instances : django.db.models.QuerySet
        QuerySet of instances to filter.
    user : accounts.models.User
        User instance.

    Returns
    -------
    QuerySet<ExperimentSet | Experiment | ScoreSet>
    """
    if instances is None:
        return []

    if (not instances) or (not instances.count()):
        return instances

    if user is None or user_is_anonymous(user):
        return instances.exclude(private=True)

    # def fetch_primary_keys(queryset):
    #     perm_groups = user.groups.filter(
    #         name__iregex=r"{}:\d+-\w+".format(
    #             queryset.model.__class__.__name__
    #         )
    #     )
    #     return set(
    #         int(g.name.split(":")[-1].split("-")[0]) for g in perm_groups
    #     )

    if instances.model is ExperimentSet:
        private_visible = user.profile.contributor_experimentsets(
            instances.filter(private=True)
        )
        visible_meta = (
            ExperimentSet.meta_analyses()
            .intersection(instances)
            .filter(private=True)
            .filter(
                experiments__scoresets__in=(
                    ScoreSet.meta_analyses().intersection(
                        user.profile.contributor_scoresets()
                    )
                )
            )
        )
    elif instances.model is Experiment:
        private_visible = user.profile.contributor_experiments(
            instances.filter(private=True)
        )
        visible_meta = (
            Experiment.meta_analyses()
            .intersection(instances)
            .filter(private=True)
            .filter(
                scoresets__in=(
                    user.profile.contributor_scoresets().intersection(
                        ScoreSet.meta_analyses()
                    )
                )
            )
        )
    elif instances.model is ScoreSet:
        private_visible = user.profile.contributor_scoresets(
            instances.filter(private=True)
        )
        visible_meta = instances.none()
    else:
        raise TypeError(
            f"Cannot filter non dataset class {instances.model.__name__}"
        )

    public = instances.exclude(private=True)
    return (
        (
            public.distinct()
            | private_visible.distinct()
            | visible_meta.distinct()
        )
        .distinct()
        .order_by("urn")
        .all()
    )


@register.assignment_tag
def lex_sorted_references(instance):
    """
    Sort the references of an instance based on lex order using the
    `reference_html` field on `PubmedIdentifier`

    Includes ancestor references.

    Parameters
    ----------
    instance : ExperimentSet | Experiment | Experiment
        Instance to sort reference for.

    Returns
    -------
    QuerySet<PubmedIdentifier>
    """
    if isinstance(instance, models.experimentset.ExperimentSet):
        references = PubmedIdentifier.objects.filter(
            associated_experimentsets__in=[instance]
        )
    elif isinstance(
        instance, (models.experiment.Experiment, models.scoreset.ScoreSet)
    ):
        references = (
            instance.pubmed_ids.all().distinct()
            | unique_parent_references(instance)
        )
    else:
        references = PubmedIdentifier.objects.none()

    return references.distinct().order_by("reference_html")


@register.assignment_tag
def unique_parent_references(instance):
    """
    Returns the parent references of a dataset model sorted by the
    `reference_html` field on `PubmedIdentifier` that are not in the
    instance's pubmed references.

    Parameters
    ----------
    instance : ExperimentSet | Experiment | Experiment
        Instance to sort reference for.

    Returns
    -------
    QuerySet<PubmedIdentifier>
    """
    if isinstance(instance, models.experiment.Experiment):
        references = PubmedIdentifier.objects.filter(
            Q(associated_experimentsets__in=[instance.parent])
        ).exclude(Q(associated_experiments__in=[instance]))
    elif isinstance(instance, models.scoreset.ScoreSet):
        references = PubmedIdentifier.objects.filter(
            Q(associated_experimentsets__in=[instance.parent.parent])
            | Q(associated_experiments__in=[instance.parent])
            | Q(associated_experiments__in=[instance.parent])
        ).exclude(Q(associated_scoresets__in=[instance]))
    else:
        references = PubmedIdentifier.objects.none()

    return references.distinct().order_by("reference_html")


@register.simple_tag
def format_urn_name_for_user(instance, user):
    """
    Adds [Private] to a URN if the model is private and user is a contributor.

    Parameters
    ----------
    instance : ExperimentSet | Experiment | Experiment | Variant
        Instance which has the `urn` field.

    user : User
        User model.

    Returns
    -------
    str
    """
    if instance.private and user in instance.contributors:
        return "{} [Private]".format(instance.urn)
    return instance.urn
