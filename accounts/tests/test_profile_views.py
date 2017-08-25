
from django.core.urlresolvers import reverse_lazy
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


def experimentset():
    return ExperimentSet.objects.create()


def experiment():
    return Experiment.objects.create(target="test", wt_sequence="AT")


def scoreset():
    return ScoreSet.objects.create(
        experiment=Experiment.objects.create(
            target="test", wt_sequence="AT"
        )
    )


class TestProfileHomeView(TestCase):

    def setUp(self):
        self.path = reverse_lazy("accounts:profile")
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")

    def test_uses_correct_template(self):
        self.fail("Write this test!")

    def test_requires_login(self):
        self.fail("Write this test!")


class TestProfileManageInstanceView(TestCase):

    def setUp(self):
        self.path = reverse_lazy("accounts:manage_instance")
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")
        self.data = {"users": []}

    def test_uses_correct_template(self):
        self.fail("Write this test!")

    def test_requires_login(self):
        self.fail("Write this test!")

    def test_404_if_no_admin_permissions(self):
        self.fail("Write this test!")

    def test_404_if_klass_cannot_be_inferred_from_accession(self):
        self.fail("Write this test!")

    def test_404_if_instance_not_found(self):
        self.fail("Write this test!")

    def test_updates_admins_with_valid_post_data(self):
        self.fail("Write this test!")

    def test_updates_contribs_with_valid_post_data(self):
        self.fail("Write this test!")

    def test_updates_viewers_with_valid_post_data(self):
        self.fail("Write this test!")

    def test_redirects_to_manage_page_valid_submission(self):
        self.fail("Write this test!")

    def test_returns_updated_admin_form_when_inputting_invalid_data(self):
        self.fail("Write this test!")

    def test_returns_updated_contrib_form_when_inputting_invalid_data(self):
        self.fail("Write this test!")

    def test_returns_viewer_admin_form_when_inputting_invalid_data(self):
        self.fail("Write this test!")


class TestProfileEditInstanceView(TestCase):

    def setUp(self):
        self.path = reverse_lazy("accounts:edit_instance")
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")
        self.experiment_data = {
            'private': "",
            'doi_id': "",
            'sra_id': "",
            'keywords': "",
            'external_accessions': "",
            'abstract': "",
            'method_desc': ""
        }
        self.scoreset_data = {
            'private': "",
            'doi_id': "",
            'keywords': "",
            'abstract': "",
            'method_desc': ""
        }

    def test_404_object_not_found(self):
        self.fail("Write this test!")

    def test_uses_correct_template(self):
        self.fail("Write this test!")

    def test_requires_login(self):
        self.fail("Write this test!")

    def test_can_defer_instance_type_from_accession(self):
        self.fail("Write this test!")

    def test_404_edit_an_experimentset(self):
        self.fail("Write this test!")

    def test_preview_mode_does_not_save_experiment_instance(self):
        self.fail("Write this test!")

    def test_preview_mode_does_not_save_scoreset_instance(self):
        self.fail("Write this test!")


class TestProfileViewInstanceView(TestCase):

    def setUp(self):
        self.path = reverse_lazy("accounts:view_instance")
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")

    def test_uses_correct_template(self):
        self.fail("Write this test!")

    def test_requires_login(self):
        self.fail("Write this test!")

    def test_redirects_to_correct_view_based_on_accession(self):
        self.fail("Write this test!")

    def test_404_not_viewer_contrib_or_admin(self):
        self.fail("Write this test!")

    def test_404_object_not_found(self):
        self.fail("Write this test!")
