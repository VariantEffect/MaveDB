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
        self.new_values = set()

    def is_new_value(self, value):
        """
        Creates the an instance with the accession `value` if it does not exist
        in the database already. The value is considered new if it cannot be
        found filtering by `to_field_name`.

        Parameters
        ----------
        value : str
            The field value corresponding the model field `to_field_name`.

        Returns
        -------
        `bool`
            Returns True if an instance already exists with the value for the
            field defined by `to_field_name`.
        """
        accession = str(value).strip()
        exists_in_db = self.klass.objects.filter(
            **{self.to_field_name: accession}
        ).count() > 0
        exists_in_new = accession in set([
            getattr(inst, self.to_field_name)
            for inst in self.new_values
        ])
        return not (exists_in_db or exists_in_new)

    def clean(self, value):
        """
        Cleans the value returning a QuerySet of instances relating
        to the chosen values in `value`.

        Note: QuerySet that is returned will only contain instances that
        are already in the database. If new keywords etc have been created
        then these values are in the `new_values` attribute. These should
        be saved only when the form containing this field is valid.
        """
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

        Parameters
        ----------
        value : list
            The field values corresponding the model field `to_field_name`.

        Returns
        -------
        `QuerySet`
            Returns the queryset of instances corresponding to the selected
            options.
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
            if self.is_new_value(value):
                self.new_values.add(value)
            else:
                existing.append(value)
        return super(ModelSelectMultipleField)._check_values(existing)



