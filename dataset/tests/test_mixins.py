from django.test import TestCase

from metadata.factories import (
    UniprotIdentifierFactory, RefseqIdentifierFactory,
    EnsemblIdentifierFactory
)

from ..models.experiment import Experiment
from ..models.scoreset import ScoreSet
from ..factories import ExperimentWithScoresetFactory, ScoreSetWithTargetFactory
from ..mixins import ExperimentSearchMixin, ScoreSetSearchMixin


class TestExperimentSearchMixin(TestCase):
    
    def setUp(self):
        self.factory = ExperimentWithScoresetFactory
        self.searcher = ExperimentSearchMixin()
        self.model_class = Experiment

    def test_can_filter_singular_target(self):
        obj1 = self.factory()
        target1 = obj1.children.first().get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.children.first().get_target()
        target2.name = 'STAT'
        target2.save()

        q = self.searcher.search_all(
            value_or_dict={"target": target1.get_name().lower()},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_filter_multiple_targets(self):
        obj1 = self.factory()
        target1 = obj1.children.first().get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.children.first().get_target()
        target2.name = 'MAP'
        target2.save()

        q = self.searcher.search_all(
            value_or_dict={"target": [
                target1.get_name(),
                target2.get_name(),
            ]},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)

    def test_can_AND_search(self):
        obj1 = self.factory()
        target1 = obj1.children.first().get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.children.first().get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.children.first().get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={
                "target": [
                    target1.get_name(),
                    target2.get_name(),
                ],
                'urn': obj1.urn
            },
            join_func=self.searcher.and_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_OR_search(self):
        obj1 = self.factory()
        target1 = obj1.children.first().get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.children.first().get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.children.first().get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={
                "target": [
                    target2.get_name().lower(),
                ],
                'urn': obj1.urn
            },
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_search_by_organism(self):
        obj1 = self.factory()
        obj2 = self.factory()

        genome1 = obj1.children.first().get_target().\
            get_reference_genomes().first()
        genome1.species_name = 'Human'
        genome1.save()

        genome2 = obj2.children.first().get_target().\
            get_reference_genomes().first()
        genome2.species_name = 'Chimp'
        genome2.save()
        
        q = self.searcher.search_all(
            value_or_dict={
                "organism": ["human"]
            },
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_genome_name(self):
        obj1 = self.factory()
        obj2 = self.factory()

        genome1 = obj1.children.first().get_target().\
            get_reference_genomes().first()
        genome1.short_name = 'Hg16'
        genome1.save()

        genome2 = obj2.children.first().get_target().\
            get_reference_genomes().first()
        genome2.short_name = 'Hg17'
        genome2.save()

        q = self.searcher.search_all(
            value_or_dict={'genome': 'hg16'},
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_genome_id(self):
        obj1 = self.factory()
        obj2 = None
        genome1 = obj1.children.first().get_target().\
            get_reference_genomes().first()

        break_ = False
        while not break_:
            obj2 = self.factory()
            genome2 = obj2.children.first().get_target().\
                get_reference_genomes().first()
            if genome1.get_identifier() != genome2.get_identifier():
                break_ = True

        q = self.searcher.search_all(
            value_or_dict={'genome': genome1.get_identifier()},
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_id(self):
        obj1 = self.factory()
        obj2 = self.factory()
        id_factories = [
            (UniprotIdentifierFactory, 'uniprot_id'),
            (RefseqIdentifierFactory, 'refseq_id'),
            (EnsemblIdentifierFactory, 'ensembl_id'),
        ]

        for factory, field in id_factories:
            id1 = factory()
            id2 = factory()
            while id1 == id2:
                id2 = factory()

            target1 = obj1.children.first().get_target()
            target2 = obj2.children.first().get_target()
            setattr(target1, field, id1)
            target1.save()
            setattr(target2, field, id2)
            target2.save()

            q = self.searcher.search_all(
                value_or_dict={field.replace('_id', ''): id1.identifier},
                join_func=self.searcher.or_join_qs
            )

            result = self.model_class.objects.filter(q)
            self.assertEqual(result.count(), 1)
            self.assertIn(obj1, result)
            self.assertNotIn(obj2, result)


class TestScoreSetSearchMixin(TestCase):

    def setUp(self):
        self.factory = ScoreSetWithTargetFactory
        self.searcher = ScoreSetSearchMixin()
        self.model_class = ScoreSet

    def test_can_filter_singular_target(self):
        obj1 = self.factory()
        target1 = obj1.get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.get_target()
        target2.name = 'MAP'
        target2.save()

        q = self.searcher.search_all(
            value_or_dict={"target": 'JAK'},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_filter_multiple_targets(self):
        obj1 = self.factory()
        target1 = obj1.get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={"target": [
                target1.get_name(),
                target2.get_name(),
            ]},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_AND_search(self):
        obj1 = self.factory()
        target1 = obj1.get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={
                "target": [
                    target1.get_name(),
                    target2.get_name(),
                ],
                'urn': obj1.urn
            },
            join_func=self.searcher.and_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_OR_search(self):
        obj1 = self.factory()
        target1 = obj1.get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={
                "target": [
                    target1.get_name(),
                    target2.get_name(),
                ],
                'urn': obj1.urn
            },
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_search_by_organism(self):
        obj1 = self.factory()
        obj2 = self.factory()

        genome1 = obj1.get_target().get_reference_genomes().first()
        genome1.species_name = 'Human'
        genome1.save()

        genome2 = obj2.get_target().get_reference_genomes().first()
        genome2.species_name = 'Chimp'
        genome2.save()

        q = self.searcher.search_all(
            value_or_dict={
                "organism": ["human"]
            },
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_genome_name(self):
        obj1 = self.factory()
        obj2 = self.factory()

        genome1 = obj1.get_target().get_reference_genomes().first()
        genome1.short_name = 'Hg16'
        genome1.save()

        genome2 = obj2.get_target().get_reference_genomes().first()
        genome2.short_name = 'Hg17'
        genome2.save()

        q = self.searcher.search_all(
            value_or_dict={'genome': 'hg16'},
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_genome_id(self):
        obj1 = self.factory()
        obj2 = None
        genome1 = obj1.get_target().get_reference_genomes().first()

        break_ = False
        while not break_:
            obj2 = self.factory()
            genome2 = obj2.get_target().get_reference_genomes().first()
            if genome1.get_identifier() != genome2.get_identifier():
                break_ = True

        q = self.searcher.search_all(
            value_or_dict={'genome': genome1.get_identifier()},
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_id(self):
        obj1 = self.factory()
        obj2 = self.factory()
        id_factories = [
            (UniprotIdentifierFactory, 'uniprot_id'),
            (RefseqIdentifierFactory, 'refseq_id'),
            (EnsemblIdentifierFactory, 'ensembl_id'),
        ]

        for factory, field in id_factories:
            id1 = factory()
            id2 = factory()
            while id1 == id2:
                id2 = factory()

            target1 = obj1.get_target()
            target2 = obj2.get_target()
            setattr(target1, field, id1)
            target1.save()
            setattr(target2, field, id2)
            target2.save()

            q = self.searcher.search_all(
                value_or_dict={field.replace('_id', ''): id1.identifier},
                join_func=self.searcher.or_join_qs
            )

            result = self.model_class.objects.filter(q)
            self.assertEqual(result.count(), 1)
            self.assertIn(obj1, result)
            self.assertNotIn(obj2, result)
