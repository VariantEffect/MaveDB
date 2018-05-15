from django import template
from django.utils.safestring import mark_safe

from dataset import models

register = template.Library()


@register.simple_tag
def display_targets(instance, user):
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
        return '-'
    return ', '.join(sorted(list(targets)))


@register.simple_tag
def display_species(instance, user):
    species = set()
    if isinstance(instance, models.experiment.Experiment):
        for child in instance.children:
            if child.private and user in child.contributors():
                species |= child.get_display_target_organisms()
            elif not child.private:
                species |= child.get_display_target_organisms()
    elif isinstance(instance, models.scoreset.ScoreSet):
        species |= instance.get_display_target_organisms()
    if not species:
        return '-'
    return mark_safe(', '.join(sorted(list(species))))


@register.assignment_tag
def visible_children(instance, user):
    children = []
    for child in instance.children:
        if not child.private:
            children.append(child)
        elif child.private and user in child.contributors():
            children.append(child)
    return list(sorted(children, key=lambda i: i.urn))

