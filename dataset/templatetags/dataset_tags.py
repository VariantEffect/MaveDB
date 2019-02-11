import json
import logging
from django import template
from django.utils.safestring import mark_safe

from dataset import models

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


@register.simple_tag
def display_targets(instance, user, javascript=False,
                    categories=False, organisms=False):
    targets = []
    if isinstance(instance, models.experiment.Experiment):
        for child in instance.children.order_by('urn'):
            # This shouldn't happen but just in case a scoreset ends up
            # without a target, then check.
            if child.get_target() is None:
                logger.warning("NoneType gene passed by {}.".format(child.urn))
                continue
            ref_map = get_ref_map(child.get_target())
            if ref_map is None:
                continue
            # Only proceed if a ref map is present.
            if child.private and user in child.contributors():
                targets.append([
                    child.get_target().get_name(),
                    child.get_target().category,
                    ref_map.format_reference_genome_organism_html(),
                ])
            elif not child.private:
                targets.append([
                    child.get_target().get_name(),
                    child.get_target().category,
                    ref_map.format_reference_genome_organism_html(),
                ])
    elif isinstance(instance, models.scoreset.ScoreSet):
        # This shouldn't happen but just in case a scoreset ends up
        # without a target, then check.
        if instance.get_target():
            logger.warning("NoneType gene passed by {}.".format(instance.urn))
            ref_map = get_ref_map(instance.get_target())
            if ref_map is not None:
                # Only proceed if a ref map is present.
                targets.append([
                    instance.get_target().get_name(),
                    instance.get_target().category,
                    ref_map.format_reference_genome_organism_html(),
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