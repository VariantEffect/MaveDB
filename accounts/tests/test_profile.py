from django.test import TestCase, mock
from django.core import mail
from django.contrib.auth import get_user_model

from social_django.models import UserSocialAuth
from guardian.conf.settings import ANONYMOUS_USER_NAME

from accounts.factories import UserFactory

from core.tasks import send_mail

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset import factories

from ..models import Profile, user_is_anonymous
from ..permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_editor,
    assign_user_as_instance_viewer,
    remove_user_as_instance_admin,
    remove_user_as_instance_editor,
    remove_user_as_instance_viewer
)

User = get_user_model()


class TestUserProfile(TestCase):
    def setUp(self):
        self.exps_1 = ExperimentSet.objects.create()
        self.exps_2 = ExperimentSet.objects.create()
        self.exp_1 = Experiment.objects.create()
        self.exp_2 = Experiment.objects.create()
        self.scs_1 = ScoreSet.objects.create(experiment=self.exp_1)
        self.scs_2 = ScoreSet.objects.create(experiment=self.exp_2)

    def test_can_get_non_anonymous_profiles(self):
        bob = User.objects.create(username="bob", password="secretkey")
        anon = User.objects.get(username=ANONYMOUS_USER_NAME)
        self.assertFalse(user_is_anonymous(bob))
        self.assertTrue(user_is_anonymous(anon))

    def test_profile_gets_users_email_as_default(self):
        user = UserFactory()
        profile = user.profile
        profile.email = None
        profile.save()
        self.assertIsNone(user.profile.email)

    def test_name_methods_default_to_username(self):
        bob = User.objects.create(username="bob", password="secretkey")
        self.assertEqual(bob.profile.get_full_name(), "bob")
        self.assertEqual(bob.profile.get_short_name(), "bob")
        self.assertEqual(bob.profile.get_display_name(), "bob")

    def test_save_creates_user_profile(self):
        User.objects.create(username="bob", password="secretkey")
        self.assertEqual(len(Profile.non_anonymous_profiles()), 1)

    def test_can_get_full_name(self):
        bob = User.objects.create(
            username="bob", password="secretkey",
            first_name="daniel", last_name="smith"
        )
        self.assertEqual(bob.profile.get_full_name(), "Daniel Smith")

    def test_can_get_short_name(self):
        bob = User.objects.create(
            username="bob", password="secretkey",
            first_name="daniel", last_name="smith"
        )
        self.assertEqual(bob.profile.get_short_name(), "Smith, D")

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_send_email_uses_profile_by_email_by_default(self, patch):
        bob = User.objects.create(
            username="bob", password="secretkey",
            first_name="daniel", last_name="smith"
        )
        bob.profile.email = "email@email.com"
        bob.profile.save()
        bob.profile.email_user(message="hello", subject="None")
        
        patch.assert_called()
        send_mail.apply(**patch.call_args[1])
        
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [bob.profile.email])

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_send_email_uses_user_email_as_backup(self, patch):
        bob = User.objects.create(
            username="bob", password="secretkey",
            first_name="daniel", last_name="smith", email="bob@email.com"
        )
        bob.profile.email = None
        bob.profile.save()

        bob.profile.email_user(message="hello", subject="None")

        patch.assert_called()
        send_mail.apply(**patch.call_args[1])
        
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [bob.email])

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_email_user_sends_no_email_if_no_email_present(self, patch):
        bob = User.objects.create(
            username="bob", password="secretkey",
            first_name="daniel", last_name="smith",
            email="",
        )
        bob.profile.email = None
        bob.profile.save()
        bob.profile.email_user(message="hello", subject="None")
        patch.assert_not_called()

    # ----- ExperimentSets
    def test_can_get_all_experimentsets_user_is_admin_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.exps_1)
        assign_user_as_instance_editor(bob, self.exps_2)
        bobs_exps = bob.profile.administrator_experimentsets()
        self.assertEqual(len(bobs_exps), 1)
        self.assertEqual(bobs_exps[0], self.exps_1)

    def test_can_get_all_experimentsets_user_is_editor_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_editor(bob, self.exps_1)
        assign_user_as_instance_admin(bob, self.exps_2)
        bobs_exps = bob.profile.editor_experimentsets()
        self.assertEqual(len(bobs_exps), 1)
        self.assertEqual(bobs_exps[0], self.exps_1)

    def test_can_get_all_experimentsets_user_is_viewer_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_viewer(bob, self.exps_1)
        assign_user_as_instance_admin(bob, self.exps_2)
        bobs_exps = bob.profile.viewer_experimentsets()
        self.assertEqual(len(bobs_exps), 1)
        self.assertEqual(bobs_exps[0], self.exps_1)

    def test_public_experimentsets_filters_out_private(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.exps_1)
        assign_user_as_instance_admin(bob, self.exps_2)
        public = bob.profile.public_contributor_experimentsets()
        self.exps_1.private = False
        self.exps_1.save()
        self.assertEqual(len(public), 1)
        self.assertEqual(list(public)[0], self.exps_1)

    # ----- Experiments
    def test_can_get_all_experiments_user_is_admin_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.exp_1)
        assign_user_as_instance_editor(bob, self.exp_2)
        bobs_exp = bob.profile.administrator_experiments()
        self.assertEqual(len(bobs_exp), 1)
        self.assertEqual(bobs_exp[0], self.exp_1)

    def test_can_get_all_experiments_user_is_editor_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_editor(bob, self.exp_1)
        assign_user_as_instance_admin(bob, self.exp_2)
        bobs_exp = bob.profile.editor_experiments()
        self.assertEqual(len(bobs_exp), 1)
        self.assertEqual(bobs_exp[0], self.exp_1)

    def test_can_get_all_experiments_user_is_viewer_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_viewer(bob, self.exp_1)
        assign_user_as_instance_admin(bob, self.exp_2)
        bobs_exp = bob.profile.viewer_experiments()
        self.assertEqual(len(bobs_exp), 1)
        self.assertEqual(bobs_exp[0], self.exp_1)

    def test_public_experiments_filters_out_private(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.exp_1)
        assign_user_as_instance_admin(bob, self.exp_2)
        public = bob.profile.public_contributor_experiments()

        self.exp_1.private = False
        self.exp_1.save()

        self.assertEqual(len(public), 1)
        self.assertEqual(list(public)[0], self.exp_1)

    # ----- ScoreSets
    def test_can_get_all_scoresets_user_is_admin_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.scs_1)
        assign_user_as_instance_editor(bob, self.scs_2)
        bobs_scs = bob.profile.administrator_scoresets()
        self.assertEqual(len(bobs_scs), 1)
        self.assertEqual(bobs_scs[0], self.scs_1)

    def test_can_get_all_scoresets_user_is_editor_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_editor(bob, self.scs_1)
        assign_user_as_instance_admin(bob, self.scs_2)
        bobs_scs = bob.profile.editor_scoresets()
        self.assertEqual(len(bobs_scs), 1)
        self.assertEqual(bobs_scs[0], self.scs_1)

    def test_can_get_all_scoresets_user_is_viewer_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_viewer(bob, self.scs_1)
        assign_user_as_instance_admin(bob, self.scs_2)
        bobs_scs = bob.profile.viewer_scoresets()
        self.assertEqual(len(bobs_scs), 1)
        self.assertEqual(bobs_scs[0], self.scs_1)

    def test_public_scoresets_filters_out_private(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.scs_1)
        assign_user_as_instance_admin(bob, self.scs_2)
        public = bob.profile.public_contributor_scoresets()
        self.scs_1.private = False
        self.scs_1.save()
        self.assertEqual(len(public), 1)
        self.assertEqual(list(public)[0], self.scs_1)

    # ----- Empty values
    def test_empty_list_not_admin_on_anything(self):
        bob = User.objects.create(username="bob")
        self.assertEqual(len(bob.profile.administrator_scoresets()), 0)
        self.assertEqual(len(bob.profile.administrator_experimentsets()), 0)
        self.assertEqual(len(bob.profile.administrator_experiments()), 0)

    def test_empty_list_not_editor_on_anything(self):
        bob = User.objects.create(username="bob")
        self.assertEqual(len(bob.profile.editor_scoresets()), 0)
        self.assertEqual(len(bob.profile.editor_experimentsets()), 0)
        self.assertEqual(len(bob.profile.editor_experiments()), 0)

    def test_empty_list_not_viewer_on_anything(self):
        bob = User.objects.create(username="bob")
        self.assertEqual(len(bob.profile.viewer_scoresets()), 0)
        self.assertEqual(len(bob.profile.viewer_experimentsets()), 0)
        self.assertEqual(len(bob.profile.viewer_experiments()), 0)

    # ----- Remove user
    def test_can_remove_user_as_admin(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.exps_1)
        self.assertEqual(len(bob.profile.administrator_experimentsets()), 1)

        remove_user_as_instance_admin(bob, self.exps_1)
        self.assertEqual(len(bob.profile.administrator_experimentsets()), 0)

    def test_can_remove_user_as_editor(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_editor(bob, self.exps_1)
        self.assertEqual(len(bob.profile.editor_experimentsets()), 1)

        remove_user_as_instance_editor(bob, self.exps_1)
        self.assertEqual(len(bob.profile.editor_experimentsets()), 0)

    def test_can_remove_user_as_viewer(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_viewer(bob, self.exps_1)
        self.assertEqual(len(bob.profile.viewer_experimentsets()), 1)

        remove_user_as_instance_viewer(bob, self.exps_1)
        self.assertEqual(len(bob.profile.viewer_experimentsets()), 0)
    
    # ------ Group change
    @mock.patch('core.tasks.send_mail.apply_async')
    def test_notify_group_change_full_url_rendererd_in_template(self, patch):
        user = UserFactory()
        instance = factories.ExperimentFactory()
        user.profile.notify_user_group_change(
            instance, 'added', 'administrator')
        patch.assert_called()
        self.assertIn(
            instance.get_url(),
            patch.call_args[1]['kwargs']['message']
        )
        
    # --- Upload status
    @mock.patch('core.tasks.send_mail.apply_async')
    def test_renders_url_correctly(self, patch):
        user = UserFactory()
        instance = factories.ExperimentFactory()
        user.profile.notify_user_upload_status(True, instance)
        patch.assert_called()
        self.assertIn(
            instance.get_url(),
            patch.call_args[1]['kwargs']['message']
        )

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_delegates_correct_template_fail(self, patch):
        user = UserFactory()
        instance = factories.ExperimentSetFactory()
        user.profile.notify_user_upload_status(success=False, instance=instance)
        
        patch.assert_called()
        message = patch.call_args[1]['kwargs']['message']
        self.assertIn("could not be processed", message)

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_delegates_correct_template_success(self, patch):
        user = UserFactory()
        instance = factories.ExperimentSetFactory()
        user.profile.notify_user_upload_status(success=True, instance=instance)
    
        patch.assert_called()
        message = patch.call_args[1]['kwargs']['message']
        self.assertIn("has been successfully processed", message)
