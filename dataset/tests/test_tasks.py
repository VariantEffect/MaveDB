from django.test import TestCase, mock

from accounts.factories import UserFactory

from core.models import FailedTask

from variant.factories import generate_hgvs, make_data, VariantFactory

from dataset import constants
from dataset.models.scoreset import default_dataset, ScoreSet
from dataset.factories import ScoreSetFactory
from dataset.tasks import create_variants, publish_scoreset, BasePublish


class TestCreateVariantsTask(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.scoreset = ScoreSetFactory(
            dataset_columns={
                constants.count_columns: ['count'],
                constants.score_columns: ['score', 'sig', 'se']
            }
        )
        self.scoreset.save()
        self.hgvs = generate_hgvs()
        self.variants = {
            self.hgvs: {constants.hgvs_column: self.hgvs, 'data': make_data()}
        }

    def test_create_variants_resets_dataset_columns(self):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        ))
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.dataset_columns, default_dataset())

    @mock.patch('dataset.tasks.notify_user_upload_status.delay')
    def test_notifies_user_on_end(self, mock_patch):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
             base_url="",
            scoreset_urn=self.scoreset.urn,
        ))
        mock_patch.assert_called()

    def test_sets_status_to_success_on_success(self):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        ))
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.processing_state, constants.success)

    def test_on_failure_sets_status_to_failed(self):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        ))
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.processing_state, constants.failed)

    @mock.patch('dataset.tasks.notify_user_upload_status.delay')
    def test_notifies_user_on_fail(self, mock_patch):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        ))
        mock_patch.assert_called()
        
    def test_saves_on_fail(self):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        ))
        self.assertEqual(FailedTask.objects.count(), 1)
        
    def test_can_find_saved_task(self):
        # run twice
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        ))
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        ))
        self.assertEqual(FailedTask.objects.count(), 1)
        self.assertEqual(FailedTask.objects.first().failures, 2)


class TestPublishScoresetTask(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.scoreset = ScoreSetFactory(
            dataset_columns={
                constants.count_columns: ['count'],
                constants.score_columns: ['score', 'sig', 'se']
            }
        )
        self.scoreset.save()
        self.hgvs = generate_hgvs()
        self.variants = {
            self.hgvs: {constants.hgvs_column: self.hgvs, 'data': make_data()}
        }

    def test_propagates_modified(self):
        publish_scoreset.apply(kwargs=dict(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk, base_url=""))
        scoreset = ScoreSet.objects.first()
        self.assertEqual(scoreset.modified_by, self.user)
        self.assertEqual(scoreset.parent.modified_by, self.user)
        self.assertEqual(scoreset.parent.parent.modified_by, self.user)

    def test_propagates_public(self):
        publish_scoreset.apply(kwargs=dict(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk, base_url=""))
        scoreset = ScoreSet.objects.first()
        self.assertEqual(scoreset.private, False)
        self.assertEqual(scoreset.parent.private, False)
        self.assertEqual(scoreset.parent.parent.private, False)

    @mock.patch('core.tasks.email_admins.delay')
    def test_sends_admin_emails(self, mock_patch):
        publish_scoreset.apply(kwargs=dict(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk, base_url=""))
        mock_patch.assert_called()
        
    def test_publish_sets_public_urns(self):
        var = VariantFactory(scoreset=self.scoreset)
        self.assertFalse(var.has_public_urn)
        publish_scoreset.apply(kwargs=dict(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk, base_url=""))
        var.refresh_from_db()
        self.scoreset.refresh_from_db()
        self.assertTrue(var.has_public_urn)
        self.assertTrue(self.scoreset.has_public_urn)
        
    def test_on_failure_sets_status_to_failed(self):
        # Patch the task base class
        base = BasePublish()
        base.scoreset = self.scoreset
        base.user = self.user
        base.urn = self.scoreset.urn
        base.base_url = ""
        base.on_failure(
            exc=Exception("Test"), task_id='1', args=[], einfo=None, kwargs={})
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.processing_state, constants.failed)

    @mock.patch('dataset.tasks.notify_user_upload_status.delay')
    def test_notifies_user_on_fail(self, mock_patch):
        # Patch the task base class
        base = BasePublish()
        base.scoreset = self.scoreset
        base.user = self.user
        base.urn = self.scoreset.urn
        base.base_url = ""
        base.on_failure(
            exc=Exception("Test"), task_id='1', args=[], einfo=None, kwargs={})
        mock_patch.assert_called()
        
    def test_saves_on_fail(self):
        # Patch the task base class
        base = BasePublish()
        base.scoreset = self.scoreset
        base.user = self.user
        base.urn = self.scoreset.urn
        base.base_url = ""
        base.on_failure(
            exc=Exception("Test"), task_id='1', args=[], einfo=None, kwargs={})
        self.assertEqual(FailedTask.objects.count(), 1)
