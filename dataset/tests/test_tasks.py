import pandas as pd
import numpy as np

from django.test import TestCase, mock

from accounts.factories import UserFactory
from accounts.models import Profile

from core.models import FailedTask

from variant.factories import generate_hgvs, VariantFactory

from dataset import constants
from dataset.models.scoreset import default_dataset, ScoreSet
from dataset.factories import ScoreSetFactory
from dataset.tasks import (
    create_variants,
    publish_scoreset,
    BaseDatasetTask,
    delete_instance,
    BasePublishTask,
)


class TestBaseDatasetTask(TestCase):
    def setUp(self):
        self.instance = ScoreSetFactory()
        self.user = UserFactory()

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_on_failure_sets_status_to_failed(self, patch):
        base = BaseDatasetTask()
        base.instance = self.instance
        base.user = self.user
        base.urn = self.instance.urn
        base.description = "do the thing {urn}"

        base.on_failure(
            exc=Exception("Test"), task_id="1", args=[], einfo=None, kwargs={}
        )
        patch.assert_called()
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.processing_state, constants.failed)

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_on_success_sets_status_to_success(self, patch):
        base = BaseDatasetTask()
        base.instance = self.instance
        base.user = self.user
        base.urn = self.instance.urn
        base.description = "do the thing {urn}"

        base.on_success(retval=self.instance, task_id="1", args=[], kwargs={})
        patch.assert_called()
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.processing_state, constants.success)

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_notifies_user_on_fail(self, mock_patch):
        base = BaseDatasetTask()
        base.instance = self.instance
        base.user = self.user
        base.urn = self.instance.urn
        base.description = "do the thing {urn}"
        description = base.description.format(urn=self.instance.urn)

        base.on_failure(
            exc=Exception("Test"), task_id="1", args=[], einfo=None, kwargs={}
        )
        mock_patch.assert_called_with(
            **{"success": False, "description": description, "task_id": "1"}
        )

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_notifies_user_on_success(self, mock_patch):
        base = BaseDatasetTask()
        base.instance = self.instance
        base.user = self.user
        base.urn = self.instance.urn
        base.description = "do the thing {urn}"
        description = base.description.format(urn=self.instance.urn)

        base.on_success(retval=self.instance, task_id="1", args=[], kwargs={})
        mock_patch.assert_called_with(
            **{"success": True, "description": description, "task_id": "1"}
        )

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_fail_creates_a_failedtask_instances(self, patch):
        base = BaseDatasetTask()
        base.instance = self.instance
        base.user = self.user
        base.urn = self.instance.urn
        base.description = "do the thing {urn}"

        base.on_failure(
            exc=Exception("Test"), task_id="1", args=[], einfo=None, kwargs={}
        )
        patch.assert_called()
        self.assertEqual(FailedTask.objects.count(), 1)


class TestCreateVariantsTask(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.scoreset = ScoreSetFactory()
        self.hgvs_nt = generate_hgvs(prefix="p")
        self.hgvs_tx = generate_hgvs(prefix="c")
        self.hgvs_pro = generate_hgvs(prefix="p")
        self.df_scores = pd.DataFrame(
            {
                constants.hgvs_nt_column: [self.hgvs_nt],
                constants.hgvs_pro_column: [self.hgvs_pro],
                constants.hgvs_tx_column: [self.hgvs_tx],
                "score": 1.1,
            }
        )
        self.df_counts = pd.DataFrame(
            {
                constants.hgvs_nt_column: [self.hgvs_nt],
                constants.hgvs_pro_column: [self.hgvs_pro],
                constants.hgvs_tx_column: [self.hgvs_tx],
                "counts": 10,
            }
        )
        self.dataset_columns = {
            constants.count_columns: ["count"],
            constants.score_columns: [constants.required_score_column],
        }
        self.index = constants.hgvs_nt_column

    def mock_kwargs(self, **kwargs):
        mock_kwargs = dict(
            user_pk=self.user.pk,
            scoreset_urn=self.scoreset.urn,
            dataset_columns=self.dataset_columns,
            scores_records=self.df_scores.to_json(orient="records"),
            counts_records=self.df_counts.to_json(orient="records"),
            index=self.index,
        )
        mock_kwargs.update(**kwargs)
        return mock_kwargs

    def test_converts_nan_hgvs_to_none(self):
        self.index = constants.hgvs_pro_column
        self.df_scores[constants.hgvs_nt_column] = np.NaN
        self.df_counts[constants.hgvs_nt_column] = np.NaN

        self.scoreset.dataset_columns = default_dataset()
        create_variants.run(**self.mock_kwargs())
        self.scoreset.refresh_from_db()
        self.assertIsNone(self.scoreset.variants.first().hgvs_nt)

    def test_create_variants_resets_dataset_columns(self):
        self.scoreset.dataset_columns = default_dataset()
        create_variants.run(**self.mock_kwargs())
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.dataset_columns, self.dataset_columns)

    def test_create_variants_sets_last_child_value_to_zero(self):
        self.scoreset.last_child_value = 100
        self.scoreset.save()
        create_variants.run(**self.mock_kwargs())
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.last_child_value, 1)


class TestPublishScoresetTask(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.scoreset = ScoreSetFactory()
        self.scoreset.save()

    def mock_kwargs(self):
        return dict(scoreset_urn=self.scoreset.urn, user_pk=self.user.pk)

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_resets_public_to_false_if_failed(self, patch):
        self.scoreset.private = False
        experiment = self.scoreset.parent
        experiment.private = False
        experimentset = self.scoreset.parent.parent
        experimentset.private = False

        experimentset.save()
        experiment.save()
        self.scoreset.save()

        base = BasePublishTask()
        base.instance = self.scoreset
        base.user = self.user
        base.urn = self.scoreset.urn
        base.description = "do the thing {urn}"

        base.on_failure(
            exc=Exception("Test"), task_id="1", args=[], einfo=None, kwargs={}
        )
        patch.assert_called()
        scoreset = ScoreSet.objects.first()
        self.assertTrue(scoreset.private)
        self.assertTrue(scoreset.parent.private)
        self.assertTrue(scoreset.parent.parent.private)

    def test_propagates_modified(self):
        publish_scoreset.run(**self.mock_kwargs())
        scoreset = ScoreSet.objects.first()
        self.assertEqual(scoreset.modified_by, self.user)
        self.assertEqual(scoreset.parent.modified_by, self.user)
        self.assertEqual(scoreset.parent.parent.modified_by, self.user)

    def test_propagates_public(self):
        publish_scoreset.run(**self.mock_kwargs())
        scoreset = ScoreSet.objects.first()
        self.assertEqual(scoreset.private, False)
        self.assertEqual(scoreset.parent.private, False)
        self.assertEqual(scoreset.parent.parent.private, False)

    def test_publish_assigns_new_public_urns(self):
        var = VariantFactory(scoreset=self.scoreset)
        self.assertFalse(var.has_public_urn)
        publish_scoreset.run(**self.mock_kwargs())
        var.refresh_from_db()
        self.scoreset.refresh_from_db()
        self.assertTrue(var.has_public_urn)
        self.assertTrue(self.scoreset.has_public_urn)


class TestDeleteInstance(TestCase):
    def setUp(self):
        self.scoreset = ScoreSetFactory()
        self.user = UserFactory()

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_on_failure_sets_status_to_previous_state(self, patch):
        exp = self.scoreset.parent
        exp.processing_state = constants.processing
        exp.save()

        delete_instance.apply(
            kwargs=dict(urn=self.scoreset.parent.urn, user_pk=self.user.pk)
        )
        patch.assert_called()
        exp.refresh_from_db()
        self.assertEqual(exp.processing_state, constants.processing)

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_on_success_sets_self_instance_to_none(self, patch):
        delete_instance.apply(
            kwargs=dict(urn=self.scoreset.urn, user_pk=self.user.pk)
        )
        patch.assert_called()
        self.assertIsNone(delete_instance.instance)

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_fails_if_deleting_public(self, patch):
        self.scoreset.private = False
        self.scoreset.save()
        delete_instance.apply(
            kwargs=dict(urn=self.scoreset.urn, user_pk=self.user.pk)
        )
        patch.assert_called()
        self.assertEqual(FailedTask.objects.count(), 1)

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_fails_if_deleting_with_public_urn(self, patch):
        publish_scoreset(user_pk=self.user.pk, scoreset_urn=self.scoreset.urn)
        delete_instance.apply(
            kwargs=dict(urn=self.scoreset.urn, user_pk=self.user.pk)
        )
        patch.assert_called()
        self.assertEqual(FailedTask.objects.count(), 1)

    @mock.patch.object(Profile, "notify_user_submission_status")
    def test_fails_if_deleting_non_scs_parent_with_children(self, patch):
        exp = self.scoreset.parent
        exp.processing_state = constants.processing
        exp.save()
        delete_instance.apply(
            kwargs=dict(urn=self.scoreset.parent.urn, user_pk=self.user.pk)
        )
        patch.assert_called()
        self.assertEqual(FailedTask.objects.count(), 1)
