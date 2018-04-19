from django.db.models import Q


class FilterMixin(object):
    """
    Mixin enabling the creation of complex search queries using
    AND/OR `Q` objects. Requires the base class `Viewset` from
    `django_rest_framework`.
    """
    def search_to_q(self, query_param, field_name, filter_type):
        value = self.request.query_params.getlist(query_param, [])
        if isinstance(value, (list, set)):
            return self.list_to_or_q(value, field_name, filter_type)
        else:
            return self.value_to_q(value, field_name, filter_type)

    def list_to_or_q(self, search_list, field_name, filter_type):
        q_object = Q()
        if not len(search_list):
            return q_object
        if len(search_list) == 1:
            return self.value_to_q(search_list[0], field_name, filter_type)
        for search_value in search_list:
            q_object |= self.value_to_q(search_value, field_name, filter_type)
        return q_object

    def list_to_and_q(self, search_list, field_name, filter_type):
        q_object = Q()
        if len(search_list) == 1:
            return self.value_to_q(search_list[0], field_name, filter_type)
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


class DatasetModelFilterMixin(FilterMixin):
    """
    Filter :class:`DatasetModel` instances by common fields such as
    `absract_text`, `method_text`, `title` and `short_description`.
    """
    def filter_abstract(self, query_key=None):
        query_key = query_key or 'abstract'
        return self.search_to_q(
            query_key, field_name='abstract_text', filter_type='icontains')

    def filter_method(self, query_key=None):
        query_key = query_key or 'method'
        return self.search_to_q(
            query_key, field_name='method_text', filter_type='icontains')

    def filter_title(self, query_key=None):
        query_key = query_key or 'title'
        return self.search_to_q(
            query_key, field_name='title', filter_type='icontains')

    def filter_description(self, query_key=None):
        query_key = query_key or 'description'
        return self.search_to_q(
            query_key, field_name='short_description', filter_type='icontains')

    def filter_keywords(self, query_key=None):
        query_key = query_key or 'keyword'
        return self.search_to_q(
            query_key,
            field_name='short_description', filter_type='icontains')

    def filter_sra(self, query_key=None):
        query_key = query_key or 'sra'
        return self.search_to_q(
            query_key, field_name='sra_ids__identifier', filter_type='iexact')

    def filter_doi(self, query_key=None):
        query_key = query_key or 'doi'
        return self.search_to_q(
            query_key, field_name='doi_ids__identifier', filter_type='iexact')

    def filter_pubmed(self, query_key=None):
        query_key = query_key or 'pubmed'
        return self.search_to_q(
            query_key, field_name='pubmed_ids__identifier', filter_type='iexact')

    def filter_urn(self, query_key=None):
        query_key = query_key or 'urn'
        return self.search_to_q(
            query_key, field_name='urn', filter_type='iexact')

    def make_q_object_list(self):
        if 'search' in self.request.query_params:
            self.key = 'search'
            self.join_func = self.or_join_qs
        else:
            self.key = None
            self.join_func = self.and_join_qs

        return [
            # self.filter_abstract(self.key),
            # self.filter_title(self.key),
            # self.filter_method(self.key),
            # self.filter_description(self.key),
            # self.filter_keywords(self.key),
            # self.filter_sra(self.key),
            # self.filter_doi(self.key),
            # self.filter_pubmed(self.key),
            self.filter_urn(self.key),
        ]
