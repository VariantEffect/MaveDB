import json

from django import forms

def parse_char_list(value):
    if isinstance(value, (list, set, tuple)):
        return list(value)
    try:
        value = json.loads(
            value
                .replace('[\'', '[\"')
                .replace('\']', '\"]')
                .replace(', \'', ', \"')
                .replace('\',', '\",')
        )
        if not isinstance(value, (list, set, tuple)):
            return [value]
        return value
    except (ValueError, TypeError):
        return [value]


class CSVCharField(forms.CharField):
    def clean(self, value):
        if value is None:
            return super(CSVCharField, self).clean(value)
        return [super(CSVCharField, self).clean(v)
                for v in parse_char_list(value)]
