import os

from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.firefox.options import FirefoxBinary, Options

from django.test import LiveServerTestCase, mock, tag

from mavedb import celery_app

from accounts.factories import UserFactory

from dataset import models as data_models
from dataset import factories as data_factories
from dataset import tasks
from dataset import constants

from metadata import models as meta_models
from metadata import factories as meta_factories

from genome import factories as genome_factories
from genome import models as genome_models

from .utilities import (
    authenticate_webdriver,
    LOG_PATH,
    STAGING_OR_PROD,
    ActionMixin,
)

celery_app.conf["task_always_eager"] = False


class TestCreateExperimentAndScoreSet(LiveServerTestCase, ActionMixin):
    def setUp(self):
        self.user = UserFactory()
        if STAGING_OR_PROD:
            binary = FirefoxBinary("/usr/bin/firefox")
            options = Options()
            options.add_argument("--headless")
        else:
            binary = None
            options = None
        self.browser = webdriver.Firefox(
            log_path=LOG_PATH, firefox_options=options, firefox_binary=binary
        )

    def tearDown(self):
        self.browser.close()

    def authenticate(self):
        authenticate_webdriver(
            self.user.username, self.user._password, self, "browser"
        )

    @mock.patch(
        "dataset.tasks.create_variants.submit_task", return_value=(True, None)
    )
    @mock.patch("core.tasks.send_mail.submit_task", return_value=(True, None))
    @tag("webtest")
    def test_create_experiment_flow(self, notify_patch, variants_patch):
        # Create some experimentsets that the user should not be able to see
        exps1 = data_factories.ExperimentSetFactory(private=False)
        exps2 = data_factories.ExperimentSetFactory()
        exps3 = data_factories.ExperimentSetFactory()
        exps2.add_administrators(self.user)
        exps3.add_viewers(self.user)

        # Make one entry for each
        kw = meta_factories.KeywordFactory()
        pm = meta_factories.PubmedIdentifierFactory()
        doi = meta_factories.DoiIdentifierFactory()
        sra = meta_factories.SraIdentifierFactory()
        meta_models.Keyword.objects.all().delete()
        meta_models.SraIdentifier.objects.all().delete()
        meta_models.DoiIdentifier.objects.all().delete()
        meta_models.PubmedIdentifier.objects.all().delete()

        # Store the text only which selenium will use to input new entries
        kw_text = kw.text
        pm_identifier = pm.identifier
        sra_identifier = sra.identifier
        doi_identifier = doi.identifier

        self.authenticate()
        self.browser.get(self.live_server_url + "/experiment/new/")

        # Check that only exps2 is visible as this is the only editable one.
        exps_select = Select(
            self.browser.find_element_by_id("id_experimentset")
        )
        options = [o.text for o in exps_select.options]
        self.assertEqual(len(options), 2)
        self.assertIn("---", options[0])
        self.assertIn(exps2.urn, options[1])

        # ----- REQUIRED FIELDS ------- #
        title = self.browser.find_element_by_id("id_title")
        self.perform_action(title, "send_keys", "Experiment 1")

        description = self.browser.find_element_by_id("id_short_description")
        self.perform_action(description, "send_keys", "hello, world!")

        # ------ M2M fields ------- #
        # Ordering is important as it replicates the form field ordering
        # in `DatasetModelForm`
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[0]
        self.perform_action(field, "send_keys", kw_text)
        search_item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(search_item, "click")

        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[1]
        self.perform_action(field, "send_keys", doi_identifier)
        search_item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(search_item, "click")

        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[2]
        self.perform_action(field, "send_keys", sra_identifier)
        search_item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(search_item, "click")

        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[3]
        self.perform_action(field, "send_keys", pm_identifier)
        search_item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(search_item, "click")

        submit = self.browser.find_element_by_id("submit-form")
        self.perform_action(submit, "click")

        # ------ CHECK EXPERIMENT IS CONFIGURED CORRECTLY ------ #
        # Delete unnecessary objects
        exps1.delete()
        exps2.delete()
        exps3.delete()

        # Check the experiment has been configured properly
        kw = meta_models.Keyword.objects.all().first()
        sra = meta_models.SraIdentifier.objects.all().first()
        doi = meta_models.DoiIdentifier.objects.all().first()
        pm = meta_models.PubmedIdentifier.objects.all().first()

        experiment = data_models.experiment.Experiment.objects.first()
        messages = self.browser.find_elements_by_class_name("alert")
        self.assertEqual(len(messages), 2)
        self.assertIsNotNone(experiment)
        self.assertFalse(experiment.has_public_urn)
        self.assertEqual(list(experiment.keywords.all()), [kw])
        self.assertEqual(list(experiment.sra_ids.all()), [sra])
        self.assertEqual(list(experiment.doi_ids.all()), [doi])
        self.assertEqual(list(experiment.pubmed_ids.all()), [pm])

        # ----- MAKE SCORESET ------- #
        # Should be on the scoreset creation page - check the correct M2M
        # elements are selected.
        self.assertIn(
            "scoreset/new/?experiment={}".format(experiment.urn),
            self.browser.current_url,
        )
        exp_select = Select(self.browser.find_element_by_id("id_experiment"))
        self.assertEqual(
            [o.text for o in exp_select.all_selected_options],
            ["{} | {}".format(experiment.urn, experiment.title)],
        )

        kw_select = Select(self.browser.find_element_by_id("id_keywords"))
        self.assertEqual(
            [o.text for o in kw_select.all_selected_options], [kw.text]
        )

        pm_select = Select(self.browser.find_element_by_id("id_pubmed_ids"))
        self.assertEqual(
            [o.text for o in pm_select.all_selected_options], [pm.identifier]
        )

        doi_select = Select(self.browser.find_element_by_id("id_doi_ids"))
        self.assertEqual(
            [o.text for o in doi_select.all_selected_options], [doi.identifier]
        )

        # Check to see if the target drop down will auto-populate fields
        # Edit: Couldn't find a way, might be better to test this with a
        # javascript front end testing framework?
        scs = data_factories.ScoreSetWithTargetFactory()
        scs.add_viewers(self.user)
        self.authenticate()
        self.browser.get(
            self.live_server_url
            + "/scoreset/new/?experiment={}".format(experiment.urn)
        )

        # At least check if the target is clickable.
        target_select = Select(self.browser.find_element_by_id("id_target"))
        self.assertEqual(len([o.text for o in target_select.options]), 2)
        self.assertIn(scs.urn, target_select.options[1].text)

        # ----- REQUIRED FIELDS ------- #
        title = self.browser.find_element_by_id("id_title")
        self.perform_action(title, "send_keys", "score set 1")

        description = self.browser.find_element_by_id("id_short_description")
        self.perform_action(description, "send_keys", "hello, new world!")

        genome_input = self.browser.find_element_by_id(
            "select2-id_genome-container"
        )
        self.perform_action(genome_input, "click")
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[-1]
        self.perform_action(
            field,
            "send_keys",
            genome_models.ReferenceGenome.objects.first().display_name(),
        )
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        target_name = self.browser.find_element_by_id("id_name")
        self.perform_action(target_name, "send_keys", "BRCA1")
        target_seq = self.browser.find_element_by_id("id_sequence_text")
        self.perform_action(target_seq, "send_keys", "atcg")

        # Upload a local file.
        upload = self.browser.find_element_by_id("id_score_data")
        self.perform_action(
            upload, "send_keys", os.getcwd() + "/webtests/scores.csv"
        )

        # ----- M2M AND OFFSET FIELDS ----- #
        # Fill in the offset fields. Open the select2 container, and then
        # click the second option (first@0 is the null option)
        ensembl = meta_models.EnsemblIdentifier.objects.first()
        uniprot = meta_models.UniprotIdentifier.objects.first()
        refseq = meta_models.RefseqIdentifier.objects.first()

        # Add an extra keyword
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[1]
        self.perform_action(field, "send_keys", "new kw")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        id_input = self.browser.find_element_by_id(
            "select2-id_uniprot-offset-identifier-container"
        )
        self.perform_action(id_input, "click")
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[-1]
        self.perform_action(field, "send_keys", uniprot.identifier)
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")
        uniprot_offset = self.browser.find_element_by_id(
            "id_uniprot-offset-offset"
        )
        uniprot_offset.clear()
        self.perform_action(uniprot_offset, "send_keys", 10)

        id_input = self.browser.find_element_by_id(
            "select2-id_refseq-offset-identifier-container"
        )
        self.perform_action(id_input, "click")
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[-1]
        self.perform_action(field, "send_keys", refseq.identifier)
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")
        refseq_offset = self.browser.find_element_by_id(
            "id_refseq-offset-offset"
        )
        refseq_offset.clear()
        self.perform_action(refseq_offset, "send_keys", 20)

        id_input = self.browser.find_element_by_id(
            "select2-id_ensembl-offset-identifier-container"
        )
        self.perform_action(id_input, "click")
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[-1]
        self.perform_action(field, "send_keys", ensembl.identifier)
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")
        ensembl_offset = self.browser.find_element_by_id(
            "id_ensembl-offset-offset"
        )
        ensembl_offset.clear()
        self.perform_action(ensembl_offset, "send_keys", 30)

        # select target type
        self.browser.find_element_by_xpath(
            "//select[@id='id_category']/option[text()='Protein coding']"
        ).click()

        # Delete these identifier to see if new ones will be created
        uniprot.delete()
        refseq.delete()
        ensembl.delete()

        submit = self.browser.find_element_by_id("submit-form")
        self.perform_action(submit, "click")

        # ------ CHECK SCORESET IS CONFIGURED CORRECTLY ------ #
        # Check dashboard to see if success message and processing-icon shown
        messages = self.browser.find_elements_by_class_name("alert")
        self.assertEqual(len(messages), 1)
        processing = self.browser.find_element_by_class_name("processing-icon")
        self.assertIsNotNone(processing)

        # Run the create_variants tasks manually
        scs.delete()  # Delete test replaces
        self.assertEqual(data_models.scoreset.ScoreSet.objects.count(), 1)

        scoreset = data_models.scoreset.ScoreSet.objects.first()
        self.assertIsNotNone(scoreset)
        self.assertFalse(scoreset.has_public_urn)
        self.assertIn("new kw", [k.text for k in scoreset.keywords.all()])
        self.assertEqual(scoreset.processing_state, constants.processing)
        tasks.create_variants.apply(**variants_patch.call_args[1])

        # Check to see if the notify emails were sent
        self.assertEqual(notify_patch.call_count, 1)

        # Refresh scoreset and check fields
        self.assertEqual(data_models.scoreset.ScoreSet.objects.count(), 1)

        scoreset = data_models.scoreset.ScoreSet.objects.first()
        self.assertEqual(scoreset.processing_state, constants.success)
        self.assertEqual(scoreset.variants.count(), 6)
        self.assertEqual(
            scoreset.dataset_columns[constants.score_columns],
            ["score", "SE", "epsilon"],
        )
        self.assertEqual(scoreset.dataset_columns[constants.count_columns], [])

        # Check that the target is properly configured
        targetgene = scoreset.get_target()
        self.assertIsNotNone(targetgene)

        uniprot = meta_models.UniprotIdentifier.objects.first()
        uniprot_offset = targetgene.get_uniprot_offset_annotation()
        self.assertIsNotNone(uniprot_offset)
        self.assertEqual(uniprot_offset.offset, 10)
        self.assertEqual(uniprot_offset.identifier, uniprot)
        self.assertEqual(targetgene.uniprot_id, uniprot)

        refseq = meta_models.RefseqIdentifier.objects.first()
        refseq_offset = targetgene.get_refseq_offset_annotation()
        self.assertIsNotNone(refseq_offset)
        self.assertEqual(refseq_offset.offset, 20)
        self.assertEqual(refseq_offset.identifier, refseq)
        self.assertEqual(targetgene.refseq_id, refseq)

        ensembl = meta_models.EnsemblIdentifier.objects.first()
        ensembl_offset = targetgene.get_ensembl_offset_annotation()
        self.assertIsNotNone(ensembl_offset)
        self.assertEqual(ensembl_offset.offset, 30)
        self.assertEqual(ensembl_offset.identifier, ensembl)
        self.assertEqual(targetgene.ensembl_id, ensembl)

        # Check browser shows smiley-icon
        self.browser.refresh()
        success = self.browser.find_element_by_class_name("success-icon")
        self.assertIsNotNone(success)

        self.assertIn(self.user, scoreset.administrators)
        self.assertIn(self.user, scoreset.experiment.administrators)
        self.assertIn(
            self.user, scoreset.experiment.experimentset.administrators
        )


class TestJavaScriptOnCreatePage(LiveServerTestCase, ActionMixin):
    def setUp(self):
        self.user = UserFactory()
        self.browser = webdriver.Firefox(log_path=LOG_PATH)

    def tearDown(self):
        self.browser.close()

    def authenticate(self):
        authenticate_webdriver(
            self.user.username, self.user._password, self, "browser"
        )

    @tag("webtest")
    def test_failed_experiment_submission_repops_m2m_fields(self):
        self.authenticate()
        self.browser.get(self.live_server_url + "/experiment/new/")

        # Fill in the fields.
        title = self.browser.find_element_by_id("id_title")
        self.perform_action(title, "send_keys", "Experiment 1")

        description = self.browser.find_element_by_id("id_short_description")
        self.perform_action(description, "send_keys", "hello, world!")

        # Ordering is important as it replicates the form field ordering
        # in `DatasetModelForm`
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[0]
        self.perform_action(field, "send_keys", "new keyword")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[1]
        self.perform_action(field, "send_keys", "bad doi")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[2]
        self.perform_action(field, "send_keys", "bad sra")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[3]
        self.perform_action(field, "send_keys", "bad pm")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        submit = self.browser.find_element_by_id("submit-form")
        self.perform_action(submit, "click")

        messages = self.browser.find_elements_by_class_name("invalid-feedback")
        self.assertGreater(len(messages), 0)

        select = Select(self.browser.find_element_by_id("id_keywords"))
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["new keyword"]
        )

        select = Select(self.browser.find_element_by_id("id_sra_ids"))
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["bad sra"]
        )

        select = Select(self.browser.find_element_by_id("id_doi_ids"))
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["bad doi"]
        )

        select = Select(self.browser.find_element_by_id("id_pubmed_ids"))
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["bad pm"]
        )

    @tag("webtest")
    def test_failed_scoreset_submission_repops_m2m_fields(self):
        # Create a genome to select as this is a required field
        genome_factories.ReferenceGenomeFactory()

        # Create an experiment we can select
        experiment = data_models.experiment.Experiment(
            title="Hello", short_description="world"
        )
        experiment.save()
        experiment.add_administrators(self.user)

        self.authenticate()
        self.browser.get(self.live_server_url + "/scoreset/new/")

        # Fill in required fields.
        title = self.browser.find_element_by_id("id_title")
        self.perform_action(title, "send_keys", "ScoreSet 1")

        description = self.browser.find_element_by_id("id_short_description")
        self.perform_action(description, "send_keys", "hello, world!")

        target_name = self.browser.find_element_by_id("id_name")
        self.perform_action(target_name, "send_keys", "BRCA1")
        target_seq = self.browser.find_element_by_id("id_sequence_text")
        self.perform_action(target_seq, "send_keys", "atcg")

        # select target type
        self.browser.find_element_by_xpath(
            "//select[@id='id_category']/option[text()='Protein coding']"
        ).click()

        genome_input = self.browser.find_element_by_id(
            "select2-id_genome-container"
        )
        self.perform_action(genome_input, "click")
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[-1]
        self.perform_action(
            field,
            "send_keys",
            genome_models.ReferenceGenome.objects.first().display_name(),
        )
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        exp_input = self.browser.find_element_by_id(
            "select2-id_experiment-container"
        )
        self.perform_action(exp_input, "click")
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[-1]
        self.perform_action(field, "send_keys", experiment.urn)
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        upload = self.browser.find_element_by_id("id_score_data")
        self.perform_action(
            upload, "send_keys", os.getcwd() + "/webtests/scores.csv"
        )

        # Ordering is important as it replicates the form field ordering
        # in `DatasetModelForm`
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[1]
        self.perform_action(field, "send_keys", "new keyword")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[2]
        self.perform_action(field, "send_keys", "invalid doi")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[3]
        self.perform_action(field, "send_keys", "invalid sra")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        id_input = self.browser.find_element_by_id(
            "select2-id_uniprot-offset-identifier-container"
        )
        self.perform_action(id_input, "click")
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[-1]
        self.perform_action(field, "send_keys", "invalid uniprot")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        id_input = self.browser.find_element_by_id(
            "select2-id_refseq-offset-identifier-container"
        )
        self.perform_action(id_input, "click")
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[-1]
        self.perform_action(field, "send_keys", "invalid refseq")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        id_input = self.browser.find_element_by_id(
            "select2-id_ensembl-offset-identifier-container"
        )
        self.perform_action(id_input, "click")
        field = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[-1]
        self.perform_action(field, "send_keys", "invalid ensembl")
        item = self.browser.find_elements_by_class_name(
            "select2-results__option"
        )[0]
        self.perform_action(item, "click")

        submit = self.browser.find_element_by_id("submit-form")
        self.perform_action(submit, "click")

        messages = self.browser.find_elements_by_class_name("invalid-feedback")
        self.assertGreater(len(messages), 0)

        select = Select(self.browser.find_element_by_id("id_keywords"))
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["new keyword"]
        )

        select = Select(self.browser.find_element_by_id("id_doi_ids"))
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["invalid doi"]
        )

        select = Select(self.browser.find_element_by_id("id_pubmed_ids"))
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["invalid sra"]
        )

        select = Select(
            self.browser.find_element_by_id("id_uniprot-offset-identifier")
        )
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["invalid uniprot"]
        )

        select = Select(
            self.browser.find_element_by_id("id_refseq-offset-identifier")
        )
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["invalid refseq"]
        )

        select = Select(
            self.browser.find_element_by_id("id_ensembl-offset-identifier")
        )
        self.assertEqual(
            [o.text for o in select.all_selected_options], ["invalid ensembl"]
        )
