
class SingletonMixin:
    """
    A singleton abtract model which allows only once instance(row) to exist.
    Must be the first class inherited to work.
    """
    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonMixin, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class NestedEnumMixin:
    """ Nested `Enum` of error messages relating to specific fields."""
    
    def __getattr__(self, item):
        """Allows this `Enum` to be nested by customising attribute lookup."""
        if item != '_value_':
            return getattr(self.value, item).value
        raise AttributeError
    