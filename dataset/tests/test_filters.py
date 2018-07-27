from django.test import TestCase, RequestFactory

from main.models import Licence

from accounts.factories import UserFactory

from metadata import factories as meta_factories
from genome import factories as genome_factories

from .. import factories, filters, models, utilities


class TestDatasetModelFilter(TestCase):
    def setUp(self):
        self.user1 = UserFactory(first_name='Alice', last_name='Mare')
        self.user2 = UserFactory(first_name='David', last_name='Davidson')
        self.instance1 = factories.ExperimentSetFactory()
        self.instance2 = factories.ExperimentSetFactory()
        self.instance1.private = False
        self.instance2.private = False
        self.instance1.save()
        self.instance2.save()
        
    def test_filters_out_private_by_default(self):
        self.instance1.private = True
        self.instance2.private = True
        self.instance1.save()
        self.instance2.save()
        f = filters.ExperimentSetFilterModel(
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertEqual(f.qs.count(), 0)

    def test_search_by_urn(self):
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.URN: self.instance1.urn},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_title(self):
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.TITLE: self.instance1.title},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
    def test_search_by_description(self):
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.DESCRIPTION:
                      self.instance1.short_description},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
    def test_search_by_abstract(self):
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.ABSTRACT:
                      self.instance1.abstract_text[
                      0:len(self.instance1.abstract_text)//2]},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
    def test_search_by_method(self):
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.METHOD:
                      self.instance1.method_text[
                      0:len(self.instance1.method_text)//2]},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
    def test_search_by_doi(self):
        self.instance1.doi_ids.clear()
        self.instance2.doi_ids.clear()
        
        id1 = meta_factories.DoiIdentifierFactory(
            identifier='10.1016/j.cels.2018.01.015')
        id2 = meta_factories.DoiIdentifierFactory(
            identifier='10.1016/j.jmb.2018.02.009')
        self.instance1.doi_ids.add(id1)
        self.instance2.doi_ids.add(id2)
        
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.DOI:
                      self.instance1.doi_ids.first().identifier},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_sra(self):
        self.instance1.sra_ids.clear()
        self.instance2.sra_ids.clear()
    
        id1 = meta_factories.SraIdentifierFactory(identifier='SRX3407687')
        id2 = meta_factories.SraIdentifierFactory(identifier='SRX3407686')
        self.instance1.sra_ids.add(id1)
        self.instance2.sra_ids.add(id2)
    
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.SRA:
                      self.instance1.sra_ids.first().identifier},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_pubmed(self):
        self.instance1.pubmed_ids.clear()
        self.instance2.pubmed_ids.clear()
    
        id1 = meta_factories.PubmedIdentifierFactory(identifier='25075907')
        id2 = meta_factories.PubmedIdentifierFactory(identifier='20711194')
        self.instance1.pubmed_ids.add(id1)
        self.instance2.pubmed_ids.add(id2)
    
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.PUBMED:
                      self.instance1.pubmed_ids.first().identifier},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_keywords(self):
        self.instance1.keywords.clear()
        self.instance2.keywords.clear()
    
        id1 = meta_factories.KeywordFactory(text='learning')
        id2 = meta_factories.KeywordFactory(text='machine learning')
        self.instance1.keywords.add(id1)
        self.instance2.keywords.add(id2)
    
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.KEYWORD:
                      self.instance1.keywords.first().text},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertIn(self.instance2, f.qs.all())  # icontains
    
    def test_search_by_first_name_returns_contributor_instances(self):
        self.instance1.add_administrators(self.user1)
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.FIRST_NAME: self.user1.first_name},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
    def test_search_by_last_name_returns_contributor_instances(self):
        self.instance1.add_administrators(self.user1)
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.LAST_NAME: self.user1.last_name},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
    def test_search_by_username_returns_contributor_instances(self):
        self.instance1.add_administrators(self.user1)
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.USERNAME: self.user1.username},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
    def test_search_by_display_name_returns_contributor_instances(self):
        self.instance1.add_administrators(self.user1)
        f = filters.ExperimentSetFilterModel(
            data={filters.DatasetModelFilter.DISPLAY_NAME:
                      self.user1.profile.get_display_name()},
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
    def test_searching_multiple_fields_joins_results_by_AND(self):
        # No results since the two querysets are disjoint
        f = filters.ExperimentSetFilterModel(
            data={
                filters.DatasetModelFilter.TITLE: self.instance1.title,
                filters.DatasetModelFilter.DESCRIPTION:
                    self.instance2.short_description,
            },
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertNotIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
        # Should return first instance only
        f = filters.ExperimentSetFilterModel(
            data={
                filters.DatasetModelFilter.TITLE: self.instance1.title,
                filters.DatasetModelFilter.DESCRIPTION:
                    self.instance1.short_description,
            },
            queryset=models.experimentset.ExperimentSet.objects.all(),
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
        
    def test_returns_private_if_user_is_authenticated(self):
        self.instance1.private = True
        self.instance2.private = True
        self.instance1.save()
        self.instance2.save()
        
        request = RequestFactory().get(path='/')
        request.user = self.user1
        
        f = filters.ExperimentSetFilterModel(
            queryset=models.experimentset.ExperimentSet.objects.all(),
            request=request
        )
        self.assertEqual(f.qs.count(), 2)


class TestExperimentFilter(TestCase):
    def setUp(self):
        self.user1 = UserFactory(first_name='Alice', last_name='Mare')
        self.user2 = UserFactory(first_name='David', last_name='Davidson')
        self.instance1 = factories.ExperimentWithScoresetFactory()
        self.instance2 = factories.ExperimentWithScoresetFactory()
        
        self.scoreset1 = utilities.publish_dataset(
            self.instance1.children.first())
        target1 = self.scoreset1.target
        genome1 = self.scoreset1.target.reference_maps.first().genome
        target1.name = 'BRCA1'
        target1.uniprot_id = meta_factories.UniprotIdentifierFactory(
            identifier='P00533')
        target1.ensembl_id = meta_factories.EnsemblIdentifierFactory(
            identifier='NP_001349131.1')
        target1.refseq_id = meta_factories.RefseqIdentifierFactory(
            identifier='ENSG00000267816')
        genome1.short_name = 'HG17'
        genome1.species_name = 'Homo sapiens'
        genome1.genome_id = meta_factories.GenomeIdentifierFactory(
            identifier='GCF_000146045.2')
        target1.save()
        genome1.save()
    
        self.scoreset2 = utilities.publish_dataset(
            self.instance2.children.first())
        target2 = self.scoreset2.target
        genome2 = self.scoreset2.target.reference_maps.first().genome
        target2.name = 'JAK'
        target2.uniprot_id = meta_factories.UniprotIdentifierFactory(
            identifier='P30530')
        target2.ensembl_id = meta_factories.EnsemblIdentifierFactory(
            identifier='YP_009472129.1')
        target2.refseq_id = meta_factories.RefseqIdentifierFactory(
            identifier='ENSG00000198001')
        genome2.short_name = 'HG18'
        genome2.species_name = 'Synthetic sequence'
        genome2.genome_id = meta_factories.GenomeIdentifierFactory(
            identifier='GCF_000001405.26')
        target2.save()
        genome2.save()
    
        self.scoreset2.licence = Licence.get_cc0()
        self.scoreset2.licence = Licence.get_cc_by()
        self.scoreset2.save()
        self.scoreset2.save()

        self.instance1.refresh_from_db()
        self.instance2.refresh_from_db()
        self.queryset = models.experiment.Experiment.objects.all()

    def test_search_by_licence_short_name(self):
        f = filters.ExperimentFilter(
            data={
                filters.ExperimentFilter.LICENCE:
                    self.instance1.children.first().licence.short_name,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_licence_long_name(self):
        f = filters.ExperimentFilter(
            data={
                filters.ExperimentFilter.LICENCE:
                    self.instance1.children.first().licence.long_name,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_genome_short_name(self):
        f = filters.ExperimentFilter(
            data={
                filters.ExperimentFilter.GENOME:
                    self.instance1.children.first().target.
                        reference_maps.first().
                        genome.short_name,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_genome_assembly_identifier(self):
        f = filters.ExperimentFilter(
            data={
                filters.ExperimentFilter.GENOME:
                    self.instance1.children.first().target.
                        reference_maps.first().
                        genome.genome_id.identifier,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_targetgene_name(self):
        f = filters.ExperimentFilter(
            data={
                filters.ExperimentFilter.TARGET: self.instance1.
                    children.first().target.name
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_targetgene_species(self):
        f = filters.ExperimentFilter(
            data={
                filters.ExperimentFilter.SPECIES:
                    self.instance1.children.first().target.
                        reference_maps.first().
                        genome.species_name,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_uniprot_id(self):
        f = filters.ExperimentFilter(
            data={
                filters.ExperimentFilter.UNIPROT: self.instance1.
                    children.first().target.
                    uniprot_id.identifier
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_ensembl_id(self):
        f = filters.ExperimentFilter(
            data={
                filters.ExperimentFilter.ENSEMBL: self.instance1.
                    children.first().target.
                    ensembl_id.identifier
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())

    def test_search_by_refseq_id(self):
        f = filters.ExperimentFilter(
            data={
                filters.ExperimentFilter.REFSEQ: self.instance1.
                    children.first().target.
                    refseq_id.identifier
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())


class TestScoreSetFilter(TestCase):
    def setUp(self):
        self.user1 = UserFactory(first_name='Alice', last_name='Mare')
        self.user2 = UserFactory(first_name='David', last_name='Davidson')
        self.instance1 = factories.ScoreSetWithTargetFactory()
        self.instance2 = factories.ScoreSetWithTargetFactory()
        self.queryset = models.scoreset.ScoreSet.objects.all()
        
        target1 = self.instance1.target
        genome1 = self.instance1.target.reference_maps.first().genome
        target1.name = 'BRCA1'
        target1.uniprot_id = meta_factories.UniprotIdentifierFactory(
            identifier='P00533')
        target1.ensembl_id = meta_factories.EnsemblIdentifierFactory(
            identifier='NP_001349131.1')
        target1.refseq_id = meta_factories.RefseqIdentifierFactory(
            identifier='ENSG00000267816')
        genome1.short_name = 'HG17'
        genome1.species_name = 'Homo sapiens'
        genome1.genome_id = meta_factories.GenomeIdentifierFactory(
            identifier='GCF_000146045.2')
        target1.save()
        genome1.save()

        target2 = self.instance2.target
        genome2 = self.instance2.target.reference_maps.first().genome
        target2.name = 'JAK'
        target2.uniprot_id = meta_factories.UniprotIdentifierFactory(
            identifier='P30530')
        target2.ensembl_id = meta_factories.EnsemblIdentifierFactory(
            identifier='YP_009472129.1')
        target2.refseq_id = meta_factories.RefseqIdentifierFactory(
            identifier='ENSG00000198001')
        genome2.short_name = 'HG18'
        genome2.species_name = 'Synthetic sequence'
        genome2.genome_id = meta_factories.GenomeIdentifierFactory(
            identifier='GCF_000001405.26')
        target2.save()
        genome2.save()

        self.instance1.licence = Licence.get_cc0()
        self.instance2.licence = Licence.get_cc_by()
        self.instance1.save()
        self.instance2.save()
        
        utilities.publish_dataset(self.instance1)
        utilities.publish_dataset(self.instance2)
        self.instance1.refresh_from_db()
        self.instance2.refresh_from_db()
    
    def test_search_by_licence_short_name(self):
        f = filters.ScoreSetFilter(
            data={
                filters.ScoreSetFilter.LICENCE:
                    self.instance1.licence.short_name,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
    
    def test_search_by_licence_long_name(self):
        f = filters.ScoreSetFilter(
            data={
                filters.ScoreSetFilter.LICENCE:
                    self.instance1.licence.long_name,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
    
    def test_search_by_genome_short_name(self):
        f = filters.ScoreSetFilter(
            data={
                filters.ScoreSetFilter.GENOME:
                    self.instance1.target.reference_maps.first().
                        genome.short_name,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
    
    def test_search_by_genome_assembly_identifier(self):
        f = filters.ScoreSetFilter(
            data={
                filters.ScoreSetFilter.GENOME:
                    self.instance1.target.reference_maps.first().
                        genome.genome_id.identifier,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
    
    def test_search_by_targetgene_name(self):
        f = filters.ScoreSetFilter(
            data={
                filters.ScoreSetFilter.TARGET: self.instance1.target.name
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
    
    def test_search_by_targetgene_species(self):
        f = filters.ScoreSetFilter(
            data={
                filters.ScoreSetFilter.SPECIES:
                    self.instance1.target.reference_maps.first().
                        genome.species_name,
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
    
    def test_search_by_uniprot_id(self):
        f = filters.ScoreSetFilter(
            data={
                filters.ScoreSetFilter.UNIPROT: self.instance1.target.
                    uniprot_id.identifier
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
    
    def test_search_by_ensembl_id(self):
        f = filters.ScoreSetFilter(
            data={
                filters.ScoreSetFilter.ENSEMBL: self.instance1.target.
                    ensembl_id.identifier
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
    
    def test_search_by_refseq_id(self):
        f = filters.ScoreSetFilter(
            data={
                filters.ScoreSetFilter.REFSEQ: self.instance1.target.
                    refseq_id.identifier
            },
            queryset=self.queryset,
        )
        self.assertIn(self.instance1, f.qs.all())
        self.assertNotIn(self.instance2, f.qs.all())
