from unittest import mock

from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.shortcuts import reverse

from accounts.factories import UserFactory

from core.utilities import base_url

from genome.models import TargetGene

from main.models import Licence

from variant.factories import VariantFactory

from urn.validators import MAVEDB_SCORESET_URN_RE

from dataset import constants

from ..models.scoreset import default_dataset, ScoreSet, assign_public_urn
from ..factories import (
    ScoreSetFactory,
    ScoreSetWithTargetFactory,
    ExperimentFactory,
)
from ..utilities import publish_dataset


class TestScoreSet(TestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`ScoreSet`, representing an experiment with associated
    :py:class:`Variant` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """

    def test_new_is_assigned_all_permission_groups(self):
        self.assertEqual(Group.objects.count(), 0)
        _ = ScoreSetFactory()
        self.assertEqual(Group.objects.count(), 9)

    def test_deleted_deletes_all_permission_groups(self):
        obj = ScoreSetFactory()
        self.assertEqual(Group.objects.count(), 9)
        obj.delete()
        self.assertEqual(Group.objects.count(), 6)

    def test_cannot_create_with_duplicate_urn(self):
        obj = ScoreSetFactory()
        with self.assertRaises(IntegrityError):
            ScoreSetFactory(urn=obj.urn)

    def test_cannot_save_without_experiment(self):
        with self.assertRaises(IntegrityError):
            ScoreSetFactory(experiment=None)

    def test_gets_cc4_licence_by_default(self):
        obj = ScoreSetFactory()
        self.assertEqual(obj.licence, Licence.get_default())

    def test_scoreset_not_approved_and_private_by_default(self):
        scs = ScoreSet()
        self.assertFalse(scs.approved)
        self.assertTrue(scs.private)

    def test_cannot_delete_scoreset_with_variants(self):
        scs = ScoreSetFactory()
        _ = VariantFactory(scoreset=scs)
        with self.assertRaises(ProtectedError):
            scs.delete()

    def test_can_traverse_replaced_by_tree(self):
        scs_1 = ScoreSetFactory()
        scs_2 = ScoreSetFactory(experiment=scs_1.experiment, replaces=scs_1)
        scs_3 = ScoreSetFactory(experiment=scs_2.experiment, replaces=scs_2)
        self.assertEqual(scs_1.current_version, scs_3)
        self.assertEqual(scs_1.next_version, scs_2)
        self.assertEqual(scs_2.previous_version, scs_1)

    def test_has_replacement_returns_false_if_no_relationship_set(self):
        scs = ScoreSetFactory()
        self.assertFalse(scs.has_replacement)

    def test_replaces_returns_false_if_no_relationship_set(self):
        scs = ScoreSetFactory()
        self.assertFalse(scs.replaces)

    def test_has_replacement_returns_true_if_relationship_set(self):
        scs_1 = ScoreSetFactory()
        _ = ScoreSetFactory(experiment=scs_1.experiment, replaces=scs_1)
        self.assertTrue(scs_1.has_replacement)

    def test_replaces_returns_true_if_relationship_set(self):
        scs_1 = ScoreSetFactory()
        scs_2 = ScoreSetFactory(experiment=scs_1.experiment, replaces=scs_1)
        self.assertTrue(scs_2.replaces)

    def test_has_variants(self):
        scs = ScoreSetFactory()
        self.assertFalse(scs.has_variants)
        _ = VariantFactory(scoreset=scs)
        self.assertTrue(scs.has_variants)

    def test_delete_variants_resets_dataset_columns(self):
        scs = ScoreSetFactory()
        _ = VariantFactory(scoreset=scs)
        scs.delete_variants()
        scs.save()

        self.assertEqual(scs.dataset_columns, default_dataset())
        self.assertEqual(scs.variants.count(), 0)
        self.assertEqual(scs.last_child_value, 0)

    def test_can_traverse_public_replaced_by_tree(self):
        scs_1 = ScoreSetFactory(private=False)
        scs_2 = ScoreSetFactory(
            private=False, experiment=scs_1.experiment, replaces=scs_1
        )
        scs_3 = ScoreSetFactory(
            private=True, experiment=scs_2.experiment, replaces=scs_2
        )
        self.assertEqual(scs_1.current_public_version, scs_2)
        self.assertEqual(scs_2.current_public_version, scs_2)

    def test_next_public_version_returns_none_if_next_is_private(self):
        scs_1 = ScoreSetFactory(private=False)
        scs_2 = ScoreSetFactory(
            private=True, experiment=scs_1.experiment, replaces=scs_1
        )
        self.assertEqual(scs_1.next_public_version, None)
        self.assertEqual(scs_2.next_public_version, None)

    def test_next_public_version_returns_next_if_next_is_public(self):
        scs_1 = ScoreSetFactory(private=False)
        scs_2 = ScoreSetFactory(
            private=False, experiment=scs_1.experiment, replaces=scs_1
        )
        self.assertEqual(scs_1.next_public_version, scs_2)

    def test_previous_public_version_returns_none_if_previous_is_private(self):
        scs_1 = ScoreSetFactory(private=True)
        scs_2 = ScoreSetFactory(experiment=scs_1.experiment, replaces=scs_1)
        self.assertEqual(scs_1.previous_public_version, None)
        self.assertEqual(scs_2.previous_public_version, None)

    def test_previous_public_version_returns_previous_if_previous_is_public(
        self,
    ):
        scs_1 = ScoreSetFactory(private=False)
        scs_2 = ScoreSetFactory(
            private=True, experiment=scs_1.experiment, replaces=scs_1
        )
        scs_3 = ScoreSetFactory(experiment=scs_2.experiment, replaces=scs_2)
        self.assertEqual(scs_3.previous_public_version, scs_1)
        self.assertEqual(scs_2.previous_public_version, scs_1)

    def test_delete_cascades_to_target(self):
        scs = ScoreSetWithTargetFactory()
        self.assertEqual(TargetGene.objects.count(), 1)
        scs.delete()
        self.assertEqual(TargetGene.objects.count(), 0)

    def test_delete_does_not_delete_licence(self):
        scs = ScoreSetFactory()
        self.assertEqual(Licence.objects.count(), 1)
        scs.delete()
        self.assertEqual(Licence.objects.count(), 1)

    def test_delete_replaces_sets_field_to_none(self):
        scs_1 = ScoreSetFactory()
        scs_2 = ScoreSetFactory(replaces=scs_1)
        self.assertIsNotNone(scs_2.replaces)
        scs_1.delete()
        scs_2.refresh_from_db()
        self.assertIsNone(scs_2.replaces)

    def test_can_get_url(self):
        obj = ScoreSetFactory()
        self.assertEqual(
            obj.get_url(),
            base_url() + reverse("dataset:scoreset_detail", args=(obj.urn,)),
        )

    def test_primary_column_is_nt_when_nt_is_present(self):
        obj = ScoreSetFactory()
        VariantFactory(scoreset=obj, hgvs_nt="a")
        VariantFactory(scoreset=obj)
        self.assertEqual(obj.primary_hgvs_column, constants.hgvs_nt_column)

    def test_primary_column_is_pro_when_nt_is_not_present(self):
        obj = ScoreSetFactory()
        VariantFactory(scoreset=obj, hgvs_nt=None)
        self.assertEqual(obj.primary_hgvs_column, constants.hgvs_pro_column)

    def test_get_version_is_public_user_is_none(self):
        instance1 = ScoreSetFactory(private=False)
        instance2 = ScoreSetFactory(replaces=instance1, private=False)
        instance3 = ScoreSetFactory(replaces=instance2, private=True)
        self.assertEqual(
            instance1.get_version("next_version", "next_public_version"),
            instance1.next_public_version,
        )

    def test_get_version_is_returns_public_attr_result_if_attr_is_none(self):
        instance1 = ScoreSetFactory(private=False)
        self.assertEqual(
            instance1.get_version("next_version", "next_public_version"),
            instance1.next_public_version,
        )

    def test_get_version_returns_public_when_user_not_contributor_on_private_version(
        self,
    ):
        instance1 = ScoreSetFactory(private=False)
        instance2 = ScoreSetFactory(replaces=instance1, private=True)
        user = UserFactory()
        self.assertEqual(
            instance1.get_version("next_version", "next_public_version", user),
            instance1.next_public_version,
        )

    def test_get_version_returns_private_when_user_is_a_contributor(self):
        instance1 = ScoreSetFactory(private=False)
        instance2 = ScoreSetFactory(replaces=instance1, private=True)
        user = UserFactory()
        instance2.add_viewers(user)
        self.assertIsNotNone(instance1.next_version)
        self.assertEqual(
            instance1.get_version("next_version", "next_public_version", user),
            instance1.next_version,
        )

    @mock.patch.object(ScoreSet, "get_version")
    def test_get_next_version_calls_get_version_with_correct_args(self, patch):
        instance = ScoreSetFactory()
        instance.get_next_version()
        patch.assert_called_with(
            *("next_version", "next_public_version", None)
        )

    @mock.patch.object(ScoreSet, "get_version")
    def test_get_prev_version_calls_get_version_with_correct_args(self, patch):
        instance = ScoreSetFactory()
        instance.get_previous_version()
        patch.assert_called_with(
            *("previous_version", "previous_public_version", None)
        )

    @mock.patch.object(ScoreSet, "get_version")
    def test_get_curr_version_calls_get_version_with_correct_args(self, patch):
        instance = ScoreSetFactory()
        instance.get_current_version()
        patch.assert_called_with(
            *("current_version", "current_public_version", None)
        )

    def test_has_uniprot_metadata_returns_correct_boolean(self):
        instance = ScoreSetWithTargetFactory()
        target = instance.target
        self.assertTrue(instance.has_uniprot_metadata)

        target.uniprot_id = None
        target.save()
        instance.refresh_from_db()
        self.assertFalse(instance.has_uniprot_metadata)

    def test_has_protein_variants_returns_correct_boolean(self):
        instance = ScoreSetWithTargetFactory()

        v1 = VariantFactory(scoreset=instance)
        self.assertTrue(instance.has_protein_variants)

        v1.hgvs_pro = None
        v1.save()
        self.assertFalse(instance.has_protein_variants)


class TestAssignPublicUrn(TestCase):
    def setUp(self):
        self.factory = ScoreSetFactory
        self.private_parent = ExperimentFactory()
        self.public_parent = publish_dataset(ExperimentFactory())

    def test_assigns_public_urn(self):
        instance = self.factory(experiment=self.public_parent)
        instance = assign_public_urn(instance)
        self.assertIsNotNone(MAVEDB_SCORESET_URN_RE.fullmatch(instance.urn))
        self.assertTrue(instance.has_public_urn)

    def test_increments_parent_last_child_value(self):
        instance = self.factory(experiment=self.public_parent)
        self.assertEqual(instance.parent.last_child_value, 0)
        instance = assign_public_urn(instance)
        self.assertEqual(instance.parent.last_child_value, 1)

    def test_attr_error_parent_has_tmp_urn(self):
        instance = self.factory(experiment=self.private_parent)
        self.private_parent.private = False
        self.private_parent.save()
        with self.assertRaises(AttributeError):
            assign_public_urn(instance)

    def test_assigns_sequential_urns(self):
        instance1 = self.factory(experiment=self.public_parent)
        instance2 = self.factory(experiment=self.public_parent)
        instance1 = assign_public_urn(instance1)
        instance2 = assign_public_urn(instance2)
        self.assertEqual(int(instance1.urn[-1]), 1)
        self.assertEqual(int(instance2.urn[-1]), 2)

    def test_applying_twice_does_not_change_urn(self):
        instance = self.factory(experiment=self.public_parent)
        i1 = assign_public_urn(instance)
        i2 = assign_public_urn(instance)
        self.assertEqual(i1.urn, i2.urn)
