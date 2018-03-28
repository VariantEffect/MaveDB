# import datetime
#
# from django.db import IntegrityError
# from django.contrib.auth.models import Group
# from django.core.exceptions import ValidationError
# from django.test import TransactionTestCase
# from django.db.models import ProtectedError
#
# from metadata.models import (
#     Keyword, SraIdentifier, DoiIdentifier, PubmedIdentifier
# )
# from variant.models import Variant
# from ..models import Experiment, ExperimentSet, ScoreSet
# import dataset.constants as constants
#
#
# class TestScoreSet(TransactionTestCase):
#     """
#     The purpose of this unit test is to test that the database model
#     :py:class:`ScoreSet`, representing an experiment with associated
#     :py:class:`Variant` objects. We will test correctness of creation,
#     validation, uniqueness, queries and that the appropriate errors are raised.
#     """
#
#     reset_sequences = True
#
#     def setUp(self):
#         self.target = "target"
#         self.wt_seq = "ATCG"
#         self.exp = Experiment.objects.create(
#             target=self.target,
#             wt_sequence=self.wt_seq
#         )
#         self.exp_accession = "EXP000001A"
#         self.scs_accession_1 = "SCS000001A.1"
#         self.scs_accession_2 = "SCS000001A.2"
#
#     def test_can_create_minimal_scoreset(self):
#         scs = ScoreSet.objects.create(experiment=self.exp)
#         self.assertEqual(scs.accession, self.scs_accession_1)
#         self.assertEqual(scs.experiment.accession, self.exp_accession)
#
#     def test_publish_updates_published_and_last_edit_dates(self):
#         scs = ScoreSet.objects.create(experiment=self.exp)
#         scs.publish()
#         self.assertEqual(scs.publish_date, datetime.date.today())
#         self.assertEqual(scs.last_edit_date, datetime.date.today())
#
#     def test_publish_updates_private_to_false(self):
#         scs = ScoreSet.objects.create(experiment=self.exp)
#         scs.publish()
#         self.assertFalse(scs.private)
#
#     def test_can_remove_keywords_during_update(self):
#         scs = ScoreSet.objects.create(experiment=self.exp)
#         kw1 = Keyword.objects.create(text="test1")
#         kw2 = Keyword.objects.create(text="test2")
#         scs.keywords.add(kw1)
#         scs.update_keywords([kw2])
#         self.assertEqual(scs.keywords.count(), 1)
#         self.assertEqual(scs.keywords.all()[0], kw2)
#
#     def test_scoreset_assigned_all_permission_groups(self):
#         scs = ScoreSet.objects.create(experiment=self.exp)
#         self.assertEqual(Group.objects.count(), 9)  # Counting parents as well
#
#     def test_autoassign_accession_in_scoreset(self):
#         ScoreSet.objects.create(experiment=self.exp)
#         ScoreSet.objects.create(experiment=self.exp)
#
#         scs_1 = ScoreSet.objects.all()[0]
#         scs_2 = ScoreSet.objects.all()[1]
#         self.assertEqual(scs_1.accession, self.scs_accession_1)
#         self.assertEqual(scs_2.accession, self.scs_accession_2)
#
#     def test_cannot_create_scoreset_with_duplicate_accession(self):
#         ScoreSet.objects.create(experiment=self.exp)
#         with self.assertRaises(IntegrityError):
#             ScoreSet.objects.create(
#                 accession=self.scs_accession_1,
#                 experiment=self.exp
#             )
#
#     def test_cannot_save_without_experiment(self):
#         with self.assertRaises(IntegrityError):
#             ScoreSet.objects.create()
#
#     def test_validation_error_json_no_scores_key(self):
#         scs = ScoreSet.objects.create(
#             experiment=self.exp,
#             dataset_columns={"not scores": [], COUNTS_KEY: []}
#         )
#         with self.assertRaises(ValidationError):
#             scs.full_clean()
#
#     def test_validation_error_json_no_counts_key(self):
#         scs = ScoreSet.objects.create(
#             experiment=self.exp,
#             dataset_columns={SCORES_KEY: [], "not counts": []}
#         )
#         with self.assertRaises(ValidationError):
#             scs.full_clean()
#
#     def test_validation_error_json_unexpected_keys(self):
#         scs = ScoreSet.objects.create(
#             experiment=self.exp,
#             dataset_columns={
#                 SCORES_KEY: [], COUNTS_KEY: [], "extra": [], "jumbo": []
#             }
#         )
#         with self.assertRaises(ValidationError):
#             scs.full_clean()
#
#     def test_validation_error_json_value_not_list(self):
#         scs = ScoreSet.objects.create(
#             experiment=self.exp,
#             dataset_columns={SCORES_KEY: 1, COUNTS_KEY: 2}
#         )
#         with self.assertRaises(ValidationError):
#             scs.full_clean()
#
#     def test_validation_error_json_list_not_strings(self):
#         scs = ScoreSet.objects.create(
#             experiment=self.exp,
#             dataset_columns={SCORES_KEY: [1], COUNTS_KEY: [1]}
#         )
#         with self.assertRaises(ValidationError):
#             scs.full_clean()
#
#     def test_validation_error_json_list_empty(self):
#         scs = ScoreSet.objects.create(
#             experiment=self.exp,
#             dataset_columns={SCORES_KEY: [], COUNTS_KEY: [1]}
#         )
#         with self.assertRaises(ValidationError):
#             scs.full_clean()
#
#     def test_scoresets_sorted_by_most_recent(self):
#         date_1 = datetime.date.today()
#         date_2 = datetime.date.today() + datetime.timedelta(days=1)
#         scs_1 = ScoreSet.objects.create(
#             experiment=self.exp,
#             creation_date=date_1)
#         scs_2 = ScoreSet.objects.create(
#             experiment=self.exp,
#             creation_date=date_2)
#         self.assertEqual(
#             self.scs_accession_2, ScoreSet.objects.all()[0].accession)
#
#     def test_new_scoreset_has_todays_date_by_default(self):
#         ScoreSet.objects.create(experiment=self.exp)
#         scs = ScoreSet.objects.all()[0]
#         self.assertEqual(scs.creation_date, datetime.date.today())
#
#     def test_scoreset_not_approved_and_private_by_default(self):
#         ScoreSet.objects.create(experiment=self.exp)
#         scs = ScoreSet.objects.all()[0]
#         self.assertFalse(scs.approved)
#         self.assertTrue(scs.private)
#
#     def test_scoreset_cannot_validate_negative_last_used_suffix(self):
#         with self.assertRaises(ValidationError):
#             ScoreSet.objects.create(
#                 experiment=self.exp,
#                 last_used_suffix=-1
#             ).full_clean()
#
#     def test_cannot_delete_scoreset_with_variants(self):
#         scs = ScoreSet.objects.create(experiment=self.exp)
#         var = Variant.objects.create(
#             scoreset=scs,
#             hgvs="hgvs",
#         )
#         with self.assertRaises(ProtectedError):
#             scs.delete()
#
#     def test_delete_does_not_rollback_variant_accession(self):
#         scs = ScoreSet.objects.create(experiment=self.exp)
#         Variant.objects.create(scoreset=scs, hgvs="hgvs")
#         var = Variant.objects.create(scoreset=scs, hgvs="hgvs")
#         var.delete()
#         var = Variant.objects.create(scoreset=scs, hgvs="hgvs")
#         self.assertEqual(var.accession[-1], '3')
#
#     def test_can_associate_valid_variant(self):
#         scs = ScoreSet.objects.create(
#             experiment=self.exp,
#             dataset_columns={SCORES_KEY: ['score'], COUNTS_KEY: ['count']}
#         )
#         var = Variant.objects.create(
#             scoreset=scs, hgvs="hgvs",
#             data={SCORES_KEY: {'score': 1}, COUNTS_KEY: {'count': 1}}
#         )
#         scs.validate_variant_data(var)  # should pass
#
#     def test_cannot_associate_variant_with_nonmatching_data_columns(self):
#         scs = ScoreSet.objects.create(
#             experiment=self.exp,
#             dataset_columns={SCORES_KEY: ['score'], COUNTS_KEY: ['count']}
#         )
#         var = Variant.objects.create(
#             scoreset=scs, hgvs="hgvs",
#             data={
#                 SCORES_KEY: {'score': 1, 'SE': 1},
#                 COUNTS_KEY: {'count': 1}
#             }
#         )
#         with self.assertRaises(ValueError):
#             scs.validate_variant_data(var)
#
#     def test_has_counts_dataset_return_false_when_COUNTS_KEY_is_empty_list(self):
#         scs = ScoreSet.objects.create(
#             experiment=self.exp,
#             dataset_columns={SCORES_KEY: ['score'], COUNTS_KEY: []}
#         )
#         self.assertFalse(scs.has_counts_dataset())
#
#     def test_can_traverse_replaced_by_tree(self):
#         scs_1 = ScoreSet.objects.create(
#             experiment=self.exp,
#         )
#         scs_2 = ScoreSet.objects.create(
#             experiment=self.exp, replaces=scs_1
#         )
#         scs_3 = ScoreSet.objects.create(
#             experiment=self.exp, replaces=scs_2
#         )
#         self.assertEqual(scs_1.get_latest_version(), scs_3)
#
#     def test_get_replaced_by(self):
#         scs_1 = ScoreSet.objects.create(
#             experiment=self.exp,
#         )
#         scs_2 = ScoreSet.objects.create(
#             experiment=self.exp, replaces=scs_1
#         )
#         self.assertEqual(scs_1.get_replaced_by(), scs_2)
#         self.assertEqual(scs_2.get_replaced_by(), None)
#
#     def test_approved_bit_propagates(self):
#         scs_1 = ScoreSet.objects.create(experiment=self.exp)
#         self.assertEqual(scs_1.experiment.approved, False)
#         self.assertEqual(scs_1.experiment.experimentset.approved, False)
#         scs_1.approved = True
#         scs_1.save()
#         self.assertEqual(scs_1.experiment.approved, True)
#         self.assertEqual(scs_1.experiment.experimentset.approved, True)