from django.test import TestCase, RequestFactory
from django.core.exceptions import PermissionDenied
from django.contrib.messages.storage.fallback import FallbackStorage

from accounts.factories import UserFactory
from accounts.permissions import (
    assign_user_as_instance_viewer,
    assign_user_as_instance_editor,
)

from ..factories import ExperimentSetFactory
from dataset.views.experimentset import ExperimentSetDetailView


class TestExperimentSetDetailView(TestCase):
    """
    Test that experimentsets are displayed correctly to the public.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.template = "dataset/experimentset/experimentset.html"
        self.template_403 = "main/403.html"
        self.template_404 = "main/404.html"
        self.user = UserFactory()

    def create_request(self, method="get", **kwargs):
        request = getattr(self.factory, method)(**kwargs)
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)
        return request

    def test_uses_correct_template(self):
        obj = ExperimentSetFactory(private=False)
        response = self.client.get("/experimentset/{}/".format(obj.urn))
        self.assertTemplateUsed(response, self.template)

    def test_private_instance_will_403_if_no_permission(self):
        user = UserFactory()
        obj = ExperimentSetFactory(private=True)
        request = self.create_request(
            method="get", path="/experiment/{}/".format(obj.urn)
        )
        request.user = user
        with self.assertRaises(PermissionDenied):
            ExperimentSetDetailView.as_view()(request, urn=obj.urn)

    def test_403_uses_correct_template(self):
        obj = ExperimentSetFactory(private=True)
        response = self.client.get("/experimentset/{}/".format(obj.urn))
        self.assertTemplateUsed(response, self.template_403)

    def test_404_status_and_template_used_when_object_not_found(self):
        obj = ExperimentSetFactory()
        urn = obj.urn
        obj.delete()
        response = self.client.get("/experimentset/{}/".format(urn))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "main/404.html")

    def test_private_experiment_rendered_if_user_can_view(self):
        user = UserFactory()
        obj = ExperimentSetFactory(private=True)
        assign_user_as_instance_viewer(user, obj)
        request = self.factory.get("/experimentset/{}/".format(obj.urn))
        request.user = user
        response = ExperimentSetDetailView.as_view()(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)

    def test_user_with_edit_permission_can_see_add_and_edit_button(self):
        user = UserFactory()
        obj = ExperimentSetFactory(private=True)
        assign_user_as_instance_editor(user, obj)
        request = self.factory.get("/experimentset/{}/".format(obj.urn))
        request.user = user
        response = ExperimentSetDetailView.as_view()(request, urn=obj.urn)
        self.assertContains(response, "Add an experiment")

    def test_user_without_edit_permission_cannot_see_edit_button(self):
        user = UserFactory()
        obj = ExperimentSetFactory(private=True)
        assign_user_as_instance_viewer(user, obj)
        request = self.factory.get("/experimentset/{}/".format(obj.urn))
        request.user = user
        response = ExperimentSetDetailView.as_view()(request, urn=obj.urn)
        self.assertNotContains(response, "Add an experiment")
