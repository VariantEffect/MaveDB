from django.test import TestCase

from metadata import models as meta_models

from genome.models import TargetGene

from variant.models import Variant
from variant.factories import VariantFactory

from .. import models
from ..factories import (
    ExperimentSetFactory,
    ExperimentWithScoresetFactory,
    ScoreSetWithTargetFactory,
)

from ..utilities import (
    delete_instance, delete_experiment, delete_scoreset, delete_experimentset
)


class TestDeleteInstance(TestCase):

    def test_delegates_to_correct_method(self):
        delete_instance(ExperimentSetFactory())
        self.assertEqual(models.experimentset.ExperimentSet.objects.count(), 0)

        delete_instance(ExperimentWithScoresetFactory())
        self.assertEqual(models.experiment.Experiment.objects.count(), 0)

        delete_instance(ScoreSetWithTargetFactory())
        self.assertEqual(models.scoreset.ScoreSet.objects.count(), 0)


class TestDataSetDelete(TestCase):

    def test_does_not_delete_keywords(self):
        obj = ExperimentSetFactory()
        self.assertEqual(meta_models.Keyword.objects.count(), 1)
        delete_instance(obj)
        self.assertEqual(meta_models.Keyword.objects.count(), 1)

    def test_does_not_delete_pubmed_ids(self):
        obj = ExperimentSetFactory()
        self.assertEqual(meta_models.PubmedIdentifier.objects.count(), 1)
        delete_instance(obj)
        self.assertEqual(meta_models.PubmedIdentifier.objects.count(), 1)

    def test_does_not_delete_doi_ids(self):
        obj = ExperimentSetFactory()
        self.assertEqual(meta_models.DoiIdentifier.objects.count(), 1)
        delete_instance(obj)
        self.assertEqual(meta_models.DoiIdentifier.objects.count(), 1)

    def test_does_not_delete_sra_ids(self):
        obj = ExperimentSetFactory()
        self.assertEqual(meta_models.SraIdentifier.objects.count(), 1)
        delete_instance(obj)
        self.assertEqual(meta_models.SraIdentifier.objects.count(), 1)


class TestDeleteExperimentSet(TestCase):

    def test_deletes_experiments(self):
        exps = ExperimentSetFactory()
        ExperimentWithScoresetFactory(experimentset=exps)
        self.assertEqual(models.experiment.Experiment.objects.count(), 1)
        self.assertEqual(models.experimentset.ExperimentSet.objects.count(), 1)
        delete_experimentset(exps)
        self.assertEqual(models.experiment.Experiment.objects.count(), 0)
        self.assertEqual(models.experimentset.ExperimentSet.objects.count(), 0)

    def test_type_error_wrong_type(self):
        with self.assertRaises(TypeError):
            delete_experimentset(ScoreSetWithTargetFactory())


class TestDeleteExperiment(TestCase):

    def test_deletes_scoresets(self):
        exp = ExperimentWithScoresetFactory()
        self.assertEqual(models.experiment.Experiment.objects.count(), 1)
        self.assertEqual(models.scoreset.ScoreSet.objects.count(), 1)
        delete_experiment(exp)
        self.assertEqual(models.experiment.Experiment.objects.count(), 0)
        self.assertEqual(models.scoreset.ScoreSet.objects.count(), 0)

    def test_does_not_delete_parent(self):
        exp = ExperimentWithScoresetFactory()
        delete_experiment(exp)
        self.assertEqual(models.experimentset.ExperimentSet.objects.count(), 1)

    def test_type_error_wrong_type(self):
        with self.assertRaises(TypeError):
            delete_experiment(ScoreSetWithTargetFactory())


class TestDeleteScoreSet(TestCase):

    def test_deletes_variants(self):
        scs = ScoreSetWithTargetFactory()
        VariantFactory(scoreset=scs)
        self.assertEqual(models.scoreset.ScoreSet.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)
        delete_scoreset(scs)
        self.assertEqual(models.scoreset.ScoreSet.objects.count(), 0)
        self.assertEqual(Variant.objects.count(), 0)

    def test_deletes_target(self):
        scs = ScoreSetWithTargetFactory()
        self.assertEqual(models.scoreset.ScoreSet.objects.count(), 1)
        self.assertEqual(TargetGene.objects.count(), 1)
        delete_scoreset(scs)
        self.assertEqual(models.scoreset.ScoreSet.objects.count(), 0)
        self.assertEqual(TargetGene.objects.count(), 0)

    def test_does_not_delete_parents(self):
        scs = ScoreSetWithTargetFactory()
        self.assertEqual(models.experiment.Experiment.objects.count(), 1)
        self.assertEqual(models.experimentset.ExperimentSet.objects.count(), 1)
        delete_scoreset(scs)
        self.assertEqual(models.experiment.Experiment.objects.count(), 1)
        self.assertEqual(models.experimentset.ExperimentSet.objects.count(), 1)

    def test_type_error_wrong_type(self):
        with self.assertRaises(TypeError):
            delete_scoreset(ExperimentSetFactory())