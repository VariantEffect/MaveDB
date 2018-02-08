
from django.core import mail
from django.core.urlresolvers import reverse_lazy, reverse
from django.test import TestCase, RequestFactory
from django.utils.functional import SimpleLazyObject
from django.contrib.auth import get_user_model

from ..views import (
    manage_instance,
    edit_instance,
    profile_view,
    view_instance,
    get_class_for_accession
)

from main.models import ReferenceMapping
from experiment.models import ExperimentSet, Experiment
from scoreset.models import ScoreSet
from scoreset.validators import Constants
from scoreset.tests.utility import make_score_count_files

from ..models import Profile, user_is_anonymous
from ..permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer,
    remove_user_as_instance_admin,
    remove_user_as_instance_viewer,
    instances_for_user_with_group_permission,
    user_is_admin_for_instance,
    user_is_viewer_for_instance
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

    def test_requires_login(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)


class TestProfileManageInstanceView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice", password="secret")
        self.bob = User.objects.create(username="bob", password="secret")
        self.client.logout()

    def test_requires_login(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.bob, obj)
        response = self.client.get(
            '/accounts/profile/manage/{}/'.format(obj.accession)
        )
        self.assertEqual(response.status_code, 302)

    def test_404_if_no_admin_permissions(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_viewer(self.alice, obj)
        request = self.factory.get(
            '/accounts/profile/manage/{}/'.format(obj.accession)
        )
        request.user = self.alice
        response = manage_instance(request, accession=obj.accession)
        self.assertEqual(response.status_code, 404)

    def test_404_if_klass_cannot_be_inferred_from_accession(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_viewer(self.alice, obj)
        request = self.factory.get(
            '/accounts/profile/manage/NOT_ACCESSION/'
        )
        request.user = self.alice
        response = manage_instance(request, accession='NOT_ACCESSION')
        self.assertEqual(response.status_code, 404)

    def test_404_if_instance_not_found(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_viewer(self.alice, obj)
        obj.delete()
        request = self.factory.get(
            '/accounts/profile/manage/{}/'.format(obj.accession)
        )
        request.user = self.alice
        response = manage_instance(request, accession=obj.accession)
        self.assertEqual(response.status_code, 404)

    def test_updates_admins_with_valid_post_data(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.accession),
            data={
                "administrators[]": [self.bob.pk],
                "administrator_management-users": [self.bob.pk]
            }
        )
        request.user = self.alice
        response = manage_instance(request, accession=obj.accession)
        self.assertFalse(user_is_admin_for_instance(self.alice, obj))
        self.assertTrue(user_is_admin_for_instance(self.bob, obj))

    def test_updates_viewers_with_valid_post_data(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.accession),
            data={
                "viewers[]": [self.bob.pk],
                "viewer_management-users": [self.bob.pk]
            }
        )
        request.user = self.alice
        response = manage_instance(request, accession=obj.accession)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertTrue(user_is_viewer_for_instance(self.bob, obj))

    def test_redirects_to_manage_page_valid_submission(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.accession),
            data={
                "administrators[]": [self.alice.pk, self.bob.pk],
                "administrator_management-users": [self.alice.pk, self.bob.pk]
            }
        )
        request.user = self.alice
        response = manage_instance(request, accession=obj.accession)
        self.assertEqual(response.status_code, 302)

    def test_returns_admin_form_when_inputting_invalid_data(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.accession),
            data={
                "administrators[]": [10000],
                "administrator_management-users": [10000]
            }
        )
        request.user = self.alice
        response = manage_instance(request, accession=obj.accession)
        self.assertEqual(response.status_code, 200)

    def test_returns_viewer_admin_form_when_inputting_invalid_data(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.accession),
            data={
                "viewers[]": [10000],
                "viewer_management-users": [10000]
            }
        )
        request.user = self.alice
        response = manage_instance(request, accession=obj.accession)
        self.assertEqual(response.status_code, 200)


class TestProfileEditInstanceView(TestCase):

    def setUp(self):
        self.path = reverse_lazy("accounts:edit_instance")
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")
        self.alice.set_password("secret_key")
        self.alice.save()
        self.bob = User.objects.create(username="bob")
        self.experiment_post_data = {
            'doi_id': [""],
            'sra_id': [""],
            "target": ["brca1"],
            'wt_sequence': ["atcg"],
            "target_organism": [''],
            'keywords': [''],
            'external_accessions': [''],
            'abstract': [""],
            'method_desc': [""],
            'reference_mapping-TOTAL_FORMS': ['0'],
            'reference_mapping-INITIAL_FORMS': ['0'],
            'reference_mapping-MIN_NUM_FORMS': ['0'],
            'reference_mapping-MAX_NUM_FORMS': ['1000'],
            'reference_mapping-__prefix__-reference': [''],
            'reference_mapping-__prefix__-target_start': [''],
            'reference_mapping-__prefix__-target_end': [''],
            'reference_mapping-__prefix__-reference_start': [''],
            'reference_mapping-__prefix__-reference_end': [''],
            'submit': ['submit'],
            'publish': ['']
        }

        score_file, count_file = make_score_count_files()
        self.scoreset_post_data = {
            'replaces': [''],
            'abstract': [''],
            'method_desc': [''],
            'doi_id': [''],
            'keywords': [''],
            'submit': ['submit'],
            'publish': ['']
        }

    def make_scores_test_data(self, scores_data=None, counts_data=None):
        data = self.scoreset_post_data.copy()
        s_file, c_file = make_score_count_files(scores_data, counts_data)
        files = {Constants.SCORES_DATA: s_file}
        if c_file is not None:
            files[Constants.COUNTS_DATA] = c_file
        return data, files

    def test_404_object_not_found(self):
        obj = experiment()
        accession = obj.accession
        assign_user_as_instance_viewer(self.alice, obj)
        request = self.factory.get(
            '/accounts/profile/edit/{}/'.format(accession)
        )
        request.user = self.alice
        obj.delete()
        response = edit_instance(request, accession=accession)
        self.assertEqual(response.status_code, 404)

    def test_publish_button_sends_admin_emails(self):
        admin = User.objects.create(
            username="admin", email="admin@admin.com"
        )
        admin.is_superuser = True
        admin.save()

        obj = scoreset()
        assign_user_as_instance_admin(self.alice, obj)
        data, _ = self.make_scores_test_data()
        score_file, count_file = make_score_count_files()
        data['scores_data'] = score_file
        data['counts_data'] = count_file
        data['publish'] = ['publish']
        path = '/accounts/profile/edit/{}/'.format(obj.accession)
        self.client.login(username="alice", password="secret_key")
        response = self.client.post(path=path, data=data)

        obj.refresh_from_db()
        self.assertFalse(obj.private)
        self.assertEqual(len(mail.outbox), 1)

    def test_requires_login(self):
        obj = experiment()
        response = self.client.get(
            '/accounts/profile/edit/{}/'.format(obj.accession)
        )
        self.assertEqual(response.status_code, 302)

    def test_can_defer_instance_type_from_accession(self):
        accession = experiment().accession
        self.assertEqual(get_class_for_accession(accession), Experiment)

        accession = experimentset().accession
        self.assertEqual(get_class_for_accession(accession), ExperimentSet)

        accession = scoreset().accession
        self.assertEqual(get_class_for_accession(accession), ScoreSet)

        accession = "exp12012.1A"
        self.assertEqual(get_class_for_accession(accession), None)

    def test_404_edit_an_experimentset(self):
        obj = experimentset()
        request = self.factory.get(
            '/accounts/profile/edit/{}/'.format(obj.accession)
        )
        request.user = self.alice
        response = edit_instance(request, accession=obj.accession)
        self.assertEqual(response.status_code, 404)

    def test_published_scoreset_instance_returns_edit_only_mode_form(self):
        obj = scoreset()
        obj.private = False
        obj.save()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.get(
            '/accounts/profile/edit/{}/'.format(obj.accession)
        )
        request.user = self.alice
        response = edit_instance(request, accession=obj.accession)
        self.assertNotContains(response, 'Score data')
        self.assertNotContains(response, 'Count data')

    def test_published_experiment_instance_returns_edit_only_mode_form(self):
        obj = experiment()
        obj.private = False
        obj.save()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.get(
            '/accounts/profile/edit/{}/'.format(obj.accession)
        )
        request.user = self.alice
        response = edit_instance(request, accession=obj.accession)
        self.assertNotContains(response, 'Target')

    def test_refmapping_update_deletes_removed_mappings(self):
        obj = experiment()
        assign_user_as_instance_admin(self.alice, obj)
        data = self.experiment_post_data.copy()
        data['reference_mapping-TOTAL_FORMS'] = ['1']
        data['reference_mapping-0-reference'] = ['test1']
        data['reference_mapping-0-is_alternate'] = ['off']
        data['reference_mapping-0-target_start'] = [0]
        data['reference_mapping-0-target_end'] = [10]
        data['reference_mapping-0-reference_start'] = [0]
        data['reference_mapping-0-reference_end'] = [10]
        request = self.factory.post(
            '/accounts/profile/edit/{}/'.format(obj.accession),
            data=data
        )
        request.user = self.alice
        edit_instance(request, accession=obj.accession)

        # Now delete and add a new one.
        data = self.experiment_post_data.copy()
        data['reference_mapping-TOTAL_FORMS'] = ['1']
        data['reference_mapping-0-reference'] = ['test2']
        data['reference_mapping-0-is_alternate'] = ['off']
        data['reference_mapping-0-target_start'] = [0]
        data['reference_mapping-0-target_end'] = [10]
        data['reference_mapping-0-reference_start'] = [0]
        data['reference_mapping-0-reference_end'] = [20]
        request = self.factory.post(
            '/accounts/profile/edit/{}/'.format(obj.accession),
            data=data
        )
        request.user = self.alice
        response = edit_instance(request, accession=obj.accession)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReferenceMapping.objects.count(), 1)
        self.assertEqual(ReferenceMapping.objects.all()[0].reference, 'test2')


class TestProfileViewInstanceView(TestCase):

    def setUp(self):
        self.path = reverse_lazy("accounts:view_instance")
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")

    def test_requires_login(self):
        obj = ExperimentSet.objects.create()
        response = self.client.get(
            '/accounts/profile/view/{}/'.format(obj.accession)
        )
        self.assertEqual(response.status_code, 302)

    def test_404_if_no_permissions(self):
        obj = ExperimentSet.objects.create()
        request = self.factory.get(
            '/accounts/profile/view/{}/'.format(obj.accession)
        )
        request.user = self.alice
        response = view_instance(request, accession=obj.accession)
        self.assertEqual(response.status_code, 404)

    def test_404_if_obj_not_found(self):
        obj = ExperimentSet.objects.create()
        accession = obj.accession
        assign_user_as_instance_viewer(self.alice, obj)
        request = self.factory.get(
            '/accounts/profile/view/{}/'.format(accession)
        )
        request.user = self.alice
        obj.delete()
        response = view_instance(request, accession=accession)
        self.assertEqual(response.status_code, 404)
