import os

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def get_licence_logo_path(licence):
    name = licence.get_short_name()
    if name == 'CC0':
        return mark_safe(
            settings.STATIC_URL + 'core/mavedb/cc-zero.svg')
    elif name == 'CC BY-NC-SA 4.0':
        return mark_safe(
            settings.STATIC_URL + 'core/mavedb/by-nc-sa.svg')
    else:
        raise ValueError("Unrecognised licence name '{}'.".format(name))
