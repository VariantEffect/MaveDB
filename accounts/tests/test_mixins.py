from django.test import TestCase
from django.contrib.auth import get_user_model

from dataset.models import ExperimentSet

from ..mixins import GroupPermissionMixin


User = get_user_model()


class TestGroupPermisionMixin(TestCase):
    pass