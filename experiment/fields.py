
import string

from django.db.models import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.forms import ModelMultipleChoiceField
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _

from experiment.models import Keyword, ExternalAccession, TargetOrganism


class ModelSelectMultipleField(ModelMultipleChoiceField):
    """
    Custom Field to handle Keyword, ExternalAccession and TargetOrganism
    select fields, where new input shouldn't create an error but should
    create a new instance. This needs to be initialised inside a forms
    `init` method otherwise it will be created as a class instance since
    django will not defer it's instatiation at import time.
    """

    default_error_messages = {
        'list': _('Enter a list of values.'),
        'invalid_choice': _(
            'Select a valid choice. %(value)s is not one of the'
            ' available choices.'
        ),
        'invalid_pk_value': _(
            '"%(pk)s" is not a valid option value.'
        )
    }

    def __init__(self, klass, text_key, *args, **kwargs):
        super(ModelSelectMultipleField, self).__init__(*args, **kwargs)
        self.class_ = klass
        self.class_text_key = text_key
        self.new_instances = []

        if klass not in [Keyword, ExternalAccession, TargetOrganism]:
            raise TypeError("{} is not a supported class.".format(klass))

    @staticmethod
    def is_word(value):
        try:
            float(str(value).strip())
            is_float = True
        except (ValueError, TypeError):
            is_float = False

        try:
            int(str(value).strip())
            is_int = True
        except (ValueError, TypeError):
            is_int = False

        return not (is_float or is_int)

    def create_if_not_exist(self, value):
        if isinstance(value, str) and not value.strip():
            return

        key = self.to_field_name or 'pk'
        try:
            self.class_.objects.get(**{key: value})
        except (ValueError, ObjectDoesNotExist):
            text = str(value)
            exists_in_db = self.class_.objects.filter(
                **{self.class_text_key: text}
            ).exists()
            exists_in_new = text in {
                getattr(inst, self.class_text_key)
                for inst in self.new_instances
            }
            if not (exists_in_new or exists_in_db):
                instance = self.class_(**{self.class_text_key: text})
                self.new_instances.append(instance)

    def clean(self, value):
        # The `target_organism` widget in `ExperimentForm` uses a non-multiple
        # select widget which will return a string instead of a list of values.
        # Instead of subclassing the single selection django widget just
        # for this field use this line here instead.
        if self.class_ == TargetOrganism and not isinstance(value, list):
            value = [value]
        return super(ModelSelectMultipleField, self).clean(value)

    def _check_values(self, value):
        """
        Overrides the base method found in `ModelMultipleChoiceField`.

        Given a list of possible PK values, returns a QuerySet of the
        corresponding objects. Instead of raising a ValidationError if a given
        value not a valid PK and instead is a string input, a new instance is
        created. This handles the case where new keywords etc must be
        added to the database during an instance creation/edit.
        """
        not_pks = []
        existing_pks = []
        key = self.to_field_name or 'pk'
        text_key = self.class_text_key
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            value = frozenset(value)
        except TypeError:
            # list of lists isn't hashable, for example
            raise ValidationError(
                self.error_messages['list'],
                code='list',
            )
        for pk in value:
            try:
                self.queryset.filter(**{key: pk})
            except (ValueError, TypeError):
                if not self.is_word(pk):
                    raise ValidationError(
                        self.error_messages['invalid_pk_value'],
                        code='invalid_pk_value',
                        params={'pk': pk},
                    )
                else:
                    if self.queryset.filter(**{text_key: pk}).exists():
                        o = self.queryset.get(**{text_key: pk})
                        existing_pks.append(getattr(o, key))
                    not_pks.append(pk)

        valid_pks = [v for v in value if v not in not_pks]
        valid_pks += [v for v in existing_pks if v not in valid_pks]
        qs = self.queryset.filter(**{'%s__in' % key: valid_pks})
        pks = set(force_text(getattr(o, key)) for o in qs)
        for val in value:
            if force_text(val) not in pks:
                if self.is_word(force_text(val)):
                    instance = self.create_if_not_exist(val)
                else:
                    raise ValidationError(
                        self.error_messages['invalid_choice'],
                        code='invalid_choice',
                        params={'value': val},
                    )
        return qs
