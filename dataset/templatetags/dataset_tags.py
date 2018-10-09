import json
from django import template
from django.utils.safestring import mark_safe

from dataset import models

register = template.Library()


@register.simple_tag
def display_targets(instance, user, javascript=False):
    targets = set()
    if isinstance(instance, models.experiment.Experiment):
        for child in instance.children:
            if child.private and user in child.contributors():
                targets.add(child.get_target().get_name())
            elif not child.private:
                targets.add(child.get_target().get_name())
    elif isinstance(instance, models.scoreset.ScoreSet):
        targets.add(instance.get_target().get_name())
    if not targets:
        if javascript:
            return mark_safe(json.dumps(['-']))
        return '-'
    if javascript:
        return mark_safe(json.dumps(sorted(list(targets))))
    return mark_safe(', '.join(sorted(list(targets))))


@register.simple_tag
def display_organism(instance, user, javascript=False):
    organism_names = set()
    if isinstance(instance, models.experiment.Experiment):
        for child in instance.children:
            if child.private and user in child.contributors():
                organism_names |= child.get_display_target_organisms()
            elif not child.private:
                organism_names |= child.get_display_target_organisms()
    elif isinstance(instance, models.scoreset.ScoreSet):
        organism_names |= instance.get_display_target_organisms()
    if not organism_names:
        if javascript:
            return mark_safe(json.dumps(['-']))
        return '-'
    if javascript:
        return mark_safe(json.dumps(sorted(list(organism_names))))
    return mark_safe(', '.join(sorted(list(organism_names))))


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