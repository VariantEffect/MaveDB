# from django.core.urlresolvers import reverse_lazy
# from django.http import HttpResponse, HttpResponseForbidden
# from django.test import TestCase, TransactionTestCase, RequestFactory
#
# from django.contrib.auth import get_user_model
# from django.contrib.auth import authenticate, login
#
# from accounts.permissions import (
#     user_is_admin_for_instance,
#     assign_user_as_instance_admin,
#     assign_user_as_instance_viewer
# )
#
# from metadata.models import Keyword, ExternalIdentifier
#
# from genome.models import (
#     ReferenceGenome, TargetOrganism, TargetGene, WildTypeSequence
# )
#
# from dataset.models import Experiment, ExperimentSet
# from dataset.views import (
#     ExperimentDetailView, ExperimentSetDetailView,
#     experiment_create_view
# )
#
#
# class TestExperimentSetDetailView(TestCase):
#     """
#     Test that experimentsets are displayed correctly to the public.
#     """
#
#     def setUp(self):
#         # Every test needs access to the request factory.
#         self.User = get_user_model()
#         self.factory = RequestFactory()
#
#     def test_uses_correct_template(self):
#         obj = ExperimentSet.objects.create(private=False)
#         response = self.client.get('/experiment/{}/'.format(obj.accession))
#         self.assertTemplateUsed(response, 'experiment/experimentset.html')
#
#     def test_private_experiment_403_if_no_permission(self):
#         obj = ExperimentSet.objects.create()
#         bob = self.User.objects.create_user(
#             username='bob', password='top_secret'
#         )
#         request = self.factory.get('/experiment/')
#         request.user = bob
#         response = ExperimentSetDetailView.as_view()(
#             request, accession=obj.accession)
#         self.assertEqual(response.status_code, 403)
#
#     def test_403_uses_template(self):
#         obj = ExperimentSet.objects.create()
#         response = self.client.get('/experiment/{}/'.format(obj.accession))
#         self.assertTemplateUsed(response, 'main/403_forbidden.html')
#
#     def test_404_status_and_template_used_when_object_not_found(self):
#         response = self.client.get('/experiment/{}/'.format("EXPS999999"))
#         self.assertEqual(response.status_code, 404)
#         self.assertTemplateUsed(response, 'main/404_not_found.html')
#
#     def test_private_experiment_rendered_if_user_can_view(self):
#         obj = ExperimentSet.objects.create()
#         bob = self.User.objects.create_user(
#             username='bob', password='top_secret'
#         )
#         assign_user_as_instance_viewer(bob, obj)
#         request = self.factory.get('/experiment/')
#         request.user = bob
#         response = ExperimentSetDetailView.as_view()(
#             request, accession=obj.accession)
#         self.assertEqual(response.status_code, 200)
#
#