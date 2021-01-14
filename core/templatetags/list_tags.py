from django import template

register = template.Library()


@register.simple_tag
def is_in(item, container, javascript=False):
    return (
        str(item in container).lower() if javascript else (item in container)
    )


@register.filter
def humanize_list(value):
    if len(value) == 0:
        return ""
    elif len(value) == 1:
        return value[0]

    s = ", ".join(value[:-1])

    if len(value) > 3:
        s += ","

    return f"{s} and {value[-1]}"
