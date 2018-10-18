from django.test import TestCase, mock

from accounts.factories import UserFactory
from accounts.models import Profile

from core.models import FailedTask

from variant.factories import generate_hgvs, make_data, VariantFactory

from dataset import constants
from dataset.models.scoreset import default_dataset, ScoreSet
from dataset.factories import ScoreSetFactory
from dataset.tasks import create_variants, publish_scoreset, \
    BasePublish, delete_instance, BaseDelete


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
        self.hgvs_nt = generate_hgvs(prefix='c')
        self.hgvs_pro = generate_hgvs(prefix='p')
        self.variants = {
            self.hgvs_nt: {
                constants.hgvs_nt_column: self.hgvs_nt,
                constants.hgvs_pro_column: self.hgvs_pro,
                'data': make_data()
            }
        }

    def test_create_variants_resets_dataset_columns(self):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            scoreset_urn=self.scoreset.urn,
        ))
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.dataset_columns, default_dataset())

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_notifies_user_on_success(self, mock_patch):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            scoreset_urn=self.scoreset.urn,
        ))
        mock_patch.assert_called()
        self.assertEqual(
            mock_patch.call_args_list[0][1]['kwargs']['recipient_list'],
            [self.user.profile.email]
        )

    def test_sets_status_to_success_on_success(self):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            scoreset_urn=self.scoreset.urn,
        ))
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.processing_state, constants.success)

    def test_on_failure_sets_status_to_failed(self):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
            scoreset_urn=self.scoreset.urn,
        ))
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.processing_state, constants.failed)

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_notifies_user_on_fail(self, mock_patch):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
            scoreset_urn=self.scoreset.urn,
        ))
        mock_patch.assert_called()
        self.assertEqual(
            mock_patch.call_args_list[0][1]['kwargs']['recipient_list'],
            [self.user.profile.email]
        )
        
    def test_saves_on_fail(self):
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
            scoreset_urn=self.scoreset.urn,
        ))
        self.assertEqual(FailedTask.objects.count(), 1)
        
    def test_can_find_saved_task(self):
        # run twice
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
            scoreset_urn=self.scoreset.urn,
        ))
        create_variants.apply(kwargs=dict(
            dataset_columns=default_dataset(),
            variants=list(self.variants), # expecting a dict
            user_pk=self.user.pk,
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
        self.hgvs_nt = generate_hgvs(prefix='c')
        self.hgvs_pro = generate_hgvs(prefix='p')
        self.variants = {
            self.hgvs_nt: {
                constants.hgvs_nt_column: self.hgvs_nt,
                constants.hgvs_pro_column: self.hgvs_pro,
                'data': make_data()
            }
        }

    def test_propagates_modified(self):
        publish_scoreset.apply(kwargs=dict(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk,))
        scoreset = ScoreSet.objects.first()
        self.assertEqual(scoreset.modified_by, self.user)
        self.assertEqual(scoreset.parent.modified_by, self.user)
        self.assertEqual(scoreset.parent.parent.modified_by, self.user)

    def test_propagates_public(self):
        publish_scoreset.apply(kwargs=dict(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk,))
        scoreset = ScoreSet.objects.first()
        self.assertEqual(scoreset.private, False)
        self.assertEqual(scoreset.parent.private, False)
        self.assertEqual(scoreset.parent.parent.private, False)

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_sends_admin_emails_on_success(self, mock_patch):
        user = UserFactory(is_superuser=True)
        publish_scoreset.apply(kwargs=dict(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk,))
        self.assertEqual(
            mock_patch.call_args_list[1][1]['kwargs']['recipient_list'],
            [user.profile.email]
        )
        self.assertEqual(
            mock_patch.call_args_list[0][1]['kwargs']['recipient_list'],
            [self.user.profile.email]
        )
        
    @mock.patch('core.tasks.send_mail.apply_async')
    def test_sends_user_email_on_success(self, mock_patch):
        publish_scoreset.apply(kwargs=dict(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk,))
        self.assertEqual(
            mock_patch.call_args_list[0][1]['kwargs']['recipient_list'],
            [self.user.profile.email]
        )
        
    def test_publish_sets_public_urns(self):
        var = VariantFactory(scoreset=self.scoreset)
        self.assertFalse(var.has_public_urn)
        publish_scoreset.apply(kwargs=dict(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk,))
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

    @mock.patch('core.tasks.send_mail.apply_async')
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
        self.assertEqual(
            mock_patch.call_args_list[0][1]['kwargs']['recipient_list'],
            [self.user.profile.email]
        )
        
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


class TestDeleteInstance(TestCase):
    def setUp(self):
        self.scoreset = ScoreSetFactory()
        self.user = UserFactory()

    @mock.patch.object(Profile, 'notify_user_delete_status')
    def test_sends_user_email_on_success(self, mock_patch):
        delete_instance.apply(kwargs=dict(
            urn=self.scoreset.urn, user_pk=self.user.pk, ))
        mock_patch.assert_called_with(**{'success': True,
                                         'urn': self.scoreset.urn})
        self.assertEqual(ScoreSet.objects.count(), 0)

    @mock.patch.object(Profile, 'notify_user_delete_status')
    def test_notifies_user_on_fail_when_deleting_parent_with_child(self, mock_patch):
        delete_instance.apply(kwargs=dict(
            urn=self.scoreset.parent.urn, user_pk=self.user.pk, ))
        mock_patch.assert_called_with(**{'success': False,
                                         'urn': self.scoreset.parent.urn})

    def test_on_failure_sets_status_to_success(self):
        exp = self.scoreset.parent
        exp.processing_state = constants.processing
        exp.save()
        delete_instance.apply(kwargs=dict(
            urn=self.scoreset.parent.urn, user_pk=self.user.pk, ))
        exp.refresh_from_db()
        self.assertEqual(exp.processing_state, constants.success)
