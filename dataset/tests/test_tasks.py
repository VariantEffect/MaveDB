from django.test import TestCase, mock
from django.core import mail
from django.shortcuts import reverse

from accounts.factories import UserFactory

from variant.factories import generate_hgvs, make_data, VariantFactory

from dataset import constants
from dataset.models.scoreset import default_dataset, ScoreSet
from dataset.factories import ScoreSetFactory
from dataset.tasks import (
    create_variants, publish_scoreset, notify_user_upload_status
)


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
        create_variants(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            publish=False,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        )
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.dataset_columns, default_dataset())

    @mock.patch('dataset.tasks.notify_user_upload_status.delay')
    def test_notifies_user_on_start(self, mock_patch):
        create_variants(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            publish=False,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        )
        self.assertEqual(mock_patch.call_args_list[0][1]['step'], 'start')

    @mock.patch('dataset.tasks.notify_user_upload_status.delay')
    def test_notifies_user_on_end(self, mock_patch):
        create_variants(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            publish=False,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        )
        self.assertEqual(mock_patch.call_args_list[1][1]['step'], 'end')

    def test_sets_status_to_success_on_success(self):
        create_variants(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            publish=False,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        )
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.processing_state, constants.success)

    def test_on_failure_sets_status_to_failed(self):
        create_variants.on_failure(
            exc=None, task_id=1, args=[], einfo=None,
            kwargs=dict(
                user_pk=self.user.pk,
                base_url="",
                scoreset_urn=self.scoreset.urn,
            )
        )
        self.scoreset.refresh_from_db()
        self.assertEqual(self.scoreset.processing_state, constants.failed)

    @mock.patch('dataset.tasks.notify_user_upload_status.delay')
    def test_notifies_user_on_fail(self, mock_patch):
        create_variants.on_failure(
            exc=None, task_id=1, args=[], einfo=None,
            kwargs=dict(
                user_pk=self.user.pk,
                base_url="",
                scoreset_urn=self.scoreset.urn,
            )
        )
        mock_patch.assert_called()

    def test_publish_sets_public_urns(self):
        create_variants(
            dataset_columns=default_dataset(),
            variants=self.variants,
            user_pk=self.user.pk,
            publish=True,
            base_url="",
            scoreset_urn=self.scoreset.urn,
        )
        self.scoreset.refresh_from_db()
        self.assertTrue(self.scoreset.has_public_urn)
        self.assertTrue(self.scoreset.variants.first().has_public_urn)


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
        publish_scoreset(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk, base_url="")
        scoreset = ScoreSet.objects.first()
        self.assertEqual(scoreset.modified_by, self.user)
        self.assertEqual(scoreset.parent.modified_by, self.user)
        self.assertEqual(scoreset.parent.parent.modified_by, self.user)

    def test_propagates_public(self):
        publish_scoreset(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk, base_url="")
        scoreset = ScoreSet.objects.first()
        self.assertEqual(scoreset.private, False)
        self.assertEqual(scoreset.parent.private, False)
        self.assertEqual(scoreset.parent.parent.private, False)

    @mock.patch('core.tasks.email_admins.delay')
    def test_sends_admin_emails(self, mock_patch):
        publish_scoreset(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk, base_url="")
        mock_patch.assert_called()
        
    def test_publish_sets_public_urns(self):
        var = VariantFactory(scoreset=self.scoreset)
        self.assertFalse(var.has_public_urn)
        publish_scoreset(
            scoreset_urn=self.scoreset.urn, user_pk=self.user.pk, base_url="")
        var.refresh_from_db()
        self.scoreset.refresh_from_db()
        self.assertTrue(var.has_public_urn)
        self.assertTrue(self.scoreset.has_public_urn)


class TestNotifyUserTask(TestCase):

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

    def test_renders_url_correctly(self):
        notify_user_upload_status(
            self.user.pk,
            self.scoreset.urn, step='start', base_url="http://base")
        expected = "http://base" + \
                   reverse("dataset:scoreset_detail", args=(self.scoreset.urn,))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(expected, mail.outbox[0].body)

    def test_delegates_correct_template_start(self):
        notify_user_upload_status(
            self.user.pk,
            self.scoreset.urn, step='start', base_url="http://base")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("being processed", mail.outbox[0].body)

    def test_delegates_correct_template_end(self):
        notify_user_upload_status(
            self.user.pk,
            self.scoreset.urn, step='end', base_url="http://base")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("has been processed", mail.outbox[0].body)
