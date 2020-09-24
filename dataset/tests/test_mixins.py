import json

from django.test import TestCase, RequestFactory, mock
from django.http import Http404

from core.utilities.pandoc import convert_md_to_html

from accounts.factories import UserFactory, AnonymousUserFactory

from ..models.experiment import Experiment
from ..models.scoreset import ScoreSet
from ..forms.scoreset import ScoreSetForm
from ..forms.experiment import ExperimentForm
from ..factories import (
    ExperimentWithScoresetFactory,
    ScoreSetWithTargetFactory,
    ExperimentFactory,
    ScoreSetFactory,
    ExperimentSetFactory,
)
from ..mixins import (
    PrivateDatasetFilterMixin,
    ScoreSetAjaxMixin,
    MultiFormMixin,
    DatasetUrnMixin,
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

    def setUp(self):
        self.factory = RequestFactory()

    def test_converts_abstract_to_md(self):
        request = self.factory.get(
            path="/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            data={"abstractText": "# Hello world"},
        )
        driver = DataSetAjaxMixin()
        response = json.loads(driver.get_ajax(request).content.decode())
        self.assertEqual(
            response["abstractText"], convert_md_to_html("# Hello world")
        )

    def test_converts_method_to_md(self):
        request = self.factory.get(
            path="/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            data={"methodText": "# Hello world"},
        )
        driver = DataSetAjaxMixin()
        response = json.loads(driver.get_ajax(request).content.decode())
        self.assertEqual(
            response["methodText"], convert_md_to_html("# Hello world")
        )

    def test_empty_dict_if_no_GET_param_found(self):
        request = self.factory.get(
            path="/", HTTP_X_REQUESTED_WITH="XMLHttpRequest", data={}
        )
        driver = DataSetAjaxMixin()
        response = json.loads(driver.get_ajax(request).content.decode())
        self.assertEqual(response, {})


class TestScoreSetAjaxMixin(TestCase):
    """
    Testing ajax response for getting target gene and
    experiment scoresets.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def test_can_get_target(self):
        driver = ScoreSetAjaxMixin()
        scoreset = ScoreSetWithTargetFactory()
        request = self.factory.get(
            path="/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            data={"targetId": scoreset.target.pk},
        )
        response = json.loads(driver.get_ajax(request).content.decode())
        self.assertEqual(response["name"], scoreset.target.name)
        self.assertEqual(
            response["genome"],
            scoreset.target.reference_maps.first().genome.pk,
        )

    def test_lists_editable_scoresets(self):
        driver = ScoreSetAjaxMixin()

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
        response = json.loads(driver.get_ajax(request).content.decode())
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

        driver.permission_required = "dataset.can_manage"
        self.assertFalse(driver.has_permission())

    def test_true_private_and_mange_permission_match(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_administrators(request.user)
        driver.permission_required = "dataset.can_manage"
        self.assertTrue(driver.has_permission())

    def test_false_public_and_no_manage_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.private = False
        scoreset.save()
        driver.permission_required = "dataset.can_manage"
        self.assertFalse(driver.has_permission())

    def test_true_public_and_manage_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_administrators(request.user)
        scoreset.private = False
        scoreset.save()
        driver.permission_required = "dataset.can_manage"
        self.assertTrue(driver.has_permission())

    # Edit
    def test_false_private_and_no_edit_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = "dataset.can_edit"
        self.assertFalse(driver.has_permission())

    def test_true_private_and_edit_permission_match(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_editors(request.user)
        driver.permission_required = "dataset.can_edit"
        self.assertTrue(driver.has_permission())

    def test_false_public_and_no_edit_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.private = False
        scoreset.save()
        driver.permission_required = "dataset.can_edit"
        self.assertFalse(driver.has_permission())

    def test_true_public_and_edit_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_editors(request.user)
        scoreset.private = False
        scoreset.save()
        driver.permission_required = "dataset.can_edit"
        self.assertTrue(driver.has_permission())

    # View
    def test_false_private_and_no_view_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = "dataset.can_view"
        self.assertFalse(driver.has_permission())

    def test_true_private_and_view_permission_match(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        scoreset.add_viewers(request.user)
        driver.permission_required = "dataset.can_view"
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

        driver.permission_required = "dataset.can_edit"
        self.assertFalse(driver.has_permission())

    def test_false_public_no_manage_permission_anon(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get("/")
        request.user = AnonymousUserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = "dataset.can_manage"
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

            driver.permission_required = "dataset.can_edit"
            self.assertFalse(driver.has_permission())

            driver.permission_required = "dataset.can_manage"
            self.assertFalse(driver.has_permission())

            driver.permission_required = "dataset.can_view"
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


class TestDatasetUrnMixin(TestCase):
    """Tests the `get_object` method overridden by `DatasetUrnMixin"""

    class Driver(DatasetUrnMixin):
        def __init__(self, kwargs):
            self.kwargs = kwargs
            self.model = None
            self.model_class = None

    def test_404_not_found(self):
        driver = self.Driver(kwargs={"urn": None})
        driver.model = ScoreSet
        with self.assertRaises(Http404):
            driver.get_object()

    def test_can_get_object(self):
        scoreset = ScoreSetWithTargetFactory()
        driver = self.Driver(kwargs={"urn": scoreset.urn})
        driver.model = ScoreSet
        self.assertEqual(scoreset, driver.get_object())

    def test_falls_back_to_model_class(self):
        scoreset = ScoreSetWithTargetFactory()
        driver = self.Driver(kwargs={"urn": scoreset.urn})
        driver.model_class = ScoreSet
        driver.__delattr__("model")
        driver.model_class = ScoreSet
        self.assertEqual(scoreset, driver.get_object())


class TestMultiFormMixin(TestCase):
    """Tests that custom form and kwarg methods are called as expected."""

    class Driver(MultiFormMixin):
        def __init__(self, request, user):
            self.request = request
            self.user = user

        def get_scoreset_form(self, form_class, **kwargs):
            return form_class(**kwargs)

        def get_scoreset_form_kwargs(self, key):
            return {"user": self.user, "data": {}}

    def setUp(self):
        self.factory = RequestFactory()

    @mock.patch.object(Driver, "get_scoreset_form_kwargs")
    @mock.patch.object(Driver, "get_scoreset_form")
    def test_calls_scoreset_form_method(self, form_patch, kwarg_patch):
        user = UserFactory()
        request = self.factory.post("/", data={})
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {"scoreset": ScoreSetForm}
        driver.get_forms()
        form_patch.assert_called()
        kwarg_patch.assert_called()

    @mock.patch.object(Driver, "get_scoreset_form")
    def test_does_not_overwrite_user_in_kwargs(self, form_patch):
        request = self.factory.post("/")
        user1 = UserFactory()
        user2 = UserFactory()
        request.user = user2
        driver = self.Driver(request=request, user=user1)
        driver.forms = {"scoreset": ScoreSetForm}

        driver.get_forms()
        self.assertEqual(form_patch.call_args[1]["user"], driver.user)

    @mock.patch.object(Driver, "get_generic_form")
    def test_adds_missing_kwargs(self, form_patch):
        user = UserFactory()
        request = self.factory.post("/")
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {"experiment": ExperimentForm}

        driver.get_forms()
        self.assertIn("files", form_patch.call_args[1])
        self.assertIn("data", form_patch.call_args[1])
        self.assertIn("instance", form_patch.call_args[1])
        self.assertIn("prefix", form_patch.call_args[1])
        self.assertIn("user", form_patch.call_args[1])

    @mock.patch.object(Driver, "get_scoreset_form")
    def test_adds_form_prefix(self, form_patch):
        user = UserFactory()
        request = self.factory.post("/")
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {"scoreset": ScoreSetForm}
        driver.prefixes = {"scoreset": "foobar"}

        driver.get_forms()
        self.assertEqual(form_patch.call_args[1]["prefix"], "foobar")

    @mock.patch.object(Driver, "get_scoreset_form")
    def test_adds_form_instance(self, form_patch):
        user = UserFactory()
        request = self.factory.post("/")
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {"scoreset": ScoreSetForm}

        scoreset = ScoreSetWithTargetFactory()
        setattr(driver, "instance", scoreset)

        driver.get_forms()
        self.assertEqual(form_patch.call_args[1]["instance"], scoreset)

    @mock.patch.object(Driver, "get_scoreset_form")
    def test_adds_user_instance(self, form_patch):
        user = UserFactory()
        request = self.factory.post("/")
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {"scoreset": ScoreSetForm}

        driver.get_forms()
        self.assertEqual(form_patch.call_args[1]["user"], request.user)

    @mock.patch.object(Driver, "get_generic_kwargs")
    @mock.patch.object(Driver, "get_generic_form")
    def test_calls_generic_when_no_method_defined(
        self, form_patch, kwarg_patch
    ):
        user = UserFactory()
        request = self.factory.post("/")
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {"experiment": ExperimentForm}
        driver.get_forms()
        form_patch.assert_called()
        kwarg_patch.assert_called()
