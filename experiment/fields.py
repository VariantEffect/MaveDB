from django.core.exceptions import ValidationError
from django.forms import ModelMultipleChoiceField
from django.utils.translation import ugettext as _


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

    def __init__(self, klass, *args, **kwargs):
        super(ModelSelectMultipleField, self).__init__(*args, **kwargs)
        if self.to_field_name is None:
            raise ValueError("You must define 'to_field_name'.")
        self.klass = klass
        self.new_instances = []


    def create_if_not_exist(self, value):
        if value is None or not str(value).strip():
            return

        accession = str(value).strip()
        exists_in_db = self.klass.objects.filter(
            **{self.to_field_name: accession}
        ).count() > 0
        exists_in_new = accession in set([
            getattr(inst, self.to_field_name)
            for inst in self.new_instances
        ])
        if not (exists_in_new or exists_in_db):
            instance = self.klass(**{self.to_field_name: accession})
            self.new_instances.append(instance)
            return accession
        else:
            return None

    def clean(self, value):
        # The `target_organism` widget in `ExperimentForm` uses a non-multiple
        # select widget which will return a string instead of a list of values.
        # Instead of subclassing the single selection django widget just
        # for this field use this line here instead.
        if isinstance(value, str):
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
        existing = []
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            values = frozenset(value)
        except TypeError:
            # list of lists isn't hashable, for example
            raise ValidationError(
                self.error_messages['list'],
                code='list',
            )
        for value in values:
            created_value = self.create_if_not_exist(value)
            if created_value is None:
                existing.append(value)
        return super(ModelSelectMultipleField)._check_values(existing)



