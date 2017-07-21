# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-07-21 04:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_scoreset_doi'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experiment',
            name='abstract',
            field=models.TextField(blank=True, default='', verbose_name='Abstract'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='alt_target_accessions',
            field=models.TextField(blank=True, default='', verbose_name='Accessions'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='authors',
            field=models.TextField(default='', verbose_name='Author(s)'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='doi',
            field=models.TextField(blank=True, default='', verbose_name='DOI'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='keywords',
            field=models.TextField(blank=True, default='', verbose_name='Keywords'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='method_description',
            field=models.TextField(blank=True, default='', verbose_name='Method description'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='short_description',
            field=models.TextField(blank=True, default='', verbose_name='Short description'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='sra',
            field=models.TextField(blank=True, default='', verbose_name='SRA'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='target',
            field=models.CharField(default='', max_length=128, verbose_name='Target'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='target_organism',
            field=models.TextField(blank=True, default='', verbose_name='Target organism'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='wt_sequence',
            field=models.TextField(default='', verbose_name='Wild type sequence'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='abstract',
            field=models.TextField(blank=True, default='', verbose_name='Abstract'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='accession',
            field=models.CharField(default='', max_length=128, verbose_name='Accession'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='authors',
            field=models.TextField(default='', verbose_name='Author(s)'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='doi',
            field=models.TextField(blank=True, default='', verbose_name='DOI'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='keywords',
            field=models.TextField(blank=True, default='', verbose_name='Keywords'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='name',
            field=models.TextField(blank=True, default='', verbose_name='Score set name'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='theory',
            field=models.TextField(blank=True, default='', verbose_name='Method theory'),
        ),
    ]
