# from django.http import QueryDict
# from django.test import TestCase, RequestFactory
# from django.contrib.auth import get_user_model
#
# from variant.models import Variant
# from main.models import Licence
# from metadata.models import (
#     Keyword, SraIdentifier, PubmedIdentifier, DoiIdentifier
# )
#
# import dataset.constants as constants
# from ..models import Experiment, ScoreSet, ExperimentSet
# from ..forms import ScoreSetEditForm
# from .utility import make_score_count_files
#
#
# class TestScoreSetEditForm(TestCase):
#
#     def setUp(self):
#         self.experiment = Experiment.objects.create(
#             target="test", wt_sequence="ATCG"
#         )
#
#     def test_can_instantiate_form_with_instance(self):
#         instance = ScoreSet.objects.create(experiment=self.experiment)
#         form = ScoreSetEditForm({}, instance=instance)
#         self.assertTrue(form.is_valid())
#
#     def test_can_save_non_keyword_fields(self):
#         instance = ScoreSet.objects.create(experiment=self.experiment)
#         data = {
#             "method_desc": "hello",
#             "abstract": "world",
#             "doi_id": "11111"
#         }
#         post = QueryDict('', mutable=True)
#         post.update(data)
#         form = ScoreSetEditForm(post, instance=instance)
#         self.assertTrue(form.is_valid())
#
#         scs = form.save(commit=True)
#         self.assertEqual(scs.method_desc, "hello")
#         self.assertEqual(scs.abstract, "world")
#         self.assertEqual(scs.doi_id, "11111")
#
#     def test_can_create_new_keywords(self):
#         instance = ScoreSet.objects.create(experiment=self.experiment)
#         post = QueryDict('', mutable=True)
#         post.setlist("keywords", ["test1", "test2"])
#         form = ScoreSetEditForm(post, instance=instance)
#         self.assertTrue(form.is_valid())
#         self.assertEqual(len(form.new_keywords()), 2)
#
#     def test_can_find_existing_keywords(self):
#         instance = ScoreSet.objects.create(experiment=self.experiment)
#         Keyword.objects.create(text="test1")
#         post = QueryDict('', mutable=True)
#         post.setlist("keywords", ["test1", "test2"])
#
#         form = ScoreSetEditForm(post, instance=instance)
#         self.assertTrue(form.is_valid())
#         self.assertEqual(len(form.new_keywords()), 1)
#         self.assertEqual(form.cleaned_data["keywords"].count(), 1)
#
#     def test_can_save_update(self):
#         instance = ScoreSet.objects.create(experiment=self.experiment)
#         post = QueryDict('', mutable=True)
#         post.setlist("keywords", ["test1", "test2"])
#
#         form = ScoreSetEditForm(post, instance=instance)
#         scs = form.save(commit=True)
#         self.assertEqual(Keyword.objects.count(), 2)
#         self.assertEqual(scs.keywords.count(), 2)
#
#     def test_form_save_removes_keywords_not_present_in_submission(self):
#         instance = ScoreSet.objects.create(experiment=self.experiment)
#         kw = Keyword.objects.create(text="test")
#         instance.keywords.add(kw)
#
#         post = QueryDict('', mutable=True)
#         post.setlist("keywords", ["test2"])
#
#         form = ScoreSetEditForm(post, instance=instance)
#         scs = form.save(commit=True)
#         self.assertEqual(Keyword.objects.count(), 2)
#         self.assertEqual(scs.keywords.count(), 1)
#         self.assertEqual(scs.keywords.all()[0].text, "test2")
#
#     def test_commit_false_does_not_update_keywords(self):
#         instance = ScoreSet.objects.create(experiment=self.experiment)
#         kw = Keyword.objects.create(text="test")
#         instance.keywords.add(kw)
#
#         post = QueryDict('', mutable=True)
#         post.setlist("keywords", ["test2"])
#
#         form = ScoreSetEditForm(post, instance=instance)
#         scs = form.save(commit=False)
#         self.assertEqual(Keyword.objects.count(), 1)
#         self.assertEqual(scs.keywords.count(), 1)
#         self.assertEqual(scs.keywords.all()[0].text, "test")
#
#         form.save_m2m()
#         self.assertEqual(Keyword.objects.count(), 2)
#         self.assertEqual(scs.keywords.count(), 1)
#         self.assertEqual(scs.keywords.all()[0].text, "test2")
#
#     def test_save_does_not_alter_other_fields(self):
#         instance = ScoreSet.objects.create(
#             experiment=self.experiment,
#             dataset_columns={
#                 constants.variant_score_data: [constants.hgvs_column, "score"],
#                 constants.variant_count_data: [constants.hgvs_column, "count"]
#             }
#         )
#         variant = Variant.objects.create(
#             scoreset=instance,
#             hgvs="test",
#             data={
#                 constants.variant_score_data: {
#                     constants.hgvs_column: "test", "score": 0.1},
#                 constants.variant_count_data: {
#                     constants.hgvs_column: "test", "count": 1.0},
#             }
#         )
#
#         post = QueryDict('', mutable=True)
#         post.setlist("keywords", ["test"])
#         form = ScoreSetEditForm(post, instance=instance)
#         instance = form.save(commit=True)
#         self.assertEqual(instance.variant_set.first(), variant)
#         self.assertEqual(instance.keywords.count(), 1)