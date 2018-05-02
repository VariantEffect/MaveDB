from django.test import TestCase

from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset.factories import (
    ScoreSetFactory, ExperimentFactory, ExperimentWithScoresetFactory,
    ScoreSetWithTargetFactory
)

from genome.factories import TargetGeneFactory

from metadata.factories import (
    RefseqIdentifierFactory,
    EnsemblIdentifierFactory,
    UniprotIdentifierFactory,
    GenomeIdentifierFactory,
    SraIdentifierFactory,
    DoiIdentifierFactory,
    PubmedIdentifierFactory,
)

from ..forms import (
    MetadataSearchForm,
    MetaIdentifiersSearchForm,
    TargetIdentifierSearchForm,
    GenomeSearchForm
)


class TestMetadataSearchForm(TestCase):

    def test_can_search_by_title(self):
        obj1 = ExperimentFactory(title='hello world')
        obj2 = ExperimentFactory(title='foo bar')

        data = {
            "title": obj1.title
        }
        form = MetadataSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_description(self):
        obj1 = ExperimentFactory(short_description='hello world')
        obj2 = ExperimentFactory(short_description='foo bar')

        data = {
            "description": obj1.get_description()
        }
        form = MetadataSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_method(self):
        obj1 = ExperimentFactory(method_text='hello world')
        obj2 = ExperimentFactory(method_text='foo bar')

        data = {
            "method_abstract": obj1.method_text
        }
        form = MetadataSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_abstract(self):
        obj1 = ExperimentFactory(abstract_text='hello world')
        obj2 = ExperimentFactory(abstract_text='foo bar')

        data = {
            "method_abstract": obj1.abstract_text
        }
        form = MetadataSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_method_abstract_searches_by_OR(self):
        obj1 = ExperimentFactory(abstract_text='hello world')
        obj2 = ExperimentFactory(method_text='hello world')
        obj3 = ExperimentFactory(method_text='foo bar')

        data = {
            "method_abstract": obj1.abstract_text.upper()
        }
        form = MetadataSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_search_by_keywords(self):
        obj1 = ExperimentFactory()
        kw1 = obj1.keywords.first()
        kw1.text = 'Hello\'s'
        kw1.save()

        obj2 = ExperimentFactory()
        kw2 = obj2.keywords.first()
        kw2.text = "'quoted, string'"
        kw2.save()

        obj3 = ExperimentFactory()
        kw3 = obj3.keywords.first()
        kw3.text = 'foobar'
        kw3.save()

        data = {"keywords": [kw1.text, kw2.text.upper()]}
        form = MetadataSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def can_filter_by_keywords_in_scoresets(self):
        obj1 = ExperimentWithScoresetFactory()
        kw1_obj1 = obj1.keywords.first()
        kw1_obj1.text = 'Protein'
        kw1_obj1.save()

        scs1 = obj1.children.first()
        kw1 = scs1.keywords.first()
        kw1.text = 'Kinase'
        kw1.save()

        obj2 = ExperimentWithScoresetFactory()
        kw1_obj2 = obj2.keywords.first()
        kw1_obj2.text = 'Apple'
        kw1_obj2.save()

        scs2 = obj2.children.first()
        kw2 = scs2.keywords.first()
        kw2.text = 'Orange'
        kw2.save()

        data = {"keywords": [kw1.text]}
        form = MetadataSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_multiple_fields(self):
        obj1 = ExperimentFactory(method_text='foobar')
        kw1 = obj1.keywords.first()
        kw1.text = 'Hello\'s'
        kw1.save()

        obj2 = ExperimentFactory()
        kw2 = obj2.keywords.first()
        kw2.text = 'hello\'s'
        kw2.save()

        obj3 = ExperimentFactory(method_text='There\'s a snake in muhhh boots')

        data = {"keywords": [kw1.text], 'method_abstract': obj1.method_text}
        form = MetadataSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)
        self.assertNotIn(obj3, result)


class TestMetaIdentifiersSearchForm(TestCase):

    factories = (
        ('sra_ids', "sra_ids", SraIdentifierFactory),
        ('doi_ids', "doi_ids", DoiIdentifierFactory),
        ('pubmed_ids', "pubmed_ids", PubmedIdentifierFactory),
    )

    def test_can_search_by_identifier(self):
        for (search_name, field_name, factory) in self.factories:
            obj1 = ExperimentFactory()
            getattr(obj1, field_name).clear()
            obj1.save()

            obj2 = ExperimentFactory()
            getattr(obj2, field_name).clear()
            obj2.save()

            obj3 = ExperimentFactory()
            getattr(obj3, field_name).clear()
            obj3.save()

            id_1 = factory()
            id_2 = factory()
            id_3 = factory()
            while id_1.identifier == id_2.identifier:
                id_2 = factory()
            while id_3.identifier == id_2.identifier or \
                    id_3.identifier == id_1.identifier:
                id_3 = factory()

            obj1.add_identifier(id_1)
            obj2.add_identifier(id_2)
            obj3.add_identifier(id_3)

            data = {search_name: [id_1.identifier, id_2.identifier.upper()]}
            form = MetaIdentifiersSearchForm(data=data)
            self.assertTrue(form.is_valid())

            q = form.make_filters(join=True)
            result = Experiment.objects.filter(q)
            self.assertEqual(result.count(), 2)
            self.assertIn(obj1, result)
            self.assertIn(obj2, result)
            self.assertNotIn(obj3, result)

            Experiment.objects.all().delete()


class TestTargetIdentifierSearchForm(TestCase):
    factories = (
        ('uniprot', "uniprot_id", UniprotIdentifierFactory),
        ('refseq', "refseq_id", RefseqIdentifierFactory),
        ('ensembl', "ensembl_id", EnsemblIdentifierFactory),
    )

    def test_can_search_by_name(self):
        obj1 = ExperimentFactory()
        scs1 = ScoreSetFactory(experiment=obj1)

        obj2 = ExperimentFactory()
        scs2 = ScoreSetFactory(experiment=obj2)

        obj3 = ExperimentFactory()
        scs3 = ScoreSetFactory(experiment=obj3)

        TargetGeneFactory(scoreset=scs1, name='JAK')
        TargetGeneFactory(scoreset=scs2, name='STAT')
        TargetGeneFactory(scoreset=scs3, name='BRCA1')

        data = {'target': ['jak', 'stat']}
        form = TargetIdentifierSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_search_by_identifier(self):
        for (search_name, field_name, factory) in self.factories:
            obj1 = ExperimentFactory()
            scs1 = ScoreSetFactory(experiment=obj1)

            obj2 = ExperimentFactory()
            scs2 = ScoreSetFactory(experiment=obj2)

            obj3 = ExperimentFactory()
            scs3 = ScoreSetFactory(experiment=obj3)

            id_1 = factory()
            id_2 = factory()
            id_3 = factory()
            while id_1.identifier == id_2.identifier:
                id_2 = factory()
            while id_3.identifier == id_2.identifier or\
                    id_3.identifier == id_1.identifier:
                id_3 = factory()

            TargetGeneFactory(scoreset=scs1, **{field_name: id_1})
            TargetGeneFactory(scoreset=scs2, **{field_name: id_2})
            TargetGeneFactory(scoreset=scs3, **{field_name: id_3})

            data = {search_name: [id_1.identifier, id_2.identifier.lower()]}
            form = TargetIdentifierSearchForm(data=data)
            self.assertTrue(form.is_valid())

            q = form.make_filters(join=True)
            result = Experiment.objects.filter(q)
            self.assertEqual(result.count(), 2)
            self.assertIn(obj1, result)
            self.assertIn(obj2, result)
            self.assertNotIn(obj3, result)

            ScoreSet.objects.all().delete()
            Experiment.objects.all().delete()


class TestGenomeSearchForm(TestCase):

    def test_can_search_by_assembly(self):
        obj1 = ExperimentWithScoresetFactory()
        obj2 = ExperimentWithScoresetFactory()

        g1 = obj1.get_targets().first().get_reference_genomes().first()
        g2 = obj2.get_targets().first().get_reference_genomes().first()
        while g1.genome_id.identifier == g2.genome_id.identifier:
            g2.genome_id = GenomeIdentifierFactory()
            g2.save()

        data = {'assembly': g1.genome_id.identifier}
        form = GenomeSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_genome_name(self):
        obj1 = ExperimentWithScoresetFactory()
        obj2 = ExperimentWithScoresetFactory()

        g1 = obj1.get_targets().first().get_reference_genomes().first()
        g2 = obj2.get_targets().first().get_reference_genomes().first()
        g1.short_name = 'HG16'
        g1.save()
        g2.short_name = 'HG18'
        g2.save()

        data = {'genome': g1.short_name}
        form = GenomeSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_species(self):
        obj1 = ExperimentWithScoresetFactory()
        obj2 = ExperimentWithScoresetFactory()

        g1 = obj1.get_targets().first().get_reference_genomes().first()
        g2 = obj2.get_targets().first().get_reference_genomes().first()
        g1.species_name = 'HUman'
        g1.save()
        g2.species_name = 'ChimP'
        g2.save()

        data = {'species': g1.species_name.lower()}
        form = GenomeSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q).distinct()
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_multiple(self):
        obj1 = ExperimentWithScoresetFactory()
        obj2 = ExperimentWithScoresetFactory()
        obj3 = ExperimentWithScoresetFactory()

        g1 = obj1.get_targets().first().get_reference_genomes().first()
        g2 = obj2.get_targets().first().get_reference_genomes().first()
        g3 = obj2.get_targets().first().get_reference_genomes().first()
        g1.short_name = 'HG16'
        g1.species_name = 'HUman'
        g1.save()
        g2.short_name = 'HG17'
        g2.species_name = 'HUman'
        g2.save()
        g3.short_name = 'HG16'
        g3.species_name = 'CHIMP'
        g3.save()

        data = {
            'assembly': g1.genome_id.identifier,
            'genome': g1.short_name.lower()
        }
        form = GenomeSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_search_hits_when_experiment_has_multiple_scoresets(self):
        obj1 = ExperimentWithScoresetFactory()
        obj2 = ExperimentWithScoresetFactory()

        # Extra scoreset for obj1 to see if scoresets are traversed properly
        # by the filter Q.
        ScoreSetWithTargetFactory(experiment=obj1)

        g1 = obj1.scoresets.all()[0].get_target().\
            get_reference_genomes().first()
        g2 = obj1.scoresets.all()[1].get_target().\
            get_reference_genomes().first()
        g3 = obj2.scoresets.all()[0].get_target().\
            get_reference_genomes().first()

        g1.short_name = 'hg16'
        g1.species_name = 'human'
        g1.save()
        g2.short_name = 'hg16'
        g2.species_name = 'chimp'
        g2.save()

        g3.short_name = 'hg16'
        g3.species_name = 'mouse'
        g3.save()

        data = {
            'species': ['chimp', 'human'],
            'genome': g1.short_name
        }
        form = GenomeSearchForm(data=data)
        self.assertTrue(form.is_valid())

        q = form.make_filters(join=True)
        result = Experiment.objects.filter(q).distinct()
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)
