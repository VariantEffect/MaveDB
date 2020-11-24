import os
from io import StringIO

from django.test import TestCase
from django.core.files.uploadedfile import InMemoryUploadedFile

from accounts.factories import UserFactory
from accounts.permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_editor,
    assign_user_as_instance_viewer,
)

from core.utilities import null_values_list
from dataset.factories import ScoreSetFactory

from ..models import WildTypeSequence
from ..factories import (
    TargetGeneFactory,
    ReferenceMapFactory,
    ReferenceGenomeFactory,
    GenomicIntervalFactory,
)

from ..forms import GenomicIntervalForm, ReferenceMapForm, TargetGeneForm


class TestGenomicIntervalForm(TestCase):
    """
    Tests that :class:`GenomicIntervalForm` raises the appropriate errors when
    invalid input is supplied; and can update existing instances.
    """

    def test_ve_end_less_than_start(self):
        data = {"start": 2, "end": 1, "chromosome": "chrX", "strand": "+"}
        self.assertFalse(GenomicIntervalForm(data=data).is_valid())

    def test_ve_partially_filled_out_form(self):
        data = {"start": "", "end": 1, "chromosome": "chrX", "strand": "+"}
        self.assertFalse(GenomicIntervalForm(data=data).is_valid())

        data = {"start": 1, "end": "", "chromosome": "chrX", "strand": "+"}
        self.assertFalse(GenomicIntervalForm(data=data).is_valid())

    def test_ve_chromosome_null_value(self):
        for value in null_values_list:
            data = {"start": 1, "end": 2, "chromosome": value, "strand": "+"}
            self.assertFalse(GenomicIntervalForm(data=data).is_valid())

    def test_ve_strand_null_value(self):
        for value in null_values_list:
            data = {
                "start": 1,
                "end": 2,
                "chromosome": "chr21",
                "strand": value,
            }
            self.assertFalse(GenomicIntervalForm(data=data).is_valid())

    def test_updates_existing(self):
        data = {"start": 1, "end": 2, "chromosome": "chr21", "strand": "+"}
        instance = GenomicIntervalFactory()
        instance = GenomicIntervalForm(data=data, instance=instance).save(
            commit=True
        )

        expected = {
            "start": instance.start,
            "end": instance.end,
            "chromosome": instance.chromosome,
            "strand": instance.strand,
        }
        self.assertEqual(expected, data)


class TestReferenceMapForm(TestCase):
    """
    Tests that :class:`ReferenceMapForm` raises the appropriate errors when
    invalid input is supplied; and can update existing instances.
    """

    def test_ve_selected_genome_does_not_exist(self):
        data = {"genome": 1, "is_primary": True}
        form = ReferenceMapForm(data=data)
        self.assertFalse(form.is_valid())

    def test_ve_no_selected_genome(self):
        data = {"genome": 1, "is_primary": True}
        form = ReferenceMapForm(data=data)
        self.assertFalse(form.is_valid())

    def test_updates_existing(self):
        ref = ReferenceGenomeFactory()
        instance = ReferenceMapFactory()
        data = {"genome": ref.pk, "is_primary": True}
        form = ReferenceMapForm(data=data, instance=instance)
        instance = form.save(commit=True)
        self.assertEqual(
            instance.is_primary_reference_map(), data["is_primary"]
        )
        self.assertEqual(instance.get_reference_genome(), ref)


class TestTargetGeneForm(TestCase):
    """
    Tests that :class:`TargetGeneForm` raises the appropriate errors when
    invalid input is supplied; and can update existing instances.
    """

    def setUp(self):
        self.user = UserFactory()

    @staticmethod
    def mock_form_data(**kwargs):
        files = {}
        data = dict(
            name="GeneA",
            category="Protein coding",
            sequence_text="ATCG",
            sequence_type=WildTypeSequence.SequenceType.INFER,
            target=None,
        )

        fasta_content = kwargs.pop("sequence_fasta", None)
        if fasta_content is not None:
            handle = StringIO(fasta_content)
            size = handle.seek(0, os.SEEK_END)
            handle.seek(0)
            file = InMemoryUploadedFile(
                file=handle,
                name="sequence.fa",
                field_name="sequence_fasta",
                content_type="text/plain",
                size=size,
                charset="utf-8",
            )
            files = dict(sequence_fasta=file)

        data.update(dict(**kwargs))
        return data, files

    def test_ve_null_wt_sequence(self):
        for v in null_values_list:
            data, _ = self.mock_form_data(sequence_text=v)
            form = TargetGeneForm(user=self.user, data=data)
            self.assertFalse(form.is_valid())

    def test_fail_non_nucleotide_sequence(self):
        data, _ = self.mock_form_data(sequence_text="1234")
        form = TargetGeneForm(user=self.user, data=data)
        self.assertFalse(form.is_valid())

    def test_ve_null_name(self):
        for v in null_values_list:
            data, _ = self.mock_form_data(sequence_text="atcg", name=v)
            form = TargetGeneForm(user=self.user, data=data)
            self.assertFalse(form.is_valid())

    def test_can_read_sequence_from_fasta_file(self):
        data, files = self.mock_form_data(
            sequence_fasta=">sequence_1\nAAAA\n>sequence_2\nCCCC",
            sequence_text=None,
        )
        form = TargetGeneForm(user=self.user, data=data, files=files)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.sequence_params["sequence"], "AAAA")

    def test_must_have_either_sequence_or_fasta(self):
        data, files = self.mock_form_data(
            sequence_fasta=None,
            sequence_text=None,
        )
        form = TargetGeneForm(user=self.user, data=data, files=files)
        self.assertFalse(form.is_valid())
        self.assertIn("sequence is required", str(form.errors).lower())

    def test_infers_protein_sequence(self):
        data, _ = self.mock_form_data(sequence_text="MLNS")
        form = TargetGeneForm(user=self.user, data=data)
        self.assertTrue(form.is_valid())

        i = form.save(scoreset=ScoreSetFactory())
        self.assertTrue(i.get_wt_sequence().is_protein)

    def test_infers_dna_sequence(self):
        data, _ = self.mock_form_data(sequence_text="ATCG")
        form = TargetGeneForm(user=self.user, data=data)
        self.assertTrue(form.is_valid())

        i = form.save(scoreset=ScoreSetFactory())
        self.assertTrue(i.get_wt_sequence().is_dna)

    def test_strips_whitespace_from_wt_seq(self):
        data, _ = self.mock_form_data(sequence_text=" atcg ")
        form = TargetGeneForm(user=self.user, data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.sequence_params["sequence"], "atcg")

    def test_strips_line_breaks_tabs_ws_from_wt_seq(self):
        data, _ = self.mock_form_data(
            sequence_text=" atcg\ngtac\r\ngg\tgg aaaa"
        )
        form = TargetGeneForm(user=self.user, data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.sequence_params["sequence"], "atcggtacggggaaaa")

    def test_private_targets_hidden_if_user_has_no_permissions(self):
        instance = TargetGeneFactory()
        instance.scoreset.private = True
        instance.scoreset.save()

        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields["target"].queryset.count(), 0)

    def test_private_targets_shown_if_user_has_permissions(self):
        instance = TargetGeneFactory()
        instance.scoreset.private = True
        instance.scoreset.save()

        assign_user_as_instance_admin(self.user, instance.scoreset)
        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields["target"].queryset.count(), 1)

        assign_user_as_instance_editor(self.user, instance.scoreset)
        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields["target"].queryset.count(), 1)

        assign_user_as_instance_viewer(self.user, instance.scoreset)
        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields["target"].queryset.count(), 1)

    def test_public_targets_shown_as_options(self):
        instance = TargetGeneFactory()
        instance.scoreset.private = False
        instance.scoreset.save()

        form = TargetGeneForm(user=self.user)
        self.assertEqual(form.fields["target"].queryset.count(), 1)

    def test_save_sets_wt_sequence_and_type(self):
        data, files = self.mock_form_data(sequence_text="atcg")
        form = TargetGeneForm(user=self.user, data=data)
        scs = ScoreSetFactory()
        form.instance.scoreset = scs

        instance = form.save(commit=True)
        self.assertEqual(instance.get_wt_sequence_string(), "ATCG")
        self.assertTrue(instance.get_wt_sequence().is_dna)

    def test_updates_existing_wt_sequence(self):
        instance = TargetGeneFactory()

        wt = instance.get_wt_sequence()
        self.assertTrue(wt.is_dna)

        data, _ = self.mock_form_data(sequence_text="MPLS", name="JAK")
        form = TargetGeneForm(user=self.user, data=data, instance=instance)

        instance = form.save(commit=True)
        self.assertEqual(instance.get_name(), "JAK")
        self.assertEqual(instance.get_wt_sequence_string(), "MPLS")
        self.assertTrue(instance.get_wt_sequence().is_protein)
        self.assertIs(instance.get_wt_sequence(), wt)
        self.assertEqual(WildTypeSequence.objects.count(), 1)
