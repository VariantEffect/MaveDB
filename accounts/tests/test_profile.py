
from django.test import TestCase
from django.contrib.auth import get_user_model

from guardian.conf.settings import ANONYMOUS_USER_NAME

from experiment.models import ExperimentSet, Experiment
from scoreset.models import ScoreSet

from ..models import Profile, user_is_anonymous
from ..permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_contributor,
    assign_user_as_instance_viewer,
    remove_user_as_instance_admin,
    remove_user_as_instance_contributor,
    remove_user_as_instance_viewer,
    instances_for_user_with_group_permission
)

User = get_user_model()


class TestUserProfile(TestCase):

    def setUp(self):
        self.exps_1 = ExperimentSet.objects.create()
        self.exps_2 = ExperimentSet.objects.create()
        self.exp_1 = Experiment.objects.create(
            target="test1", wt_sequence='atcg'
        )
        self.exp_2 = Experiment.objects.create(
            target="test1", wt_sequence='atcg'
        )
        self.scs_1 = ScoreSet.objects.create(experiment=self.exp_1)
        self.scs_2 = ScoreSet.objects.create(experiment=self.exp_2)

    def test_can_get_non_anonymous_profiles(self):
        bob = User.objects.create(username="bob", password="secretkey")
        anon = User.objects.get(username=ANONYMOUS_USER_NAME)
        self.assertFalse(user_is_anonymous(bob))
        self.assertTrue(user_is_anonymous(anon))

    def test_can_get_full_name(self):
        bob = User.objects.create(
            username="bob", password="secretkey",
            first_name="daniel", last_name="smith"
        )
        self.assertEqual(
            bob.profile.get_full_name(), "Daniel Smith"
        )

    def test_can_get_short_name(self):
        bob = User.objects.create(
            username="bob", password="secretkey",
            first_name="daniel", last_name="smith"
        )
        self.assertEqual(
            bob.profile.get_short_name(), "Smith, D"
        )

    def test_name_methods_default_to_username(self):
        bob = User.objects.create(
            username="bob", password="secretkey"
        )
        self.assertEqual(
            bob.profile.get_full_name(), "bob"
        )
        self.assertEqual(
            bob.profile.get_short_name(), "bob"
        )

    def test_can_create_user_profile(self):
        bob = User.objects.create(username="bob", password="secretkey")
        self.assertEqual(len(Profile.non_anonymous_profiles()), 1)

    def test_cannot_create_user_profile_twice(self):
        bob = User.objects.create(username="bob", password="secretkey")
        bob.save()  # send another save signal
        self.assertEqual(len(Profile.non_anonymous_profiles()), 1)

    def test_can_get_all_experimentsets_user_is_admin_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.exps_1)
        assign_user_as_instance_contributor(bob, self.exps_2)
        bobs_exps = bob.profile.administrator_experimentsets()
        self.assertEqual(len(bobs_exps), 1)
        self.assertEqual(bobs_exps[0], self.exps_1)

    def test_can_get_all_experimentsets_user_is_contrib_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_contributor(bob, self.exps_1)
        assign_user_as_instance_admin(bob, self.exps_2)
        bobs_exps = bob.profile.contributor_experimentsets()
        self.assertEqual(len(bobs_exps), 1)
        self.assertEqual(bobs_exps[0], self.exps_1)

    def test_can_get_all_experimentsets_user_is_viewer_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_viewer(bob, self.exps_1)
        assign_user_as_instance_admin(bob, self.exps_2)
        bobs_exps = bob.profile.viewer_experimentsets()
        self.assertEqual(len(bobs_exps), 1)
        self.assertEqual(bobs_exps[0], self.exps_1)

    def test_can_get_all_experiments_user_is_admin_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.exp_1)
        assign_user_as_instance_contributor(bob, self.exp_2)
        bobs_exp = bob.profile.administrator_experiments()
        self.assertEqual(len(bobs_exp), 1)
        self.assertEqual(bobs_exp[0], self.exp_1)

    def test_can_get_all_experimentsets_user_is_contrib_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_contributor(bob, self.exp_1)
        assign_user_as_instance_admin(bob, self.exp_2)
        bobs_exp = bob.profile.contributor_experiments()
        self.assertEqual(len(bobs_exp), 1)
        self.assertEqual(bobs_exp[0], self.exp_1)

    def test_can_get_all_experimentsets_user_is_viewer_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_viewer(bob, self.exp_1)
        assign_user_as_instance_admin(bob, self.exp_2)
        bobs_exp = bob.profile.viewer_experiments()
        self.assertEqual(len(bobs_exp), 1)
        self.assertEqual(bobs_exp[0], self.exp_1)

    def test_can_get_all_scoresets_user_is_admin_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(bob, self.scs_1)
        assign_user_as_instance_contributor(bob, self.scs_2)
        bobs_scs = bob.profile.administrator_scoresets()
        self.assertEqual(len(bobs_scs), 1)
        self.assertEqual(bobs_scs[0], self.scs_1)

    def test_can_get_all_scoresets_user_is_contrib_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_contributor(bob, self.scs_1)
        assign_user_as_instance_admin(bob, self.scs_2)
        bobs_scs = bob.profile.contributor_scoresets()
        self.assertEqual(len(bobs_scs), 1)
        self.assertEqual(bobs_scs[0], self.scs_1)

    def test_can_get_all_scoresets_user_is_viewer_on(self):
        bob = User.objects.create(username="bob")
        assign_user_as_instance_viewer(bob, self.scs_1)
        assign_user_as_instance_admin(bob, self.scs_2)
        bobs_scs = bob.profile.viewer_scoresets()
        self.assertEqual(len(bobs_scs), 1)
        self.assertEqual(bobs_scs[0], self.scs_1)

    def test_empty_list_not_admin_on_anything(self):
        bob = User.objects.create(username="bob")
        self.assertEqual(len(bob.profile.administrator_scoresets()), 0)
        self.assertEqual(len(bob.profile.administrator_experimentsets()), 0)
        self.assertEqual(len(bob.profile.administrator_experiments()), 0)

    def test_empty_list_not_contributor_on_anything(self):
        bob = User.objects.create(username="bob")
        self.assertEqual(len(bob.profile.contributor_scoresets()), 0)
        self.assertEqual(len(bob.profile.contributor_experimentsets()), 0)
        self.assertEqual(len(bob.profile.contributor_experiments()), 0)

    def test_empty_list_not_viewer_on_anything(self):
        bob = User.objects.create(username="bob")
        self.assertEqual(len(bob.profile.viewer_scoresets()), 0)
        self.assertEqual(len(bob.profile.viewer_experimentsets()), 0)
        self.assertEqual(len(bob.profile.viewer_experiments()), 0)
