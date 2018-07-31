from django.test import TestCase, RequestFactory

from dataset import filters as ds_filters

from .. import forms


class TestAdvancedSearchForm(TestCase):
    def test_format_for_filter_empty_no_data(self):
        request = RequestFactory().get("/")
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertFalse(result)
        
    def test_format_for_filter_does_not_split_on_double_quotes(self):
        request = RequestFactory().get("/?{key}=Homo&{key}=\"s,d\"".format(
            key=ds_filters.ScoreSetFilter.SPECIES))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.ScoreSetFilter.SPECIES], 'Homo,"s,d"')
    
    # DatasetModel Filter fields
    # ------------------------------------------------------------------- #
    def test_format_for_filter_formats_title_field(self):
        request = RequestFactory().get("/?{}=hello".format(
            ds_filters.DatasetModelFilter.TITLE))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.TITLE], 'hello')
    
    def test_format_for_filter_formats_desc_field(self):
        request = RequestFactory().get("/?{}=hello".format(
            ds_filters.DatasetModelFilter.DESCRIPTION))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.DESCRIPTION], 'hello')
    
    def test_format_for_filter_formats_method_field(self):
        request = RequestFactory().get("/?{}=hello\nworld".format(
            ds_filters.DatasetModelFilter.METHOD))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.METHOD], 'hello\nworld')
    
    def test_format_for_filter_formats_abstract_field(self):
        request = RequestFactory().get("/?{}=hello\nworld".format(
            ds_filters.DatasetModelFilter.ABSTRACT))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.ABSTRACT], 'hello\nworld')
    
    def test_format_for_filter_formats_sra_field(self):
        request = RequestFactory().get("/?{key}=1&{key}=2".format(
            key=ds_filters.DatasetModelFilter.SRA))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.SRA], '1,2')
    
    def test_format_for_filter_formats_doi_field(self):
        request = RequestFactory().get("/?{key}=1&{key}=2".format(
            key=ds_filters.DatasetModelFilter.DOI))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.DOI], '1,2')
    
    def test_format_for_filter_formats_pubmed_field(self):
        request = RequestFactory().get("/?{key}=1&{key}=2".format(
            key=ds_filters.DatasetModelFilter.PUBMED))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.PUBMED], '1,2')
    
    def test_format_for_filter_formats_keyword_field(self):
        request = RequestFactory().get("/?{key}=1&{key}=2".format(
            key=ds_filters.DatasetModelFilter.KEYWORD))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.KEYWORD], '1,2')

    # User filter fields
    # ------------------------------------------------------------------- #
    def test_format_for_filter_formats_fn_field(self):
        request = RequestFactory().get("/?{key}=1&{key}=2".format(
            key=ds_filters.DatasetModelFilter.FIRST_NAME))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.FIRST_NAME], '1,2')

    def test_format_for_filter_formats_ln_field(self):
        request = RequestFactory().get("/?{key}=1&{key}=2".format(
            key=ds_filters.DatasetModelFilter.LAST_NAME))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.LAST_NAME], '1,2')

    def test_format_for_filter_formats_un_field(self):
        request = RequestFactory().get("/?{key}=1&{key}=2".format(
            key=ds_filters.DatasetModelFilter.USERNAME))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.USERNAME], '1,2')

    def test_format_for_filter_formats_dn_field(self):
        request = RequestFactory().get("/?{key}=1&{key}=2".format(
            key=ds_filters.DatasetModelFilter.DISPLAY_NAME))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.DatasetModelFilter.DISPLAY_NAME], '1,2')

    # ScoreSet/Experiment filter fields
    # ------------------------------------------------------------------- #
    def test_format_for_filter_formats_target_field(self):
        request = RequestFactory().get("/?{key}=BRCA1&{key}=JAK".format(
            key=ds_filters.ScoreSetFilter.TARGET))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.ScoreSetFilter.TARGET], 'BRCA1,JAK')
        
    def test_format_for_filter_formats_species_field(self):
        request = RequestFactory().get("/?{key}=Homo&{key}=Sapiens".format(
            key=ds_filters.ScoreSetFilter.SPECIES))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.ScoreSetFilter.SPECIES], 'Homo,Sapiens')
        
    def test_format_for_filter_formats_genome_field(self):
        request = RequestFactory().get("/?{key}=111&{key}=222".format(
            key=ds_filters.ScoreSetFilter.GENOME))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.ScoreSetFilter.GENOME], '111,222')
        
    def test_format_for_filter_formats_uniprot_field(self):
        request = RequestFactory().get("/?{key}=111&{key}=222".format(
            key=ds_filters.ScoreSetFilter.UNIPROT))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.ScoreSetFilter.UNIPROT], '111,222')
        
    def test_format_for_filter_formats_refseq_field(self):
        request = RequestFactory().get("/?{key}=111&{key}=222".format(
            key=ds_filters.ScoreSetFilter.REFSEQ))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.ScoreSetFilter.REFSEQ], '111,222')
        
    def test_format_for_filter_formats_ensembl_field(self):
        request = RequestFactory().get("/?{key}=111&{key}=222".format(
            key=ds_filters.ScoreSetFilter.ENSEMBL))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.ScoreSetFilter.ENSEMBL], '111,222')
        
    def test_format_for_filter_formats_licence_field(self):
        request = RequestFactory().get("/?{key}=CC0&{key}=CC by SA 4.0".format(
            key=ds_filters.ScoreSetFilter.LICENCE))
        form = forms.AdvancedSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertEqual(
            result[ds_filters.ScoreSetFilter.LICENCE], 'CC0,CC by SA 4.0')
    
    
class TestBasicSearchForm(TestCase):
    def test_format_for_filters_returns_falsey_if_no_input(self):
        request = RequestFactory().get("/")
        form = forms.BasicSearchForm(request.GET)
        self.assertFalse(form.format_data_for_filter())
        
    def test_format_for_filters_adds_in_all_fields(self):
        request = RequestFactory().get("/?{key}=Hello,World".format(
            key='search'))
        form = forms.BasicSearchForm(request.GET)
        result = form.format_data_for_filter()
        self.assertTrue(result)
        self.assertEqual(result['title'], 'Hello,World')
        self.assertEqual(len(result), 20)
