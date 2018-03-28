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
# class TestVariant(TransactionTestCase):
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
#         self.scs_1 = ScoreSet.objects.create(experiment=self.exp)
#         self.scs_2 = ScoreSet.objects.create(experiment=self.exp)
#
#         self.hgvs_1 = "c.45C>G"
#         self.hgvs_2 = "c.1A>T"
#         self.var_accession_11 = "SCSVAR000001A.1.1"
#         self.var_accession_12 = "SCSVAR000001A.1.2"
#         self.var_accession_21 = "SCSVAR000001A.2.1"
#         self.var_accession_22 = "SCSVAR000001A.2.2"
#
#     def test_can_create_minimal_variant(self):
#         Variant.objects.create(scoreset=self.scs_1, hgvs=self.hgvs_1)
#         var = Variant.objects.all()[0]
#         self.assertEqual(var.accession, self.var_accession_11)
#         self.assertEqual(var.scoreset, self.scs_1)
#
#     def test_autoassign_accession_in_variant(self):
#         Variant.objects.create(scoreset=self.scs_1, hgvs=self.hgvs_1)
#         Variant.objects.create(scoreset=self.scs_1, hgvs=self.hgvs_2)
#
#         var_1 = Variant.objects.all()[0]
#         var_2 = Variant.objects.all()[1]
#         self.assertEqual(var_1.accession, self.var_accession_11)
#         self.assertEqual(var_2.accession, self.var_accession_12)
#
#     def test_cannot_create_variant_with_duplicate_accession(self):
#         Variant.objects.create(
#             scoreset=self.scs_1,
#             hgvs=self.hgvs_1
#         )
#         with self.assertRaises(IntegrityError):
#             Variant.objects.create(
#                 accession=self.var_accession_11,
#                 hgvs=self.hgvs_1,
#                 scoreset=self.scs_1
#             )
#
#     def test_cannot_save_without_scoreset(self):
#         with self.assertRaises(IntegrityError):
#             Variant.objects.create(
#                 accession=self.var_accession_11,
#                 hgvs=self.hgvs_1
#             )
#         with self.assertRaises(IntegrityError):
#             Variant.objects.create(hgvs=self.hgvs_1)
#
#     def test_cannot_save_without_hgvs(self):
#         with self.assertRaises(IntegrityError):
#             Variant.objects.create(
#                 scoreset=self.scs_1
#             )
#
#     def test_validation_error_json_no_scores_key(self):
#         var = Variant.objects.create(
#             scoreset=self.scs_1,
#             hgvs=self.hgvs_1,
#             data={"not scores": {}, COUNTS_KEY: {}}
#         )
#         with self.assertRaises(ValidationError):
#             var.full_clean()
#
#     def test_validation_error_json_no_counts_key(self):
#         var = Variant.objects.create(
#             scoreset=self.scs_1,
#             hgvs=self.hgvs_1,
#             data={SCORES_KEY: {}, "not counts": {}}
#         )
#         with self.assertRaises(ValidationError):
#             var.full_clean()
#
#     def test_variants_sorted_by_most_recent(self):
#         date_1 = datetime.date.today()
#         date_2 = datetime.date.today() + datetime.timedelta(days=1)
#         Variant.objects.create(
#             scoreset=self.scs_1,
#             hgvs=self.hgvs_1,
#             creation_date=date_1
#         )
#         Variant.objects.create(
#             scoreset=self.scs_1,
#             hgvs=self.hgvs_1,
#             creation_date=date_2
#         )
#         self.assertEqual(
#             self.var_accession_12, Variant.objects.all()[0].accession)
#
#     def test_new_variant_has_todays_date_by_default(self):
#         Variant.objects.create(
#             scoreset=self.scs_1,
#             hgvs=self.hgvs_1,
#         )
#         var = Variant.objects.all()[0]
#         self.assertEqual(var.creation_date, datetime.date.today())
