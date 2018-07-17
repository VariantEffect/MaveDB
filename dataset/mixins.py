import json

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db import transaction

from accounts.permissions import user_is_anonymous, PermissionTypes
from search.mixins import logger, FilterMixin

from core.utilities import is_null
from core.utilities.pandoc import convert_md_to_html

from dataset.models.experiment import Experiment
from dataset.forms.experiment import ExperimentForm, ExperimentEditForm
from dataset.forms.scoreset import ScoreSetForm, ScoreSetEditForm

from genome.models import TargetGene
from genome.serializers import TargetGeneSerializer


class DatasetModelFilterMixin(FilterMixin):
    """
    Filter :class:`DatasetModel` instances by common fields:

        'urn': 'urn',
        'abstract': 'abstract_text',
        'method': 'method_text',
        'title': 'title',
        'description': 'short_description',
        'keywords': 'keywords',
        'sra': 'sra_ids__identifier',
        'doi': 'doi_ids__identifier',
        'pubmed': 'pubmed_ids__identifier',

    Expects the above :class:`DatasetModel` field names to work correctly.
    """
    # Get parameter names
    URN = 'urn'
    ABSTRACT = 'abstract'
    METHOD = 'method'
    TITLE = 'title'
    DESCRIPTION = 'description'
    KEYWORDS = 'keywords'
    SRA = 'sra'
    DOI = 'doi'
    PUBMED = 'pubmed'
    
    def search_field_to_function(self):
        return {
            self.ABSTRACT: self.filter_abstract,
            self.METHOD: self.filter_method,
            self.TITLE: self.filter_title,
            self.DESCRIPTION: self.filter_description,
            self.KEYWORDS: self.filter_keywords,
            self.SRA: self.filter_sra,
            self.DOI: self.filter_doi,
            self.PUBMED: self.filter_pubmed,
            self.URN: self.filter_urn,
        }

    def filter_abstract(self, value):
        return self.search_to_q(
            value, field_name='abstract_text', filter_type='icontains')

    def filter_method(self, value):
        return self.search_to_q(
            value, field_name='method_text', filter_type='icontains')

    def filter_title(self, value):
        return self.search_to_q(
            value, field_name='title', filter_type='icontains')

    def filter_description(self, value):
        return self.search_to_q(
            value, field_name='short_description', filter_type='icontains')

    def filter_keywords(self, value):
        return self.search_to_q(
            value, field_name='keywords__text', filter_type='iexact')

    def filter_sra(self, value):
        return self.search_to_q(
            value, field_name='sra_ids__identifier', filter_type='iexact')

    def filter_doi(self, value):
        return self.search_to_q(
            value, field_name='doi_ids__identifier', filter_type='iexact')

    def filter_pubmed(self, value):
        return self.search_to_q(
            value, field_name='pubmed_ids__identifier', filter_type='iexact')

    def filter_urn(self, value):
        return self.search_to_q(
            value, field_name='urn', filter_type='iexact')


class ExperimentSetFilterMixin(DatasetModelFilterMixin):
    """
    Filter :class:`ExperimentSet` instances by common fields:

        'urn': 'urn',
        'abstract': 'abstract_text',
        'method': 'method_text',
        'title': 'title',
        'description': 'short_description',
        'keywords': 'keywords',
        'sra': 'sra_ids__identifier',
        'doi': 'doi_ids__identifier',
        'pubmed': 'pubmed_ids__identifier',

    Expects the above :class:`ExperimentSet` field names to work correctly.
    """

    def search_field_to_function(self):
        dict_ = super().search_field_to_function()
        return dict_


class ExperimentFilterMixin(DatasetModelFilterMixin):
    """
    Filter :class:`Experiment` instances by common fields in
    :class:`DatasetModelFilterMixin` and the below:

        'target': 'scoresets__target__name',
        'species': 'scoresets__target__reference_maps__genome__species_name',
        'uniprot': 'scoresets__target__uniprot_id__identifier',
        'ensembl': 'scoresets__target__ensembl_id__identifier',
        'refseq': 'scoresets__target__refseq_id__identifier',
        'assembly': 'scoresets__target__reference_maps__genome__genome_id__identifier',
        'genome': 'scoresets__target__reference_maps__genome__short_name',
        'licence': 'scoresets__licence__short_name' || 'scoresets__licence__long_name'

    Expects the above :class:`Experiment` field names to work correctly.
    """
    # Get parameter names
    TARGET = 'target'
    SPECIES = 'species'
    UNIPROT = 'uniprot'
    ENSEMBL = 'ensembl'
    REFSEQ = 'refseq'
    ASSEMBLY = 'assembly'
    GENOME = 'genome'
    LICENCE = 'licence'

    def search_field_to_function(self):
        dict_ = super().search_field_to_function()
        dict_.update({
            self.SPECIES: self.filter_target_species,
            self.TARGET: self.filter_target,
            self.GENOME: self.filter_reference_genome_name,
            self.ASSEMBLY: self.filter_reference_genome_id,
            self.UNIPROT: self.filter_target_uniprot,
            self.ENSEMBL: self.filter_target_ensembl,
            self.REFSEQ: self.filter_target_refseq,
            self.LICENCE: self.filter_licence,
        })
        return dict_

    def filter_target(self, value):
        field_name = 'scoresets__target__name'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_species(self, value):
        field_name = 'scoresets__target__reference_maps__genome__species_name'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_uniprot(self, value):
        field_name = 'scoresets__target__uniprot_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_refseq(self, value):
        field_name = 'scoresets__target__refseq_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_ensembl(self, value):
        field_name = 'scoresets__target__ensembl_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_reference_genome_name(self, value):
        field_name = 'scoresets__target__reference_maps__genome__short_name'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_reference_genome_id(self, value):
        field_name = 'scoresets__target__reference_maps__genome__genome_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_licence(self, value):
        filter_type = 'icontains'
        return self.or_join_qs([
            self.search_to_q(value, 'scoresets__licence__short_name', filter_type),
            self.search_to_q(value, 'scoresets__licence__long_name', filter_type),
        ])


class ScoreSetFilterMixin(DatasetModelFilterMixin):
    """
    Filter :class:`ScoreSet` instances by common fields in
    :class:`DatasetModelFilterMixin` and the below:

        'target': 'target__name',
        'species': 'target__reference_maps__genome__species_name',
        'sequence': 'target__wt_sequence__sequence',
        'assembly': 'target__reference_maps__genome__genome_id__identifier',
        'genome': 'target__reference_maps__genome__short_name',
        'uniprot': 'target__uniprot_id__identifier',
        'ensembl': 'target__ensembl_id__identifier',
        'refseq': 'target__refseq_id__identifier',
        'licence': 'licence__short_name'

    Expects the above :class:`ScoreSet` field names to work correctly.
    """
    # Get parameter names
    TARGET = 'target'
    SPECIES = 'species'
    SEQUENCE = 'sequence'
    ASSEMBLY = 'assembly'
    GENOME = 'genome'
    UNIPROT = 'uniprot'
    ENSEMBL = 'ensembl'
    REFSEQ = 'refseq'
    LICENCE = 'licence'

    def search_field_to_function(self):
        dict_ = super().search_field_to_function()
        dict_.update({
            self.SPECIES: self.filter_species,
            self.TARGET: self.filter_target,
            self.GENOME: self.filter_reference_genome_name,
            self.ASSEMBLY: self.filter_reference_genome_id,
            self.UNIPROT: self.filter_target_uniprot,
            self.ENSEMBL: self.filter_target_ensembl,
            self.REFSEQ: self.filter_target_refseq,
            self.SEQUENCE: self.filter_target_sequence,
            self.LICENCE: self.filter_licence,
        })
        return dict_
    
    def filter_species(self, value):
        field_name = 'target__reference_maps__genome__species_name'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target(self, value):
        field_name = 'target__name'
        filter_type = 'iexact'
        value = value or 'target'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_sequence(self, value):
        field_name = 'target__wt_sequence__sequence'
        filter_type = 'iexact'
        value = value or 'sequence'
        return self.search_to_q(value, field_name, filter_type)

    def filter_reference_genome_name(self, value):
        field_name = 'target__reference_maps__genome__short_name'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_reference_genome_id(self, value):
        field_name = 'target__reference_maps__genome__genome_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_uniprot(self, value):
        field_name = 'target__uniprot_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_refseq(self, value):
        field_name = 'target__refseq_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_ensembl(self, value):
        field_name = 'target__ensembl_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_licence(self, value):
        filter_type = 'icontains'
        return self.or_join_qs([
            self.search_to_q(value, 'licence__short_name', filter_type),
            self.search_to_q(value, 'licence__long_name', filter_type),
        ])


class DatasetUrnMixin:
    """
    Overrides the `get_object` method of a detail-based view. Expects either
    `model` or `model_class` to be defined. `model` is defined by Django in
    DetailView. `model` is prioritized over `model_class`.
    """
    model_class = None

    def get_object(self, queryset=None):
        urn = self.kwargs.get('urn', None)
        if hasattr(self, 'model'):
            return get_object_or_404(self.model, urn=urn)
        return get_object_or_404(self.model_class, urn=urn)


class DatasetPermissionMixin(PermissionRequiredMixin):
    """
    Overrides the `has_permission` method of `PermissionRequiredMixin`.
    Returns
    """
    redirect_unauthenticated_users = "/login/"
    raise_exception = True
    permission_required = 'dataset.can_view'

    def has_permission(self):
        """
        Returns `False` if the user is anonymous. `True` if an authenticated
        user has permissions on a private dataset or `False` otherwise.
        """
        instance = self.get_object()
        is_public = not instance.private
        is_private = instance.private
        user = self.request.user
        anon_user = user_is_anonymous(user)
        perm = self.permission_required

        if is_private and anon_user:
            return False
        elif is_public and self.permission_required == 'dataset.can_view':
            return True
        elif is_private and perm != 'dataset.can_view' and anon_user:
            return False
        else:
            return user.has_perms(self.get_permission_required(), instance)


class DatasetFormViewContextMixin:
    """
    Overrides the `get_context_data` function from form-based Django class
    based views.
    """
    def get_context_data(self, **kwargs):
        """
        Inserts common context parameters into a context which javascript
        uses to dynamically populate select fields of invalid submissions.
        """
        context = super().get_context_data(**kwargs)

        # We're customising `FormView` to handle multiple forms so remove
        # the default form that is created by the base class.
        if 'form' in context:
            context.pop('form')
        # Below is invoked if paired with a MultiFormMixin
        if hasattr(self, 'get_forms'):
            for key, form in self.get_forms().items():
                if not key.endswith('_form'):
                    key += '_form'
                if key not in context:
                    context[key] = form

        if self.request.method == "POST":
            # Get the new keywords/urn/target org so that we can return
            # them for list repopulation if the form has errors.
            keywords = self.request.POST.getlist("keywords", [])
            keywords = [kw for kw in keywords if not is_null(kw)]

            sra_ids = self.request.POST.getlist("sra_ids", [])
            sra_ids = [i for i in sra_ids if not is_null(i)]

            doi_ids = self.request.POST.getlist("doi_ids", [])
            doi_ids = [i for i in doi_ids if not is_null(i)]

            pubmed_ids = self.request.POST.getlist("pubmed_ids", [])
            pubmed_ids = [i for i in pubmed_ids if not is_null(i)]

            uniprot_id = self.request.POST.getlist(
                "uniprot-offset-identifier", [])
            uniprot_id = [i for i in uniprot_id if not is_null(i)]

            ensembl_id = self.request.POST.getlist(
                "ensembl-offset-identifier", [])
            ensembl_id = [i for i in ensembl_id if not is_null(i)]

            refseq_id = self.request.POST.getlist(
                "refseq-offset-identifier", [])
            refseq_id = [i for i in refseq_id if not is_null(i)]

            context["repop_keywords"] = ','.join(keywords)
            context["repop_sra_identifiers"] = ','.join(sra_ids)
            context["repop_doi_identifiers"] = ','.join(doi_ids)
            context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)
            context["repop_uniprot_identifier"] = ','.join(uniprot_id)
            context["repop_ensembl_identifier"] = ','.join(ensembl_id)
            context["repop_refseq_identifier"] = ','.join(refseq_id)

        return context


class MultiFormMixin:
    """
    Mixin contains a helper function to instantiate an arbitrary form. For
    each key in `forms` you must define:

    - `get_<key>_form` : Instantiates the form referenced by `key`.
       Must have the parameters `**kwargs` and `form_class`.

    - `get_<key>_kwargs` : Gets the keyword arguments for the form referenced
       by `key`. Must specify argument `key` and return a dictionary with at
       least `data` populated.

    Generic methods with only pass on POST data/files. Write a custom function
    if you need GET data passed to the class constructor.
    
    Notes
    -----
    `restricted_forms` is currently unused.
    """
    forms = {}
    # Forms for update views form when an instance if not private.
    # restricted_forms is used when an instance is public instead of forms.
    restricted_forms = {}
    prefixes = {}
    form_string = 'get_{}_form'
    kwargs_string = 'get_{}_form_kwargs'

    def get_generic_form(self, form_class, **form_kwargs):
        return form_class(**form_kwargs)

    def get_generic_kwargs(self, key, **kwargs):
        if 'instance' not in kwargs:
            kwargs['instance'] = getattr(self, 'instance', None)
        if 'data' not in kwargs:
            kwargs['data'] = self.get_form_data()
        if 'files' not in kwargs:
            kwargs['files'] = self.get_form_files()
        if 'prefix' not in kwargs:
            kwargs['prefix'] = self.prefixes.get(key, None)
        
        form_class = self.forms[key]
        has_attr = form_class in \
                   (ExperimentForm, ScoreSetForm,
                    ExperimentEditForm, ScoreSetEditForm,)
        if has_attr and 'user' not in kwargs:
            kwargs['user'] = self.request.user
        
        return kwargs

    def get_form_files(self):
        if self.request.method == 'POST':
            return self.request.FILES
        return None

    def get_form_data(self):
        if self.request.method == 'POST':
            return self.request.POST
        return None

    def get_forms(self):
        created_forms = {}
        forms_dict = self.forms
        if getattr(self, 'instance', None):
            instance = getattr(self, 'instance')
            if not instance.private:
                forms_dict = self.restricted_forms

        for key, form_class in forms_dict.items():
            form_get_func = getattr(
                self, self.form_string.format(key), None)
            kwargs_get_func = getattr(
                self, self.kwargs_string.format(key), None)
            if not form_get_func:
                form_get_func = self.get_generic_form
                logger.info(
                    "'{}' has not been defined. Using default "
                    "method.".format("get_%s_form" % key))
            if not kwargs_get_func:
                kwargs_get_func = self.get_generic_kwargs
                logger.info(
                    "'{}' has not been defined. Using default "
                    "method.".format("get_%s_kwargs" % key))

            form_kwargs = kwargs_get_func(key)
            form_kwargs = self.get_generic_kwargs(key, **form_kwargs)
            created_forms[key] = form_get_func(form_class, **form_kwargs)

        return created_forms

    def forms_valid(self):
        forms = self.get_forms()
        for key, form in forms.items():
            if not form.is_valid():
                return False, dict()
        return True, forms

    @transaction.atomic
    def save_forms(self, forms):
        for key, form in forms.items():
            form.save()
        return forms
    
    
class DataSetAjaxMixin:
    def get_ajax(self, request, return_dict=False, *args, **kwargs):
        # If the request is ajax, then it's for previewing the abstract
        # or method description. This code is coupled with base.js. Changes
        # here might break the javascript code.
        data = {}
        if 'abstractText' in request.GET:
            data.update({
                "abstractText": convert_md_to_html(
                    request.GET.get("abstractText", "")),
            })
        if 'methodText' in request.GET:
            data.update({
                "methodText": convert_md_to_html(
                    request.GET.get("methodText", "")),
            })
        if return_dict:
            return data
        else:
            return HttpResponse(
                json.dumps(data), content_type="application/json")


class ExperimentAjaxMixin(DataSetAjaxMixin):
    pass


class ExperimentSetAjaxMixin(DataSetAjaxMixin):
    pass


class ScoreSetAjaxMixin(DataSetAjaxMixin):
    """
    Simple mixin to serialize a target gene for form target autocomplete and
    also to obtain the scoresets for a selected experiment to dynamically fill
    the replaces options with allowable selections.
    """
    def get_ajax(self, request, *args, **kwargs):
        # If the request is ajax, then it's for previewing the abstract
        # or method description. This code is coupled with base.js. Changes
        # here might break the javascript code.
        data = super().get_ajax(request, return_dict=True, *args, **kwargs)
        if 'targetId' in request.GET:
            pk = request.GET.get("targetId", "")
            if pk and TargetGene.objects.filter(pk=pk).count():
                targetgene = TargetGene.objects.get(pk=pk)
                data.update(TargetGeneSerializer(targetgene).data)
                map = targetgene.reference_maps.first()
                if map is not None:
                    data['genome'] = map.genome.pk
        if 'experiment' in request.GET:
            pk = request.GET.get("experiment", "")
            if pk and Experiment.objects.filter(pk=pk).count():
                experiment = Experiment.objects.get(pk=pk)
                scoresets = [
                    (s.pk, s.urn) for s in experiment.scoresets.order_by('urn')
                    if request.user.has_perm(PermissionTypes.CAN_EDIT, s) \
                    and not s.private
                ]
                data.update({'scoresets': scoresets})
                data.update(
                    {'keywords': [k.text for k in experiment.keywords.all()]}
                )
        return HttpResponse(json.dumps(data), content_type="application/json")


class PrivateDatasetFilterMixin:
    """
    Splits datasets into those viewable, filtering out those that are not.
    """
    def filter_and_split_instances(self, instances):
        private_viewable = []
        public = []
        for instance in instances:
            if user_is_anonymous(self.request.user) and instance.private:
                continue

            has_perm = self.request.user.has_perm(
                PermissionTypes.CAN_VIEW, instance)
            if not instance.private:
                public.append(instance)
            elif instance.private and has_perm:
                private_viewable.append(instance)

        return public, private_viewable