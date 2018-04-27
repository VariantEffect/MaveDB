# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-04-27 08:13
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0006_auto_20180425_1434'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenomeIdentifier',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateField(default=datetime.date.today, verbose_name='Creation date')),
                ('modification_date', models.DateField(auto_now=True, verbose_name='Modification date')),
                ('identifier', models.CharField(default=None, max_length=256, unique=True, verbose_name='Identifier')),
                ('dbname', models.CharField(default=None, max_length=256, verbose_name='Database name')),
                ('dbversion', models.CharField(blank=True, default=None, max_length=256, null=True, verbose_name='Database version')),
                ('url', models.URLField(blank=True, default=None, max_length=256, null=True, verbose_name='Identifier URL')),
            ],
            options={
                'verbose_name': 'Genome assembly accession',
                'verbose_name_plural': 'Genome assembly accessions',
            },
        ),
    ]