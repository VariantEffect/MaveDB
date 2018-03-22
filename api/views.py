import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, Http404
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect

from .serializers import (
    UserSerializer,
    ExperimentSetSerializer,
    ExperimentSerializer,
    ScoreSetSerializer
)

from experiment.models import Experiment, ExperimentSet
from experiment.models import ScoreSet
from experiment.constants import Constants
from accounts.permissions import (
    user_is_anonymous
)

User = get_user_model()


# Users
# -------------------------------------------------------------------- #
def users_all(request):
    serializer = UserSerializer()
    users = [
        user for user in User.objects.all()
        if not (user_is_anonymous(user) or user.is_superuser)
    ]
    data = serializer.serialize_set(users)
    return JsonResponse(data)


def user_by_username(request, username):
    try:
        user = get_object_or_404(User, username=username)
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    serializer = UserSerializer()
    data = serializer.serialize(user.pk)
    return JsonResponse(data)


# ExperimentSets
# -------------------------------------------------------------------- #
def experimentset_all(request):
    serializer = ExperimentSetSerializer()
    objects = ExperimentSet.objects.filter(private=False)
    data = serializer.serialize_set(objects)
    return JsonResponse(data)


def experimentset_by_urn(request, urn):
    try:
        obj = get_object_or_404(ExperimentSet, urn=urn)
        if obj.private:
            raise Http404()
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    serializer = ExperimentSetSerializer()
    data = serializer.serialize(obj.pk)
    return JsonResponse(data)


# Experiments
# -------------------------------------------------------------------- #
def experiments_all(request):
    serializer = ExperimentSerializer()
    objects = Experiment.objects.filter(private=False)
    data = serializer.serialize_set(objects)
    return JsonResponse(data)


def experiment_by_urn(request, urn):
    try:
        obj = get_object_or_404(Experiment, urn=urn)
        if obj.private:
            raise Http404()
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    serializer = ExperimentSerializer()
    data = serializer.serialize(obj.pk)
    return JsonResponse(data)


# Scoresets
# -------------------------------------------------------------------- #
def scoresets_all(request):
    serializer = ScoreSetSerializer()
    objects = ScoreSet.objects.filter(private=False)
    data = serializer.serialize_set(objects)
    return JsonResponse(data)


def scoreset_by_urn(request, urn):
    try:
        obj = get_object_or_404(ScoreSet, urn=urn)
        if obj.private:
            raise Http404()
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    serializer = ScoreSetSerializer()
    data = serializer.serialize(obj.pk)
    return JsonResponse(data)


def scoreset_score_data(request, urn):
    try:
        scoreset = get_object_or_404(ScoreSet, urn=urn)
        if scoreset.private:
            raise Http404()
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    variants = scoreset.variant_set.all().order_by("urn")
    columns = scoreset.dataset_columns[Constants.SCORES_KEY]

    def gen_repsonse():
        yield ','.join(columns) + '\n'
        for var in variants:
            data = []
            for column_key in columns:
                data.append(str(var.data[Constants.SCORES_KEY][column_key]))
            yield ','.join(data) + '\n'

    return StreamingHttpResponse(gen_repsonse(), content_type='text')


def scoreset_count_data(request, urn):
    try:
        scoreset = get_object_or_404(ScoreSet, urn=urn)
        if scoreset.private:
            raise Http404()
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    if not scoreset.has_counts_dataset():
        return StreamingHttpResponse("", content_type='text')

    variants = scoreset.variant_set.all().order_by("urn")
    columns = scoreset.dataset_columns[Constants.COUNTS_KEY]

    def gen_repsonse():
        yield ','.join(columns) + '\n'
        for var in variants:
            data = []
            for column_key in columns:
                data.append(str(var.data[Constants.COUNTS_KEY][column_key]))
            yield ','.join(data) + '\n'

    return StreamingHttpResponse(gen_repsonse(), content_type='text')
