from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory

from accounts.factories import UserFactory
from accounts.permissions import (
    assign_user_as_instance_viewer,
    assign_user_as_instance_editor,
    assign_user_as_instance_admin,
    user_is_admin_for_instance
)

from genome.factories import GenomicIntervalFactory

from ..views.scoreset import ReferenceMapEditView


request = RequestFactory()


class TestReferenceMapEditView(TestCase):

    @staticmethod
    def post_data():
        return {

        }

    @staticmethod
    def get_data():
        return {

        }

    @staticmethod
    def make_scoreset_with_user(user=None, permission_func=None):
        if user is None:
            user = UserFactory()
        if permission_func is None:
            permission_func = assign_user_as_instance_admin

        interval = GenomicIntervalFactory()
        scoreset = interval.reference_map.target.scoreset
        permission_func(user, scoreset)

        return user, scoreset

    def test_refmap_form_created_with_instance_sel_by_management_form(self):
        pass

    def test_interval_formset_created_with_qset_sel_by_management_form(self):
        pass

    def test_refmap_form_creates_new_if_management_form_selects_none(self):
        pass

    def test_interval_formset_creates_new_if_management_form_selects_none(self):
        pass