# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-04-11 04:23
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='doiidentifier',
            name='dbversion',
            field=models.CharField(blank=True, default=None, max_length=256, null=True, verbose_name='Database version'),
        ),
        migrations.AddField(
            model_name='doiidentifier',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AddField(
            model_name='ensemblidentifier',
            name='dbversion',
            field=models.CharField(blank=True, default=None, max_length=256, null=True, verbose_name='Database version'),
        ),
        migrations.AddField(
            model_name='ensemblidentifier',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AddField(
            model_name='keyword',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AddField(
            model_name='pubmedidentifier',
            name='dbversion',
            field=models.CharField(blank=True, default=None, max_length=256, null=True, verbose_name='Database version'),
        ),
        migrations.AddField(
            model_name='pubmedidentifier',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AddField(
            model_name='refseqidentifier',
            name='dbversion',
            field=models.CharField(blank=True, default=None, max_length=256, null=True, verbose_name='Database version'),
        ),
        migrations.AddField(
            model_name='refseqidentifier',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AddField(
            model_name='sraidentifier',
            name='dbversion',
            field=models.CharField(blank=True, default=None, max_length=256, null=True, verbose_name='Database version'),
        ),
        migrations.AddField(
            model_name='sraidentifier',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AddField(
            model_name='uniprotidentifier',
            name='dbversion',
            field=models.CharField(blank=True, default=None, max_length=256, null=True, verbose_name='Database version'),
        ),
        migrations.AddField(
            model_name='uniprotidentifier',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AlterField(
            model_name='doiidentifier',
            name='creation_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='ensemblidentifier',
            name='creation_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='pubmedidentifier',
            name='creation_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='refseqidentifier',
            name='creation_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='sraidentifier',
            name='creation_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='uniprotidentifier',
            name='creation_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Creation date'),
        ),
    ]