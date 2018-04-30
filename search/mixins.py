import logging

from django.db.models import Q

logger = logging.getLogger('django')


class FilterMixin(object):
    """
    Mixin enabling the creation of complex search queries using
    AND/OR `Q` objects.
    """
    def search_to_q(self, value, field_name, filter_type, join='or'):
        if not value:
            return Q()

        if join == 'or':
            join = self.list_to_or_q
        elif join == 'and':
            join = self.list_to_and_q
        else:
            raise ValueError("Unrecognised join command `{}`.".format(join))

        if isinstance(value, (list, set)):
            value = list(value)
            if len(value) > 1:
                return join(value, field_name, filter_type)
            else:
                value = value[0]

        return self.value_to_q(value, field_name, filter_type)

    def list_to_or_q(self, values, field_name, filter_type):
        q_object = Q()
        for v in values:
            q_object |= self.value_to_q(v, field_name, filter_type)
        return q_object

    def list_to_and_q(self, values, field_name, filter_type):
        q_object = Q()
        for v in values:
            q_object &= self.value_to_q(v, field_name, filter_type)
        return q_object

    @staticmethod
    def value_to_q(value, field_name, filter_type):
        value = str(value).strip()
        if not value:
            return Q()
        return Q(**{"%s__%s" % (field_name, filter_type): value})

    @staticmethod
    def and_join_qs(qs):
        if not len(qs):
            return Q()
        if len(qs) == 1:
            return qs[0]
        else:
            joined = qs[0]
            for q in qs[1:]:
                if len(q) > 0:
                    joined &= q
            return joined

    @staticmethod
    def or_join_qs(qs):
        if not len(qs):
            return Q()
        if len(qs) == 1:
            return qs[0]
        else:
            joined = qs[0]
            for q in qs[1:]:
                if len(q) > 0:
                    joined |= q
            return joined


class SearchMixin(FilterMixin):
    """
    Provides functionality to search multiple fields in a model, and combine
    them with either OR or AND. The entry point for creating a search `Q` is
    `search_all`.

    You can provide this function with a string to perform a general
    search on all model fields defined in `search_field_to_function`,
    or a dictionary mapping the keys in `search_field_to_function` to a value.
    You will also need to specify the `join_func` parameter to indicate how
    to join the Qs. If no function is provided, a list of un-joined `Q`s will
    be returned.

    For each key defined in `search_field_to_function`, a matching
    function will need to be defined which returns a `Q`. Example:

    def filter_abstract(self, value):
        return self.search_to_q(
            search_value='RNA transcription',
            field_name='abstract_text',
            filter_type='icontains',
        )

    You can specify how to construct a `Q` by providing a
    `field_name` to search a model with and a `filter_type` to `search_to_q`.
    `filter_types` are those supported by a `QuerySet`. ALternatively, you can
    define a more complex function returning a `Q`.

    `search_field_to_model_field` is currently unused, but define it anyway
    for future compatibility.
    """
    @staticmethod
    def search_field_to_model_field():
        raise NotImplementedError

    @staticmethod
    def search_field_to_function():
        raise NotImplementedError

    def get_function_for_field(self, field):
        if field not in self.search_field_to_function():
            logging.info(
                "Could not find a filter function for field '{}'.".format(
                    field))
            return None
        return self.search_field_to_function()[field]

    def q_object_list(self, dict_or_str):
        return self.search_all(dict_or_str, join_func=None)

    def and_q_object(self, dict_or_str):
        return self.search_all(dict_or_str, join_func=self.and_join_qs)

    def or_q_object(self, dict_or_str):
        return self.search_all(dict_or_str, join_func=self.or_join_qs)

    def search_all(self, value_or_dict, join_func=None):
        functions = self.search_field_to_function()
        if isinstance(value_or_dict, dict):
            qs = []
            for field, value in value_or_dict.items():
                search_func = self.get_function_for_field(field)
                if search_func is not None:
                    qs.append(search_func(value))
        elif isinstance(value_or_dict, str):
            qs = [func(value_or_dict) for _, func in functions.items()]
            join_func = self.or_join_qs
        else:
            raise TypeError("Expected `dict` or `str`. Found {}".format(
                type(value_or_dict).__name__
            ))
        if join_func is None:
            return qs
        return join_func(qs)
