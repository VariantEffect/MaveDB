# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-04-12 07:38
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import genome.validators


class Migration(migrations.Migration):

    dependencies = [
        ('genome', '0003_auto_20180411_1453'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interval',
            name='chromosome',
            field=models.CharField(default=None, max_length=32, validators=[genome.validators.validate_chromosome], verbose_name='Chromosome identifier'),
        ),
        migrations.AlterField(
            model_name='interval',
            name='end',
            field=models.PositiveIntegerField(default=None, validators=[django.core.validators.MinValueValidator(1, message='The minimum starting positive is 1.')], verbose_name='End (inclusive)'),
        ),
        migrations.AlterField(
            model_name='interval',
            name='start',
            field=models.PositiveIntegerField(default=None, validators=[django.core.validators.MinValueValidator(1, message='The minimum starting positive is 1.')], verbose_name='Start'),
        ),
        migrations.AlterField(
            model_name='interval',
            name='strand',
            field=models.CharField(choices=[('F', 'Forward'), ('R', 'Reverse')], default=None, max_length=1, validators=[genome.validators.validate_strand], verbose_name='Strand'),
        ),
        migrations.AlterField(
            model_name='referencegenome',
            name='short_name',
            field=models.CharField(default=None, max_length=256, validators=[genome.validators.validate_genome_short_name], verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='referencegenome',
            name='species_name',
            field=models.CharField(default=None, max_length=256, validators=[genome.validators.validate_species_name], verbose_name='Species'),
        ),
        migrations.AlterField(
            model_name='targetgene',
            name='name',
            field=models.CharField(default=None, max_length=256, validators=[genome.validators.validate_gene_name], verbose_name='Target name'),
        ),
    ]
