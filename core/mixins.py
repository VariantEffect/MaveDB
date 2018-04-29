import logging

from django.db.models import Q

logger = logging.getLogger('django')


class FilterMixin(object):
    """
    Mixin enabling the creation of complex search queries using
    AND/OR `Q` objects.
    """
    def search_to_q(self, search_value, field_name, filter_type):
        if isinstance(search_value, (list, set)):
            search_value = list(search_value)
            if len(search_value) == 1:
                return self.value_to_q(search_value[0], field_name, filter_type)
            return self.list_to_or_q(search_value, field_name, filter_type)
        else:
            return self.value_to_q(search_value, field_name, filter_type)

    def list_to_or_q(self, search_list, field_name, filter_type):
        q_object = Q()
        if not len(search_list):
            return q_object
        for search_value in search_list:
            q_object |= self.value_to_q(search_value, field_name, filter_type)
        return q_object

    def list_to_and_q(self, search_list, field_name, filter_type):
        q_object = Q()
        for search_value in search_list:
            q_object &= self.value_to_q(search_value, field_name, filter_type)
        return q_object

    @staticmethod
    def value_to_q(value, field_name, filter_type):
        value = str(value).strip()
        if not value:
            return Q()
        return Q(**{"%s__%s" % (field_name, filter_type): value})

    @staticmethod
    def and_join_qs(qs):
        joined = Q()
        for q in qs:
            if len(q) > 0:
                joined &= q
        return joined

    @staticmethod
    def or_join_qs(qs):
        joined = Q()
        for q in qs:
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
            search_value=value,
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
            logging.warning(
                "Could not find filter function for field {}.".format(field)
            )
            return None
        return self.search_field_to_function()[field]

    def q_object_list(self, dict_or_str):
        return self.search_all(dict_or_str, join_func=None)

    def and_q_object(self, dict_or_str):
        return self.search_all(dict_or_str, join_func=self.and_join_qs)

    def or_q_object(self, dict_or_str):
        return self.search_all(dict_or_str, join_func=self.or_join_qs)

    def search_all(self, value, join_func=None):
        functions = self.search_field_to_function()
        if isinstance(value, dict):
            qs = []
            for field, value in value.items():
                search_func = self.get_function_for_field(field)
                if search_func is not None:
                    qs.append(search_func(value))
        elif isinstance(value, str):
            qs = [func(value) for _, func in functions.items()]
        else:
            raise TypeError("Expected `dict` or `str`. Found {}".format(
                type(value).__name__
            ))
        if join_func is None:
            return qs
        return join_func(qs)
