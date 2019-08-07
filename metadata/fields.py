from django.core.exceptions import ValidationError
from django.forms import ModelMultipleChoiceField, ModelChoiceField
from django.utils.translation import ugettext_lazy as _

from core.utilities import is_null


class FlexibleModelChoiceField(ModelChoiceField):
    def __init__(self, klass, queryset, *args, **kwargs):
        super(FlexibleModelChoiceField, self).__init__(
            queryset, *args, **kwargs
        )
        self.klass = klass
        self.queryset = queryset

    def to_python(self, value):
        if is_null(value):
            return None
        try:
            return self.klass.objects.get(**{self.to_field_name: value})
        except self.queryset.model.DoesNotExist:
            return self.klass(**{self.to_field_name: value})
        except (ValueError, TypeError):
            raise ValidationError(
                self.error_messages["invalid_choice"], code="invalid_choice"
            )


class FlexibleModelMultipleChoiceField(ModelMultipleChoiceField):
    """
    Custom Field to handle Keyword, ExternalAccession and TargetOrganism
    select fields, where new input shouldn't create an error but should
    create a new instance. This needs to be initialised inside a forms
    `init` method otherwise it will be created as a class instance since
    django will not defer it's instantiation at import time.
    """

    default_error_messages = {
        "list": _("Enter a list of values."),
        "invalid_choice": _(
            'Select a valid choice. "%(value)s" is not one of the'
            " available choices."
        ),
        "invalid_pk_value": _('"%(pk)s" is not a valid option value.'),
    }

    def __init__(self, klass, queryset, *args, **kwargs):
        super().__init__(queryset, *args, **kwargs)
        self.klass = klass
        self.queryset = queryset

    def to_python(self, value):
        values = []
        if not value:
            return values
        if not isinstance(value, (set, list, tuple)):
            value = [value]
        for v in value:
            if is_null(v):
                continue
            try:
                values.append(
                    self.klass.objects.get(**{self.to_field_name: v})
                )
            except self.queryset.model.DoesNotExist:
                values.append(self.klass(**{self.to_field_name: v}))
            except (ValueError, TypeError):
                raise ValidationError(
                    self.error_messages["invalid_choice"],
                    code="invalid_choice",
                )
        return values

    def clean(self, value):
        value = self.prepare_value(value)
        if self.required and not value:
            raise ValidationError(
                self.error_messages["required"], code="required"
            )
        elif not self.required and not value:
            return self.queryset.none()
        if not isinstance(value, (list, tuple)):
            raise ValidationError(self.error_messages["list"], code="list")
        qs = self.to_python(value)
        # Since this overrides the inherited ModelChoiceField.clean
        # we run custom validators here
        self.run_validators(value)
        return qs
