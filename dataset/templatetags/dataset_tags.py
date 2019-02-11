import json
import logging
from django import template
from django.utils.safestring import mark_safe

from dataset import models

register = template.Library()
logger = logging.getLogger("django")


@register.simple_tag
def display_targets(instance, user, javascript=False,
                    categories=False, organisms=False):
    targets = []
    if isinstance(instance, models.experiment.Experiment):
        for child in instance.children.order_by('urn'):
            logger.warning((child.urn, child.get_target()))
            if child.private and user in child.contributors():
                targets.append([
                    child.get_target().get_name(),
                    child.get_target().category,
                    child.get_target().get_primary_reference_map().
                        format_reference_genome_organism_html(),
                ])
            elif not child.private:
                targets.append([
                    child.get_target().get_name(),
                    child.get_target().category,
                    child.get_target().get_primary_reference_map().
                        format_reference_genome_organism_html(),
                ])
    elif isinstance(instance, models.scoreset.ScoreSet):
        targets.append([
            instance.get_target().get_name(),
            instance.get_target().category,
            instance.get_target().get_primary_reference_map().
                format_reference_genome_organism_html(),
        ])
    if not targets:
        if javascript:
            return mark_safe(json.dumps(['-']))
        return '-'
    if javascript:
        if categories:
            return mark_safe(json.dumps([x[1] for x in targets]))
        elif organisms:
            return mark_safe(json.dumps([x[2] for x in targets]))
        else:
            return mark_safe(json.dumps([x[0] for x in targets]))
    if categories:
       return mark_safe(', '.join([x[1] for x in targets]))
    elif organisms:
        return mark_safe(', '.join([x[2] for x in targets]))
    else:
        return mark_safe(', '.join([x[0] for x in targets]))


@register.assignment_tag
def organise_by_target(scoresets):
    by_target = {s.get_target().name: [] for s in scoresets}
    for scoreset in scoresets:
        name = scoreset.get_target().name
        by_target[name].append(scoreset)
    return by_target


@register.assignment_tag
def visible_children(instance, user):
    return list(instance.children_for_user(user).order_by('urn'))


@register.assignment_tag
def parent_references(instance):
    parent_refs = set()
    for pmid in instance.parent.pubmed_ids.all():
        if pmid not in instance.pubmed_ids.all():
            parent_refs.add(pmid)
    return list(parent_refs)


@register.simple_tag
def format_urn_name_for_user(instance, user):
    if instance.private and user in instance.contributors():
        return '{} [Private]'.format(instance.urn)
    return instance.urn