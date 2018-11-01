import json
import logging

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db import transaction

from accounts.permissions import user_is_anonymous, PermissionTypes

from core.utilities import is_null
from core.utilities.pandoc import convert_md_to_html

from dataset.models.experiment import Experiment
from dataset.forms.experiment import ExperimentForm, ExperimentEditForm
from dataset.forms.scoreset import ScoreSetForm, ScoreSetEditForm

from genome.models import TargetGene
from genome.serializers import TargetGeneSerializer

logger = logging.getLogger("django")


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
                    (s.pk, s.urn, s.title)
                    for s in experiment.scoresets.order_by('urn')
                    if request.user.has_perm(PermissionTypes.CAN_EDIT, s)
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
