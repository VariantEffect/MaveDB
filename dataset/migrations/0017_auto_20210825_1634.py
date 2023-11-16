# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-08-25 06:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dataset", "0016_auto_20200923_1616"),
    ]

    operations = [
        migrations.AlterField(
            model_name="experiment",
            name="doi_ids",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_experiments",
                to="metadata.DoiIdentifier",
                verbose_name="DOIs",
            ),
        ),
        migrations.AlterField(
            model_name="experiment",
            name="pubmed_ids",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_experiments",
                to="metadata.PubmedIdentifier",
                verbose_name="PubMed IDs",
            ),
        ),
        migrations.AlterField(
            model_name="experiment",
            name="sra_ids",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_experiments",
                to="metadata.SraIdentifier",
                verbose_name="Raw reads accessions",
            ),
        ),
        migrations.AlterField(
            model_name="experimentset",
            name="doi_ids",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_experimentsets",
                to="metadata.DoiIdentifier",
                verbose_name="DOIs",
            ),
        ),
        migrations.AlterField(
            model_name="experimentset",
            name="pubmed_ids",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_experimentsets",
                to="metadata.PubmedIdentifier",
                verbose_name="PubMed IDs",
            ),
        ),
        migrations.AlterField(
            model_name="experimentset",
            name="sra_ids",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_experimentsets",
                to="metadata.SraIdentifier",
                verbose_name="Raw reads accessions",
            ),
        ),
        migrations.AlterField(
            model_name="scoreset",
            name="doi_ids",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_scoresets",
                to="metadata.DoiIdentifier",
                verbose_name="DOIs",
            ),
        ),
        migrations.AlterField(
            model_name="scoreset",
            name="pubmed_ids",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_scoresets",
                to="metadata.PubmedIdentifier",
                verbose_name="PubMed IDs",
            ),
        ),
        migrations.AlterField(
            model_name="scoreset",
            name="sra_ids",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_scoresets",
                to="metadata.SraIdentifier",
                verbose_name="Raw reads accessions",
            ),
        ),
    ]