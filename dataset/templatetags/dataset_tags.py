import json
import logging
from django import template
from django.utils.safestring import mark_safe

from dataset import models
from accounts.permissions import user_is_anonymous

register = template.Library()
logger = logging.getLogger("django")


def get_ref_map(gene):
    reference_map = gene.get_primary_reference_map()
    if not reference_map:
        reference_map = gene.get_reference_maps().first()
    if not reference_map:
        logger.warning("Could not find a reference map for {}/{}".format(
            gene.get_name(), gene.get_target().id
        ))
        return None
    return reference_map


@register.assignment_tag
def group_targets(scoresets):
    unique_targets = {}
    hash_to_target = {}
    for scoreset in scoresets:
        hash_to_target[scoreset.get_target().hash()] = scoreset.get_target()
        if scoreset.get_target().hash() in unique_targets:
            unique_targets[scoreset.get_target().hash()].append(scoreset)
        else:
            unique_targets[scoreset.get_target().hash()] = [scoreset, ]
    return [
        (
            hash_to_target[hash_],
            sorted(unique_targets[hash_], key=lambda s: s.urn)
        )
        for hash_ in unique_targets.keys()
    ]
    

@register.simple_tag
def display_targets(instance, user, javascript=False,
                    categories=False, organisms=False):
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
                targets = [instance.get_target(), ]
        else:
            logger.warning("NoneType gene passed by {}.".format(instance.urn))

    if not targets:
        if javascript:
            return mark_safe(json.dumps(['-']))
        return '-'
    
    t_categories = [t.category for t in targets]
    t_names = [t.get_name() for t in targets]
    t_organisms = [
        get_ref_map(t).format_reference_genome_organism_html()
        if get_ref_map(t) else 'No associated organism'
        for t in targets
    ]
    if javascript:
        if categories:
            return mark_safe(json.dumps(t_categories))
        elif organisms:
            return mark_safe(json.dumps(t_organisms))
        else:
            return mark_safe(json.dumps(t_names))
    if categories:
        return mark_safe(', '.join(t_categories))
    elif organisms:
        return mark_safe(', '.join(t_organisms))
    else:
        return mark_safe(', '.join(t_names))


@register.assignment_tag
def organise_by_target(scoresets):
    by_target = {s.get_target().name: [] for s in scoresets}
    for scoreset in scoresets:
        name = scoreset.get_target().name
        by_target[name].append(scoreset)
    return by_target


@register.assignment_tag
def visible_children(instance, user=None):
    return filter_visible(instance.children, user=user)


@register.assignment_tag
def current_versions(instances, user=None):
    if instances is None:
        return []
    current = {}
    for i in instances:
        new = i.get_current_version(user)
        current[new.urn] = new
    return sorted(current.values(), key=lambda ss: ss.urn)


@register.assignment_tag
def filter_visible(instances, user=None):
    if instances is None:
        return []

    if (not instances) or (not instances.count()):
        return instances

    if user is None or user_is_anonymous(user):
        return instances.exclude(private=True)

    klass = instances.first().__class__.__name__
    groups = user.groups.filter(name__iregex=r'{}:\d+-\w+'.format(klass))
    pks = set(int(g.name.split(':')[-1].split('-')[0]) for g in groups)
    public = instances.exclude(private=True)
    private_visiable = instances.exclude(private=False).filter(pk__in=set(pks))
    return (public | private_visiable).distinct().order_by('urn')


@register.assignment_tag
def parent_references(instance):
    parent_refs = set()
    for pmid in instance.parent.pubmed_ids.all():
        if pmid not in instance.pubmed_ids.all():
            parent_refs.add(pmid)
    return list(parent_refs)


@register.simple_tag
def format_urn_name_for_user(instance, user):
    if instance.private and user in instance.contributors:
        return '{} [Private]'.format(instance.urn)
    return instance.urn
