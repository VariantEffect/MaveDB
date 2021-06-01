import json
from ctypes import Union
from typing import Dict

from django.http import HttpResponse
from django.test import TestCase, RequestFactory

from core.utilities.pandoc import convert_md_to_html

from accounts.factories import UserFactory, AnonymousUserFactory

from ..models.experiment import Experiment
from ..models.scoreset import ScoreSet
from ..factories import (
    ExperimentWithScoresetFactory,
    ScoreSetWithTargetFactory,
    ExperimentFactory,
    ScoreSetFactory,
)
from ..mixins import (
    PrivateDatasetFilterMixin,
    ScoreSetAjaxMixin,
    DatasetPermissionMixin,
    DataSetAjaxMixin,
)


class TestPrivateDatasetFilterMixin(TestCase):
    class Driver(PrivateDatasetFilterMixin):
        def __init__(self, request):
            self.request = request

    def setUp(self):
        self.factory = RequestFactory()

    def test_separates_private_viewable(self):
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(request)

        i1 = ExperimentWithScoresetFactory()  # type: Experiment
        i2 = ExperimentWithScoresetFactory()  # type: Experiment
        i1.add_viewers(request.user)

        public, private = driver.filter_and_split_instances([i1, i2])
        self.assertIn(i1, private)
        self.assertNotIn(i2, private)
        self.assertNotIn(i1, public)
        self.assertNotIn(i2, public)

    def test_separates_public(self):
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(request)

        i1 = ExperimentWithScoresetFactory()  # type: Experiment
        i2 = ExperimentWithScoresetFactory()  # type: Experiment
        i1.private = False
        i1.save()

        public, private = driver.filter_and_split_instances([i1, i2])
        self.assertNotIn(i1, private)
        self.assertNotIn(i2, private)
        self.assertIn(i1, public)
        self.assertNotIn(i2, public)


class TestDataSetAjaxMixin(TestCase):
    """Testing pandoc conversion of abstract and method blobs."""

    class Driver(DataSetAjaxMixin):
        def __init__(self, request):
            self.request = request

    def setUp(self):
        self.factory = RequestFactory()

    def test_converts_abstract_to_md(self):
        request = self.factory.get(
            path="/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            data={"abstractText": "# Hello world"},
        )
        driver = self.Driver(request)
        response = json.loads(driver.get_ajax().content.decode())
        self.assertEqual(
            response["abstractText"], convert_md_to_html("# Hello world")
        )

    def test_converts_method_to_md(self):
        request = self.factory.get(
            path="/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            data={"methodText": "# Hello world"},
        )
        driver = self.Driver(request)
        response = json.loads(driver.get_ajax().content.decode())
        self.assertEqual(
            response["methodText"], convert_md_to_html("# Hello world")
        )

    def test_empty_dict_if_no_GET_param_found(self):
        request = self.factory.get(
            path="/", HTTP_X_REQUESTED_WITH="XMLHttpRequest", data={}
        )
        driver = self.Driver(request)
        response = json.loads(driver.get_ajax().content.decode())
        self.assertEqual(response, {})


class TestScoreSetAjaxMixin(TestCase):
    """
    Testing ajax response for getting target gene and
    experiment scoresets.
    """

    class Driver(ScoreSetAjaxMixin):
        def __init__(self, request):
            self.request = request

    def setUp(self):
        self.factory = RequestFactory()

    def test_can_get_target(self):
        scoreset = ScoreSetWithTargetFactory()
        request = self.factory.get(
            path="/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            data={"targetId": scoreset.target.pk},
        )
        driver = self.Driver(request)
        response = json.loads(driver.get_ajax().content.decode())

        self.assertEqual(response["name"], scoreset.target.name)
        self.assertEqual(
            response["genome"],
            scoreset.target.reference_maps.first().genome.pk,
        )

    def test_lists_editable_scoresets(self):
        user = UserFactory()
        experiment = ExperimentWithScoresetFactory()
        sc1 = experiment.scoresets.first()  # type: ScoreSet
        sc2 = ScoreSetWithTargetFactory(
            experiment=experiment
        )  # type: ScoreSet
        sc3 = ScoreSetWithTargetFactory(
            experiment=experiment
        )  # type: ScoreSet
        sc4 = ScoreSetWithTargetFactory(
            experiment=experiment
        )  # type: ScoreSet

        # Viewable since user has edit permission and is not private
        sc1.private = False
        sc1.add_editors(user)
        sc1.save(save_parents=True)

        # Is private so should not be viewable
        sc2.add_editors(user)

        # No edit permission so not viewable
        sc4.private = False
        sc4.save(save_parents=True)

        request = self.factory.get(
            path="/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            data={"experiment": experiment.pk},
        )
        request.user = user

        driver = self.Driver(request)
        response = json.loads(driver.get_ajax().content.decode())

        self.assertIn([sc1.pk, sc1.urn, sc1.title], response["scoresets"])
        self.assertNotIn([sc2.pk, sc2.urn, sc2.title], response["scoresets"])
        self.assertNotIn([sc3.pk, sc3.urn, sc3.title], response["scoresets"])
        self.assertNotIn([sc4.pk, sc4.urn, sc4.title], response["scoresets"])


class TestDatasetPermissionMixin(TestCase):
    """Testing permission mixin `has_permission` override."""

    class Driver(DatasetPermissionMixin):
        def __init__(self, instance, request):
            self.instance = instance
            self.request = request

        def get_object(self):
            return self.instance

    def setUp(self):
        self.factory = RequestFactory()

    # Manage
    def test_false_private_and_no_manage_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = DatasetPermissionMixin.MANAGE_PERMISSION
        self.assertFalse(driver.has_permission())

    def test_true_private_and_mange_permission_match(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_administrators(request.user)
        driver.permission_required = DatasetPermissionMixin.MANAGE_PERMISSION
        self.assertTrue(driver.has_permission())

    def test_false_public_and_no_manage_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.private = False
        scoreset.save()
        driver.permission_required = DatasetPermissionMixin.MANAGE_PERMISSION
        self.assertFalse(driver.has_permission())

    def test_true_public_and_manage_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_administrators(request.user)
        scoreset.private = False
        scoreset.save()
        driver.permission_required = DatasetPermissionMixin.MANAGE_PERMISSION
        self.assertTrue(driver.has_permission())

    # Edit
    def test_false_private_and_no_edit_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = DatasetPermissionMixin.EDIT_PERMISSION
        self.assertFalse(driver.has_permission())

    def test_true_private_and_edit_permission_match(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_editors(request.user)
        driver.permission_required = DatasetPermissionMixin.EDIT_PERMISSION
        self.assertTrue(driver.has_permission())

    def test_false_public_and_no_edit_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.private = False
        scoreset.save()
        driver.permission_required = DatasetPermissionMixin.EDIT_PERMISSION
        self.assertFalse(driver.has_permission())

    def test_true_public_and_edit_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_editors(request.user)
        scoreset.private = False
        scoreset.save()
        driver.permission_required = DatasetPermissionMixin.EDIT_PERMISSION
        self.assertTrue(driver.has_permission())

    # View
    def test_false_private_and_no_view_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = DatasetPermissionMixin.VIEW_PERMISSION
        self.assertFalse(driver.has_permission())

    def test_true_private_and_view_permission_match(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_viewers(request.user)
        driver.permission_required = DatasetPermissionMixin.VIEW_PERMISSION
        self.assertTrue(driver.has_permission())

    def test_true_public_instance_view(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        scoreset.private = False
        scoreset.save()
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        self.assertTrue(driver.has_permission())

    # Anon
    def test_false_anon(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = AnonymousUserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        self.assertFalse(driver.has_permission())

    def test_false_public_no_edit_permission_anon(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = AnonymousUserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = DatasetPermissionMixin.EDIT_PERMISSION
        self.assertFalse(driver.has_permission())

    def test_false_public_no_manage_permission_anon(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = AnonymousUserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = DatasetPermissionMixin.MANAGE_PERMISSION
        self.assertFalse(driver.has_permission())

    # Meta
    def test_can_only_view_public_or_private_meta_analysis_parent(self):
        instance = ExperimentFactory()

        meta_analysis = ScoreSetFactory(experiment=instance)
        child = ScoreSetFactory()
        meta_analysis.meta_analysis_for.add(child)

        request = self.factory.get("/")
        request.user = UserFactory()
        meta_analysis.add_administrators(request.user)

        def check_permissions():
            driver = self.Driver(instance=i, request=request)

            driver.permission_required = DatasetPermissionMixin.EDIT_PERMISSION
            self.assertFalse(driver.has_permission())

            driver.permission_required = (
                DatasetPermissionMixin.MANAGE_PERMISSION
            )
            self.assertFalse(driver.has_permission())

            driver.permission_required = DatasetPermissionMixin.VIEW_PERMISSION
            self.assertTrue(driver.has_permission())

        for i in [instance, instance.parent]:
            check_permissions()

        for i in [instance, instance.parent]:
            i.private = False
            i.save()
            check_permissions()

    def test_can_access_mixed_meta_analysis_if_permissions_are_present(self):
        experiment = ExperimentFactory()
        dummy = ExperimentFactory(experimentset=experiment.parent)

        child = ScoreSetFactory(experiment=experiment)
        meta_analysis = ScoreSetFactory(experiment=dummy)
        meta_analysis.meta_analysis_for.add(child)

        request = self.factory.get("/")
        request.user = UserFactory()
        meta_analysis.add_administrators(request.user)

        driver = self.Driver(instance=experiment.parent, request=request)

        perms = (
            ("can_edit", False),
            ("can_manage", False),
            ("can_view", False),
        )
        for perm, answer in perms:
            driver.permission_required = f"dataset.{perm}"
            self.assertEqual(driver.has_permission(), answer)

        experiment.parent.add_administrators(request.user)
        perms = (("can_edit", True), ("can_manage", True), ("can_view", True))
        for perm, answer in perms:
            driver.permission_required = f"dataset.{perm}"
            self.assertEqual(driver.has_permission(), answer)
