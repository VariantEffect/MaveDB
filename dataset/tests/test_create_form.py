#
# from django.test import TestCase
# from django.core.exceptions import ValidationError
#
# from dataset.models import Experiment, ExperimentSet
# from dataset.forms import ExperimentForm
#
#
# class TestExperimentForm(TestCase):
#     """
#     Test that the `ExperimentForm` object is able to raise the appropriate
#     `ValidationError` on fields such as experimentset and wt_sequence.
#     """
#
#     def setUp(self):
#         self.experimentset = ExperimentSet.objects.create()
#
#     def make_test_data(self, target, wt_sequence, use_exps=False):
#         data = {
#             "target": target,
#             "wt_sequence": wt_sequence,
#             "experimentset": self.experimentset.pk if use_exps else None
#         }
#         return data
#
#     def test_can_create_form_and_save_new_instance(self):
#         form = ExperimentForm(
#             data=self.make_test_data(
#                 target="test", wt_sequence="atcg",
#                 use_exps=True
#             )
#         )
#         self.assertTrue(form.is_valid())
#         model = form.save()
#         self.assertEqual(Experiment.objects.count(), 1)
#         self.assertEqual(ExperimentSet.objects.count(), 1)
#
#     def test_not_valid_empty_target(self):
#         form = ExperimentForm(
#             data=self.make_test_data(
#                 target="", wt_sequence="atcg",
#                 use_exps=True
#             )
#         )
#         self.assertFalse(form.is_valid())
#
#     def test_not_valid_empty_wildtype(self):
#         form = ExperimentForm(
#             data=self.make_test_data(
#                 target="test", wt_sequence="",
#                 use_exps=True
#             )
#         )
#         self.assertFalse(form.is_valid())
#
#     def test_not_valid_null_target(self):
#         form = ExperimentForm(
#             data=self.make_test_data(
#                 target=None, wt_sequence="atcg",
#                 use_exps=True
#             )
#         )
#         self.assertFalse(form.is_valid())
#
#     def test_not_valid_null_wildtype(self):
#         form = ExperimentForm(
#             data=self.make_test_data(
#                 target="test", wt_sequence=None,
#                 use_exps=True
#             )
#         )
#         self.assertFalse(form.is_valid())
#
#     def test_not_valid_non_dna_wildtype(self):
#         form = ExperimentForm(
#             data=self.make_test_data(
#                 target="test", wt_sequence="adad",
#                 use_exps=True
#             )
#         )
#         self.assertFalse(form.is_valid())
#
#     def test_not_valid_experimentset_not_found(self):
#         data = self.make_test_data(target="test", wt_sequence="atcg")
#         data["experimentset"] = "blah"
#         form = ExperimentForm(data=data)
#         self.assertFalse(form.is_valid())
#
#     def test_can_create_new_external_accessions(self):
#         data = self.make_test_data(target="test", wt_sequence="atcg")
#         data["external_accessions"] = ["test"]
#         form = ExperimentForm(data=data)
#         instance = form.save(commit=True)
#         self.assertEqual(instance.external_accessions.count(), 1)
#
#     def test_can_create_new_target_organisms(self):
#         data = self.make_test_data(target="test", wt_sequence="atcg")
#         data["target_organism"] = "test"
#         form = ExperimentForm(data=data)
#         instance = form.save(commit=True)
#         self.assertEqual(instance.target_organism.count(), 1)
#
#     def test_can_create_new_keywords(self):
#         data = self.make_test_data(target="test", wt_sequence="atcg")
#         data["keywords"] = ["test"]
#         form = ExperimentForm(data=data)
#         instance = form.save(commit=True)
#         self.assertEqual(instance.keywords.count(), 1)
#
#     def test_only_save_one_target_org(self):
#         data = self.make_test_data(target="test", wt_sequence="atcg")
#         data['target'] = "brca1"
#         data['target_organism'] = ['test1', 'test2']
#         data['wt_sequence'] = "atcg"
#
#         form = ExperimentForm(data=data)
#         instance = form.save(commit=True)
#         self.assertEqual(instance.target_organism.count(), 1)
