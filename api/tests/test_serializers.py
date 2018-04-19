# from django.test import TestCase
#
# from accounts.factories import UserFactory
# from accounts.permissions import (
#     assign_user_as_instance_admin,
#     assign_user_as_instance_viewer
# )
#
# from genome.factories import IntervalFactory
#
# import dataset.constants as constants
# from dataset.factories import (
#     ExperimentFactory, ExperimentSetFactory, ScoreSetFactory
# )
#
# # from ..serializers import (
# #     ExperimentSerializer,
# #     ExperimentSetSerializer,
# #     ScoreSetSerializer,
# #     UserSerializer
# # )
#
#
# class TestExperimentSetSerializer(TestCase):
#     """
#     Tests that the serializer for an :class:`ExperimentSet` outputs the correct
#     json data.
#     """
#     def test_can_correctly_serialize_instance(self):
#         experiment = ExperimentFactory()
#         instance = experiment.experimentset
#
#         alice = UserFactory(username="alice")
#         bob = UserFactory(username="bob")
#         assign_user_as_instance_admin(alice, instance)
#         assign_user_as_instance_viewer(bob, instance)
#
#         experiment.publish(propagate=True)
#         experiment.save(save_parents=True)
#
#         serializer = ExperimentSetSerializer()
#         expected = {
#             "contributors": ["alice"],
#             "urn": instance.urn,
#             "contributor_experiments": [experiment.urn],
#             "model_type": instance.class_name()
#         }
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result)
#
#     def test_can_filter_out_private(self):
#         experiment = ExperimentFactory()
#         instance = experiment.experimentset
#
#         alice = UserFactory(username="alice")
#         bob = UserFactory(username="bob")
#         assign_user_as_instance_admin(alice, instance)
#         assign_user_as_instance_viewer(bob, instance)
#
#         serializer = ExperimentSetSerializer()
#         expected = {
#             "contributors": ["alice"],
#             "urn": instance.urn,
#             "contributor_experiments": [],
#             "model_type": instance.class_name()
#         }
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result)
#
#     def test_empty_json_object_not_found(self):
#         serializer = ExperimentSetSerializer()
#         expected = {}
#         result = serializer.serialize(10000)
#         self.assertEqual(expected, result)
#
#     def test_empty_list_no_experiments(self):
#         instance = ExperimentSetFactory()
#         serializer = ExperimentSetSerializer()
#         expected = []
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result['contributor_experiments'])
#
#     def test_can_serialize_queryset(self):
#         instances = [
#             ExperimentSetFactory(),
#             ExperimentSetFactory()
#         ]
#         serializer = ExperimentSetSerializer()
#         expected = {
#             "contributor_experimentsets": [
#                 {
#                     "contributors": [],
#                     "urn": instances[0].urn,
#                     "contributor_experiments": [],
#                     "model_type": instances[0].class_name()
#                 },
#                 {
#                     "contributors": [],
#                     "urn": instances[1].urn,
#                     "contributor_experiments": [],
#                     "model_type": instances[1].class_name()
#                 }
#             ]
#         }
#         result = serializer.serialize_set(instances)
#         self.assertEqual(expected, result)
#
#
# class TestExperimentSerializer(TestCase):
#     """
#     Tests that the serializer for an :class:`Experiment` outputs the correct
#     json data.
#     """
#     def setUp(self):
#         self.target = IntervalFactory().reference_map.get_target_gene()
#
#     def test_can_correctly_serialize_instance(self):
#         instance = ExperimentFactory()
#         scoreset_1 = ScoreSetFactory(experiment=instance)
#         self.target.scoreset = scoreset_1
#         self.target.save()
#
#         alice = UserFactory(username="alice")
#         bob = UserFactory(username="bob")
#         assign_user_as_instance_admin(alice, instance)
#         assign_user_as_instance_viewer(bob, instance)
#
#         scoreset_1.publish(propagate=True)
#         scoreset_1.save(save_parents=True)
#
#         serializer = ExperimentSerializer()
#         expected = {
#             "contributors": ["alice"],
#             "experimentset": instance.experimentset.urn,
#             "urn": instance.urn,
#             "contributor_scoresets": [scoreset_1.urn],
#             "model_type": instance.class_name(),
#             "keywords": [],
#             "doi_ids": {},
#             "sra_ids": {},
#             "pm_ids": {},
#             "targets": {self.target.get_name(): self.target.serialise()}
#         }
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result)
#
#     def test_can_filter_out_private_scoresets_and_target(self):
#         instance = ExperimentFactory()
#         scoreset_1 = ScoreSetFactory(experiment=instance)
#         self.target.scoreset = scoreset_1
#         self.target.save()
#
#         alice = UserFactory(username="alice")
#         bob = UserFactory(username="bob")
#         assign_user_as_instance_admin(alice, instance)
#         assign_user_as_instance_viewer(bob, instance)
#
#         serializer = ExperimentSerializer()
#         expected = {
#             "contributors": ["alice"],
#             "experimentset": instance.experimentset.urn,
#             "urn": instance.urn,
#             "contributor_scoresets": [],  # private and no permissions
#             "model_type": instance.class_name(),
#             "keywords": [],
#             "doi_ids": {},
#             "sra_ids": {},
#             "pm_ids": {},
#             "targets": {}  # assoicated with private scoreset
#         }
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result)
#
#     def test_empty_scoreset_list_no_scoresets(self):
#         instance = ExperimentFactory()
#         serializer = ExperimentSerializer()
#         expected = []
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result['contributor_scoresets'])
#
#     def test_empty_json_object_not_found(self):
#         serializer = ExperimentSerializer()
#         expected = {}
#         result = serializer.serialize(10000)
#         self.assertEqual(expected, result)
#
#     def test_returns_correct_scoresets(self):
#         instance = ExperimentFactory()
#         scoreset_1 = ScoreSetFactory(experiment=instance)
#         scoreset_2 = ScoreSetFactory()  # not associated
#
#         scoreset_1.publish(propagate=True)
#         scoreset_1.save(save_parents=True)
#
#         scoreset_2.publish(propagate=True)
#         scoreset_2.save(save_parents=True)
#
#         serializer = ExperimentSerializer()
#         expected = [scoreset_1.urn]
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result['contributor_scoresets'])
#
#     def test_can_serialize_queryset(self):
#         instances = [
#             ExperimentFactory(),
#             ExperimentFactory()
#         ]
#         serializer = ExperimentSerializer()
#         expected = {
#             "contributor_experiments": [
#                 {
#                     "contributors": [],
#                     "urn": instances[0].urn,
#                     "experimentset": instances[0].experimentset.urn,
#                     "contributor_scoresets": [],
#                     "model_type": instances[0].class_name(),
#                     "keywords": [],
#                     "doi_ids": {},
#                     "sra_ids": {},
#                     "pm_ids": {},
#                     "targets": {}
#                 },
#                 {
#                     "contributors": [],
#                     "urn": instances[1].urn,
#                     "experimentset": instances[1].experimentset.urn,
#                     "contributor_scoresets": [],
#                     "model_type": instances[1].class_name(),
#                     "keywords": [],
#                     "doi_ids": {},
#                     "sra_ids": {},
#                     "pm_ids": {},
#                     "targets": {}
#                 }
#             ]
#         }
#         result = serializer.serialize_set(instances)
#         self.assertEqual(expected, result)
#
#
# class TestScoreSetSerializer(TestCase):
#     """
#     Tests that the serializer for an :class:`ScoreSet` outputs the correct
#     json data.
#     """
#     def setUp(self):
#         self.target = IntervalFactory().reference_map.get_target_gene()
#
#     def test_can_serialize_minimal_example(self):
#         instance = ScoreSetFactory()
#         self.target.scoreset = instance
#         self.target.save()
#
#         expected = {
#             "urn": instance.urn,
#             "contributors": [],
#             "current_version": instance.urn,
#             "next_version": None,
#             "previous_version": None,
#             "licence": [
#                 instance.licence.short_name, instance.licence.link,
#             ],
#             "score_columns": [constants.required_score_column],
#             "count_columns": [],
#             "model_type": instance.class_name(),
#             "keywords": [],
#             "doi_ids": {},
#             "sra_ids": {},
#             "pm_ids": {},
#             'target': self.target.serialise(),
#         }
#         serializer = ScoreSetSerializer()
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result)
#
#     def test_empty_json_object_not_found(self):
#         serializer = ScoreSetSerializer()
#         expected = {}
#         result = serializer.serialize(10000)
#         self.assertEqual(expected, result)
#
#     def test_correct_scores_columns(self):
#         instance = ScoreSetFactory()
#         instance.dataset_columns = {
#             constants.score_columns: ["hgvs", "score"],
#             constants.count_columns: []
#         }
#         instance.save()
#         expected = ["hgvs", "score"]
#         serializer = ScoreSetSerializer()
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result["score_columns"])
#
#     def test_correct_counts_columns(self):
#         instance = ScoreSetFactory()
#         instance.dataset_columns = {
#             constants.score_columns: [],
#             constants.count_columns: ["hgvs", "counts"]
#         }
#         instance.save()
#         expected = ["hgvs", "counts"]
#         serializer = ScoreSetSerializer()
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result["count_columns"])
#
#     def test_current_version_traverses_and_links_to_newest(self):
#         instance_1 = ScoreSetFactory()
#         instance_2 = ScoreSetFactory(
#             experiment=instance_1.experiment, replaces=instance_1)
#         instance_3 = ScoreSetFactory(
#             experiment=instance_2.experiment, replaces=instance_2)
#
#         expected = instance_3.urn
#         serializer = ScoreSetSerializer()
#         result = serializer.serialize(instance_1.pk)
#         self.assertEqual(expected, result['current_version'])
#
#     def test_value_is_null_when_no_next_version(self):
#         instance = ScoreSetFactory()
#         expected = None
#         serializer = ScoreSetSerializer()
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result['next_version'])
#
#     def test_correct_next_version(self):
#         instance_1 = ScoreSetFactory()
#         instance_2 = ScoreSetFactory(
#             experiment=instance_1.experiment, replaces=instance_1)
#         expected = instance_2.urn
#         serializer = ScoreSetSerializer()
#         result = serializer.serialize(instance_1.pk)
#         self.assertEqual(expected, result['next_version'])
#
#     def test_value_is_null_when_no_previous_version(self):
#         instance = ScoreSetFactory()
#         serializer = ScoreSetSerializer()
#         expected = None
#         result = serializer.serialize(instance.pk)
#         self.assertEqual(expected, result['previous_version'])
#
#     def test_previous_version_is_none_when_no_it_does_not_replace_any_instance(self):
#         instance_1 = ScoreSetFactory()
#         instance_2 = ScoreSetFactory(
#             experiment=instance_1.experiment, replaces=instance_1)
#
#         serializer = ScoreSetSerializer()
#         result = serializer.serialize(instance_2.pk)
#         self.assertEqual(instance_1.urn, result['previous_version'])
#
#
# class TestUserSerializer(TestCase):
#     """
#     Tests that the serializer for an :class:`User` outputs the correct
#     json data.
#     """
#     def setUp(self):
#         self.alice = UserFactory(
#             username="alice", last_name='Ed', first_name="Alice")
#         self.bob = UserFactory(username="bob")
#
#     def test_can_serialize_minimal_example(self):
#         exps = ExperimentSetFactory()
#         exp = ExperimentFactory(experimentset=exps)
#         scs = ScoreSetFactory(experiment=exp)
#
#         assign_user_as_instance_admin(self.alice, exps)
#         assign_user_as_instance_admin(self.alice, exp)
#         assign_user_as_instance_admin(self.alice, scs)
#
#         serializer = UserSerializer()
#         result = serializer.serialize(self.alice.pk, filter_private=False)
#         expected = {
#             "username": "alice",
#             "first_name": "Alice",
#             "last_name": "Ed",
#             "contributor_experimentsets": [exps.urn],
#             "contributor_experiments": [exp.urn],
#             "contributor_scoresets": [scs.urn],
#         }
#         self.assertEqual(expected, result)
#
#     def test_empty_json_object_not_found(self):
#         serializer = UserSerializer()
#         expected = {}
#         result = serializer.serialize(10000)
#         self.assertEqual(expected, result)
#
#     def test_can_filter_out_private_exps_admin_instances(self):
#         instance_1 = ExperimentSetFactory()
#         instance_2 = ExperimentSetFactory()
#
#         instance_2.publish(propagate=True)
#         instance_2.save(save_parents=True)
#
#         assign_user_as_instance_admin(self.alice, instance_1)
#         assign_user_as_instance_admin(self.alice, instance_2)
#
#         serializer = UserSerializer()
#         result = serializer.serialize(self.alice.pk)
#         expected = [instance_2.urn]
#         self.assertEqual(expected, result["contributor_experimentsets"])
#
#     def test_can_filter_out_private_exp_admin_instances(self):
#         instance_1 = ExperimentFactory()
#         instance_2 = ExperimentFactory()
#
#         instance_2.publish(propagate=True)
#         instance_2.save(save_parents=True)
#
#         assign_user_as_instance_admin(self.alice, instance_1)
#         assign_user_as_instance_admin(self.alice, instance_2)
#
#         serializer = UserSerializer()
#         result = serializer.serialize(self.alice.pk)
#         expected = [instance_2.urn]
#         self.assertEqual(expected, result["contributor_experiments"])
#
#     def test_can_filter_out_private_scs_admin_instances(self):
#         instance_1 = ScoreSetFactory()
#         instance_2 = ScoreSetFactory()
#
#         instance_2.publish(propagate=True)
#         instance_2.save(save_parents=True)
#
#         assign_user_as_instance_admin(self.alice, instance_1)
#         assign_user_as_instance_admin(self.alice, instance_2)
#
#         serializer = UserSerializer()
#         result = serializer.serialize(self.alice.pk)
#         expected = [instance_2.urn]
#         self.assertEqual(expected, result["contributor_scoresets"])
#
#     def test_only_show_admin_experimentsets(self):
#         instance_1 = ExperimentSetFactory()
#         instance_2 = ExperimentSetFactory()
#
#         assign_user_as_instance_viewer(self.alice, instance_1)
#         assign_user_as_instance_admin(self.alice, instance_2)
#
#         serializer = UserSerializer()
#         result = serializer.serialize(self.alice.pk, False)
#         expected = [instance_2.urn]
#         self.assertEqual(expected, result["contributor_experimentsets"])
#
#     def test_only_show_admin_experiments(self):
#         instance_1 = ExperimentFactory()
#         instance_2 = ExperimentFactory()
#
#         assign_user_as_instance_viewer(self.alice, instance_1)
#         assign_user_as_instance_admin(self.alice, instance_2)
#
#         serializer = UserSerializer()
#         result = serializer.serialize(self.alice.pk, False)
#         expected = [instance_2.urn]
#         self.assertEqual(expected, result["contributor_experiments"])
#
#     def test_only_show_admin_scoresets(self):
#         instance_1 = ScoreSetFactory()
#         instance_2 = ScoreSetFactory()
#
#         assign_user_as_instance_viewer(self.alice, instance_1)
#         assign_user_as_instance_admin(self.alice, instance_2)
#
#         serializer = UserSerializer()
#         result = serializer.serialize(self.alice.pk, False)
#         expected = [instance_2.urn]
#         self.assertEqual(expected, result["contributor_scoresets"])
