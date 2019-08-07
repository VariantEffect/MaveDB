from django import template

register = template.Library()


@register.simple_tag
def is_in(item, container, javascript=False):
    return (
        str(item in container).lower() if javascript else (item in container)
    )
