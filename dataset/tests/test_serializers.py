from django.test import TestCase

from .. import constants
from ..factories import ExperimentFactory, ExperimentSetFactory, ScoreSetFactory
from ..serializers import ExperimentSetSerializer, ExperimentSerializer, ScoreSetSerializer


class TestExperimentSetSerializer(TestCase):

    def test_private_experiments_hidden(self):
        experimentset = ExperimentSetFactory(private=False)
        ExperimentFactory(experimentset=experimentset, private=True)
        data = ExperimentSetSerializer(experimentset).data
        self.assertEqual(data['experiments'], [])

    def test_public_experiments_shown(self):
        experimentset = ExperimentSetFactory(private=False)
        exp = ExperimentFactory(experimentset=experimentset, private=False)
        data = ExperimentSetSerializer(experimentset).data
        self.assertEqual(data['experiments'], [exp.urn])


class TestExperimentSerializer(TestCase):

    def test_private_scoresets_hidden(self):
        experiment = ExperimentFactory(private=False)
        ScoreSetFactory(experiment=experiment, private=True)
        data = ExperimentSerializer(experiment).data
        self.assertEqual(data['scoresets'], [])

    def test_public_scoresets_shown(self):
        experiment = ExperimentFactory(private=False)
        scs = ScoreSetFactory(experiment=experiment, private=False)
        data = ExperimentSerializer(experiment).data
        self.assertEqual(data['scoresets'], [scs.urn])


class TestScoreSetSerializer(TestCase):

    def test_current_version_shows_only_latest_public_version(self):
        scs_1 = ScoreSetFactory()
        scs_2 = ScoreSetFactory(
            private=False,
            experiment=scs_1.experiment,
            replaces=scs_1
        )
        scs_3 = ScoreSetFactory(
            private=True,
            experiment=scs_2.experiment,
            replaces=scs_2
        )

        data = ScoreSetSerializer(scs_1).data
        self.assertEqual(data['current_version'], scs_2.urn)

    def test_next_version_is_self_if_next_version_is_private(self):
        scs_1 = ScoreSetFactory(private=False)
        scs_2 = ScoreSetFactory(
            private=True,
            experiment=scs_1.experiment,
            replaces=scs_1
        )
        data = ScoreSetSerializer(scs_1).data
        self.assertEqual(data['current_version'], scs_1.urn)

    def test_previous_version_is_none_if_previous_version_is_private(self):
        scs_1 = ScoreSetFactory(private=True)
        scs_2 = ScoreSetFactory(
            private=True,
            experiment=scs_1.experiment,
            replaces=scs_1
        )
        scs_3 = ScoreSetFactory(
            private=True,
            experiment=scs_2.experiment,
            replaces=scs_2
        )

        data = ScoreSetSerializer(scs_3).data
        self.assertEqual(data['previous_version'], None)

    def test_previous_version_skips_private_versions(self):
        scs_1 = ScoreSetFactory(private=False)
        scs_2 = ScoreSetFactory(
            private=True,
            experiment=scs_1.experiment,
            replaces=scs_1
        )
        scs_3 = ScoreSetFactory(
            private=True,
            experiment=scs_2.experiment,
            replaces=scs_2
        )

        data = ScoreSetSerializer(scs_3).data
        self.assertEqual(data['previous_version'], scs_1.urn)

    def test_columns_contains_hgvs(self):
        scs = ScoreSetFactory(private=False)
        data = ScoreSetSerializer(scs).data
        self.assertIn(constants.hgvs_nt_column, data['score_columns'])
        self.assertIn(constants.hgvs_pro_column, data['score_columns'])
        
        self.assertIn(constants.hgvs_nt_column, data['count_columns'])
        self.assertIn(constants.hgvs_pro_column, data['count_columns'])