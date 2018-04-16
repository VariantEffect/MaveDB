from django.test import TestCase, RequestFactory

from accounts.factories import UserFactory
from accounts.permissions import assign_user_as_instance_viewer

from ..factories import ExperimentSetFactory
from dataset.views.experimentset import ExperimentSetDetailView


class TestExperimentSetDetailView(TestCase):
    """
    Test that experimentsets are displayed correctly to the public.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.template = 'dataset/experimentset/experimentset.html'
        self.template_403 = 'main/403_forbidden.html'
        self.template_404 = 'main/404_not_found.html'

    def test_uses_correct_template(self):
        obj = ExperimentSetFactory()
        obj.publish()
        obj.save()
        response = self.client.get('/experimentset/{}/'.format(obj.urn))
        self.assertTemplateUsed(response, self.template)

    def test_private_instance_will_403_if_no_permission(self):
        user = UserFactory()
        obj = ExperimentSetFactory(private=True)
        request = self.factory.get('/experimentset/{}/'.format(obj.urn))
        request.user = user
        response = ExperimentSetDetailView.as_view()(request, urn=obj.urn)
        self.assertEqual(response.status_code, 403)

    def test_403_uses_correct_template(self):
        obj = ExperimentSetFactory(private=True)
        response = self.client.get('/experimentset/{}/'.format(obj.urn))
        self.assertTemplateUsed(response, self.template_403)

    def test_404_status_and_template_used_when_object_not_found(self):
        obj = ExperimentSetFactory()
        urn = obj.urn
        obj.delete()
        response = self.client.get('/experimentset/{}/'.format(urn))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'main/404_not_found.html')

    def test_private_experiment_rendered_if_user_can_view(self):
        user = UserFactory()
        obj = ExperimentSetFactory(private=True)
        assign_user_as_instance_viewer(user, obj)
        request = self.factory.get('/experimentset/{}/'.format(obj.urn))
        request.user = user
        response = ExperimentSetDetailView.as_view()(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)
