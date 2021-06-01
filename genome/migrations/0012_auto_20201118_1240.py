# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-11-18 01:40
from __future__ import unicode_literals

from django.db import migrations, models, transaction


class Migration(migrations.Migration):

    dependencies = [
        ("genome", "0011_auto_20190208_1539"),
    ]

    operations = [
        migrations.AddField(
            model_name="wildtypesequence",
            name="sequence_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("infer", "Infer"),
                    ("dna", "DNA"),
                    ("protein", "Protein"),
                ],
                default="infer",
                max_length=32,
                verbose_name="Reference sequence type",
            ),
        ),
        migrations.AlterField(
            model_name="targetgene",
            name="category",
            field=models.CharField(
                choices=[
                    ("Protein coding", "Protein coding"),
                    ("Regulatory", "Regulatory"),
                    ("Other noncoding", "Other noncoding"),
                ],
                default="Protein coding",
                max_length=32,
                verbose_name="Target type",
            ),
        ),
    ]

    @transaction.atomic()
    def apply(self, *args, **kwargs):
        retval = super().apply(*args, **kwargs)

        # All sequences will be initialized with 'infer', so run save on
        # each to infer the sequence type.
        from ..models import WildTypeSequence

        [i.save() for i in WildTypeSequence.objects.all()]

        return retval
