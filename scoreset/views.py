import json

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.generic import DetailView
from django.forms import formset_factory
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


from experiment.models import Experiment
from main.models import (
    Keyword, ExternalAccession,
    TargetOrganism, ReferenceMapping
)
from main.forms import (
    KeywordForm, ExternalAccessionForm,
    ReferenceMappingForm, TargetOrganismForm
)

from .models import ScoreSet, Variant, SCORES_KEY, COUNTS_KEY
from .forms import ScoreSetForm

KeywordFormSet = formset_factory(KeywordForm)


class ScoresetDetailView(DetailView):
    """
    Simple detail view. See `scoreset/scoreset.html` for the template
    layout.
    """
    model = Experiment
    template_name = 'scoreset/scoreset.html'
    context_object_name = "scoreset"

    def get_object(self):
        accession = self.kwargs.get('accession', None)
        return get_object_or_404(ScoreSet, accession=accession)

    def get_context_data(self, **kwargs):
        context = super(ScoresetDetailView, self).get_context_data(**kwargs)
        variant_list = Variant.objects.all()
        paginator = Paginator(variant_list, 2)

        try:
            page = self.request.GET.get('page', 1)
            variants = paginator.page(page)
        except PageNotAnInteger:
            variants = paginator.page(1)
        except EmptyPage:
            variants = paginator.page(paginator.num_pages)

        context["variants"] = variants
        context["scores_columns"] = \
            context['scoreset'].dataset_columns[SCORES_KEY]
        context["counts_columns"] = \
            context['scoreset'].dataset_columns[COUNTS_KEY]

        return context


def download_scoreset_data(request, accession, dataset_key):
    """
    This view returns the variant dataset in csv format for a specific
    `ScoreSet`. This will either be the 'scores' or 'counts' dataset, which 
    are the only two supported keys in a scoreset's `dataset_columns` 
    attributes.

    Parameters
    ----------
    accession : `str`
        The `ScoreSet` accession which will be queried.
    dataset_key : `str`
        The type of dataset requested. Currently this is either 'scores' or
        'counts' as these are the only two supported datasets.

    Returns
    -------
    `StreamingHttpResponse`
        A stream is returned to handle the case where the data is too large
        to send all at once.
    """
    scoreset = get_object_or_404(ScoreSet, accession=accession)
    variants = scoreset.variant_set.all()
    columns = scoreset.dataset_columns[dataset_key]

    def gen_repsonse():
        yield ','.join(columns) + '\n'
        for var in variants:
            data = []
            for column_key in columns:
                data.append(str(var.data[dataset_key][column_key]))
            yield ','.join(data) + '\n'

    return StreamingHttpResponse(gen_repsonse(), content_type='text')


def download_scoreset_metadata(request, accession):
    """
    This view returns the scoreset metadata in text format for viewing.

    Parameters
    ----------
    accession : `str`
        The `ScoreSet` accession which will be queried.

    Returns
    -------
    `StreamingHttpResponse`
        A stream is returned to handle the case where the data is too large
        to send all at once.
    """
    scoreset = get_object_or_404(ScoreSet, accession=accession)
    json_response = json.dumps(scoreset.metadata)
    return HttpResponse(json_response, content_type="application/json")


def parse_text_formset(formset, model_class, prefix):
    """
    Helper function to parse a keyword formset into individual `Keyword`
    objects that can be saved later. If a keyword is not valid, it is appended
    as `None`.

    Parameters
    ----------
    formset : `KeywordFormSet`
        The formset to parse.
    model_class : `Keyword`
        The class that the formset instantiates.
    prefix : `str`
        The prefix of the formset. Should be set as 'keyword'.

    Returns
    -------
    `list`
        A list of valid but unsaved `Keyword`s
    """
    objects = []
    for i, form in enumerate(formset):
        text = form.data.get("{}-{}-text".format(prefix, i), "")
        try:
            model = model_class.objects.get(text=text)
            objects.append(model)
        except ObjectDoesNotExist:
            if form.is_valid():
                if form.cleaned_data:
                    model = form.save(commit=False)
                    objects.append(model)
            else:
                objects.append(None)
    return objects


def scoreset_create_view(request):
    """
    A view to create a new scoreset. Upon successs, this view will redirect
    to the newly created scoreset object.

    If you change the prefix arguments here, make sure to change them
    in the corresponding template element id fields as well. If you don't,
    expect everything to break horribly.
    """
    context = {}
    scoreset_form = ScoreSetForm(prefix="scoreset")
    keyword_formset = KeywordFormSet(prefix="keyword")
    context["scoreset_form"] = scoreset_form
    context["keyword_formset"] = keyword_formset

    if request.method == "POST":
        scoreset_form = ScoreSetForm(request.POST, prefix="scoreset")
        keyword_formset = KeywordFormSet(request.POST, prefix="keyword")
        context["scoreset_form"] = scoreset_form
        context["keyword_formset"] = keyword_formset

        if scoreset_form.is_valid():
            scoreset = scoreset_form.save(commit=False)
        else:
            return render(
                request,
                "scoreset/new_scoreset.html",
                context=context
            )

        keywords = parse_text_formset(keyword_formset, Keyword, "keyword")
        if not all([k is not None for k in keywords]):
            return render(
                request,
                "scoreset/new_scoreset.html",
                context=context
            )

        # Looks like everything is good to save.
        scoreset.save()
        scoreset_form.save_variants()
        for kw in keywords:
            kw.save()
            scoreset.keywords.add(kw)
        scoreset.save()
        accession = scoreset.accession
        return redirect("scoreset:scoreset_detail", accession=accession)

    else:
        return render(
            request,
            "scoreset/new_scoreset.html",
            context=context
        )
