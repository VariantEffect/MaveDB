# import json
#
# from django.test import TestCase
# from django.contrib.auth import get_user_model
#
# from accounts.permissions import (
#     assign_user_as_instance_admin
# )
#
# import dataset.constants as constants
# from dataset.factories import (
#     ScoreSetFactory, ExperimentFactory, ExperimentSetFactory
# )
#
# from variant.factories import VariantFactory
#
# User = get_user_model()
#
#
# class TestUserAPIViews(TestCase):
#
#     def setUp(self):
#         self.alice = User.objects.create(username="alice")
#         self.bob = User.objects.create(username="bob")
#
#     def test_can_serialize_all_users(self):
#         response = self.client.get("/api/get/user/all/")
#         result = json.loads(response.content.decode('utf-8'))
#         expected = {
#             "users": [
#                 {
#                     "username": "alice",
#                     "first_name": "",
#                     "last_name": "",
#                     'contributor_experimentsets': [],
#                     'contributor_experiments': [],
#                     'contributor_scoresets': []
#                 },
#                 {
#                     "username": "bob",
#                     "first_name": "",
#                     "last_name": "",
#                     'contributor_experimentsets': [],
#                     'contributor_experiments': [],
#                     'contributor_scoresets': []
#                 }
#             ]
#         }
#         self.assertEqual(expected, result)
#
#     def test_filters_out_private_entries(self):
#         scs_1 = ScoreSetFactory()
#         scs_2 = ScoreSetFactory()
#         assign_user_as_instance_admin(self.alice, scs_1)
#         assign_user_as_instance_admin(self.alice, scs_2)
#
#         scs_2.publish(propagate=True)
#         scs_2.save(save_parents=True)
#
#         response = self.client.get("/api/get/user/alice/")
#         result = json.loads(response.content.decode('utf-8'))
#         expected = {
#             "username": "alice",
#             "first_name": "",
#             "last_name": "",
#             'contributor_experimentsets': [],
#             'contributor_experiments': [],
#             'contributor_scoresets': [scs_2.urn]
#         }
#         self.assertEqual(expected, result)
#
#     def test_404_cannot_find_username(self):
#         response = self.client.get("/api/get/user/dddd/")
#         self.assertEqual(response.status_code, 404)
#
#
# class TestExperimentSetAPIViews(TestCase):
#
#     def test_filters_out_private(self):
#         exps = ExperimentSetFactory()
#         response = self.client.get("/api/get/experimentset/all/")
#         result = json.loads(response.content.decode('utf-8'))
#         expected = {"contributor_experimentsets": []}
#         self.assertEqual(expected, result)
#
#     def test_404_private_experimentset(self):
#         exps = ExperimentSetFactory()
#         response = self.client.get(
#             "/api/get/experimentset/{}/".format(exps.urn)
#         )
#         self.assertEqual(response.status_code, 404)
#
#     def test_404_experimentset_not_found(self):
#         response = self.client.get("/api/get/experimentset/dddd/")
#         self.assertEqual(response.status_code, 404)
#
#
# class TestExperimentAPIViews(TestCase):
#
#     def test_filters_out_private(self):
#         instance = ExperimentFactory()
#         response = self.client.get("/api/get/experiment/all/")
#         result = json.loads(response.content.decode('utf-8'))
#         expected = {"contributor_experiments": []}
#         self.assertEqual(expected, result)
#
#     def test_404_private(self):
#         instance = ExperimentFactory()
#         response = self.client.get(
#             "/api/get/experimentset/{}/".format(instance.urn)
#         )
#         self.assertEqual(response.status_code, 404)
#
#     def test_404_not_found(self):
#         response = self.client.get("/api/get/experiment/dddd/")
#         self.assertEqual(response.status_code, 404)
#
#
# class TestScoreSetAPIViews(TestCase):
#
#     def test_filters_out_private(self):
#         instance = ScoreSetFactory()
#         response = self.client.get("/api/get/scoreset/all/")
#         result = json.loads(response.content.decode('utf-8'))
#         expected = {"contributor_scoresets": []}
#         self.assertEqual(expected, result)
#
#     def test_404_private(self):
#         instance = ScoreSetFactory()
#         response = self.client.get(
#             "/api/get/scoreset/{}/".format(instance.urn)
#         )
#         self.assertEqual(response.status_code, 404)
#
#     def test_404_private_download_scores(self):
#         instance = ScoreSetFactory()
#         response = self.client.get(
#             "/api/get/scoreset/{}/scores/".format(instance.urn)
#         )
#         self.assertTemplateUsed(response, 'main/403_forbidden.html')
#
#     def test_404_private_download_counts(self):
#         instance = ScoreSetFactory()
#         response = self.client.get(
#             "/api/get/scoreset/{}/counts/".format(instance.urn)
#         )
#         self.assertTemplateUsed(response, 'main/403_forbidden.html')
#
#     def test_404_private_download_meta(self):
#         instance = ScoreSetFactory()
#         response = self.client.get(
#             "/api/get/scoreset/{}/metadata/".format(instance.urn)
#         )
#         self.assertTemplateUsed(response, 'main/403_forbidden.html')
#
#     def test_empty_text_response_download_counts_but_has_no_counts(self):
#         instance = ScoreSetFactory()
#         instance.publish(propagate=True)
#         instance.save(save_parents=True)
#         response = self.client.get(
#             "/api/get/scoreset/{}/counts/".format(instance.urn)
#         )
#         self.assertEqual(list(response.streaming_content), [])
#
#     def test_404_not_found(self):
#         response = self.client.get("/api/get/scoreset/dddd/")
#         self.assertEqual(response.status_code, 404)
#
#     def test_can_download_scores(self):
#         scs = ScoreSetFactory()
#         scs.publish(propagate=True)
#         scs.save(save_parents=True)
#         scs.dataset_columns = {
#             constants.score_columns: ["score"],
#             constants.count_columns: ["count"]
#         }
#         scs.save()
#         _ = VariantFactory(
#             scoreset=scs, hgvs="test",
#             data={
#                 constants.variant_score_data: {"score": "1"},
#                 constants.variant_count_data: {"count": "1"}
#             }
#         )
#         response = self.client.get(
#             "/api/get/scoreset/{}/scores/".format(scs.urn)
#         )
#         self.assertEqual(
#             list(response.streaming_content),
#             [b'hgvs,score\n', b'"test",1\n']
#         )
#
#     def test_can_download_counts(self):
#         scs = ScoreSetFactory()
#         scs.publish(propagate=True)
#         scs.dataset_columns = {
#             constants.score_columns: ["score"],
#             constants.count_columns: ["count"]
#         }
#         scs.save(save_parents=True)
#         _ = VariantFactory(
#             scoreset=scs, hgvs="test",
#             data={
#                 constants.variant_score_data: {"score": "1"},
#                 constants.variant_count_data: {"count": "1"}
#             }
#         )
#         response = self.client.get(
#             "/api/get/scoreset/{}/counts/".format(scs.urn)
#         )
#         self.assertEqual(
#             list(response.streaming_content),
#             [b'hgvs,count\n', b'"test",1\n']
#         )
