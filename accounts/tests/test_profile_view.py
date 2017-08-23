
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from ..views import (
    manage_instance,
    edit_instance,
    profile_view,
    get_class_for_accession
)

from experiment.models import ExperimentSet, Experiment
from scoreset.models import ScoreSet

from ..models import Profile, user_is_anonymous
from ..permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_contributor,
    assign_user_as_instance_viewer,
    remove_user_as_instance_admin,
    remove_user_as_instance_contributor,
    remove_user_as_instance_viewer,
    instances_for_user_with_group_permission
)

User = get_user_model()


class TestProfileHomeView(TestCase):
    pass


class TestProfileManageInstanceView(TestCase):
    pass


class TestProfileEditInstanceView(TestCase):
    pass
