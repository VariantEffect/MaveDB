# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-03-23 06:49
from __future__ import unicode_literals

import accounts.mixins
import dataset.validators
import datetime
from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import genome.validators
import urn.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('metadata', '0001_initial'),
        ('genome', '0001_initial'),
        ('main', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Experiment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateField(default=datetime.date.today, verbose_name='Created on')),
                ('last_edit_date', models.DateField(default=datetime.date.today, verbose_name='Last edited on')),
                ('publish_date', models.DateField(default=None, null=True, verbose_name='Published on')),
                ('approved', models.BooleanField(default=False, verbose_name='Approved')),
                ('private', models.BooleanField(default=True, verbose_name='Private')),
                ('last_child_value', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(limit_value=0)])),
                ('extra_metadata', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}, verbose_name='Additional metadata')),
                ('abstract_text', models.TextField(blank=True, default='', verbose_name='Abstract')),
                ('method_text', models.TextField(blank=True, default='', verbose_name='Method description')),
                ('urn', models.CharField(blank=True, default=None, max_length=64, null=True, unique=True, validators=[urn.validators.validate_mavedb_urn_experiment], verbose_name='URN')),
                ('wt_sequence', models.TextField(default=None, validators=[genome.validators.validate_wildtype_sequence], verbose_name='Wild type sequence')),
                ('target', models.CharField(default=None, max_length=256, verbose_name='Target')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='last_created_experiment', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('doi_ids', models.ManyToManyField(blank=True, to='metadata.DoiIdentifier')),
            ],
            options={
                'verbose_name': 'Experiment',
                'verbose_name_plural': 'Experiments',
            },
            bases=(models.Model, accounts.mixins.GroupPermissionMixin),
        ),
        migrations.CreateModel(
            name='ExperimentSet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateField(default=datetime.date.today, verbose_name='Created on')),
                ('last_edit_date', models.DateField(default=datetime.date.today, verbose_name='Last edited on')),
                ('publish_date', models.DateField(default=None, null=True, verbose_name='Published on')),
                ('approved', models.BooleanField(default=False, verbose_name='Approved')),
                ('private', models.BooleanField(default=True, verbose_name='Private')),
                ('last_child_value', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(limit_value=0)])),
                ('extra_metadata', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}, verbose_name='Additional metadata')),
                ('abstract_text', models.TextField(blank=True, default='', verbose_name='Abstract')),
                ('method_text', models.TextField(blank=True, default='', verbose_name='Method description')),
                ('urn', models.CharField(blank=True, default=None, max_length=64, null=True, unique=True, validators=[urn.validators.validate_mavedb_urn_experimentset], verbose_name='URN')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='last_created_experimentset', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('doi_ids', models.ManyToManyField(blank=True, to='metadata.DoiIdentifier')),
                ('keywords', models.ManyToManyField(blank=True, to='metadata.Keyword')),
                ('last_edit_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='last_edited_experimentset', to=settings.AUTH_USER_MODEL, verbose_name='Last edited by')),
                ('pmid_ids', models.ManyToManyField(blank=True, to='metadata.PubmedIdentifier')),
                ('sra_ids', models.ManyToManyField(blank=True, to='metadata.SraIdentifier')),
            ],
            options={
                'verbose_name': 'ExperimentSet',
                'verbose_name_plural': 'ExperimentSets',
            },
            bases=(models.Model, accounts.mixins.GroupPermissionMixin),
        ),
        migrations.CreateModel(
            name='ScoreSet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateField(default=datetime.date.today, verbose_name='Created on')),
                ('last_edit_date', models.DateField(default=datetime.date.today, verbose_name='Last edited on')),
                ('publish_date', models.DateField(default=None, null=True, verbose_name='Published on')),
                ('approved', models.BooleanField(default=False, verbose_name='Approved')),
                ('private', models.BooleanField(default=True, verbose_name='Private')),
                ('last_child_value', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(limit_value=0)])),
                ('extra_metadata', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}, verbose_name='Additional metadata')),
                ('abstract_text', models.TextField(blank=True, default='', verbose_name='Abstract')),
                ('method_text', models.TextField(blank=True, default='', verbose_name='Method description')),
                ('urn', models.CharField(blank=True, default=None, max_length=64, null=True, unique=True, validators=[urn.validators.validate_mavedb_urn_scoreset], verbose_name='URN')),
                ('dataset_columns', django.contrib.postgres.fields.jsonb.JSONField(default={'count_columns': [], 'score_columns': []}, validators=[dataset.validators.validate_scoreset_json], verbose_name='Dataset columns')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='last_created_scoreset', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('doi_ids', models.ManyToManyField(blank=True, to='metadata.DoiIdentifier')),
                ('experiment', models.ForeignKey(default=None, on_delete=django.db.models.deletion.PROTECT, related_name='scoresets', to='dataset.Experiment', verbose_name='Experiment')),
                ('keywords', models.ManyToManyField(blank=True, to='metadata.Keyword')),
                ('last_edit_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='last_edited_scoreset', to=settings.AUTH_USER_MODEL, verbose_name='Last edited by')),
                ('licence', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='attached_scoresets', to='main.Licence', verbose_name='Licence')),
                ('pmid_ids', models.ManyToManyField(blank=True, to='metadata.PubmedIdentifier')),
                ('replaces', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='replaced_by', to='dataset.ScoreSet', verbose_name='Replaces')),
                ('sra_ids', models.ManyToManyField(blank=True, to='metadata.SraIdentifier')),
            ],
            options={
                'verbose_name': 'ScoreSet',
                'verbose_name_plural': 'ScoreSets',
            },
            bases=(models.Model, accounts.mixins.GroupPermissionMixin),
        ),
        migrations.AddField(
            model_name='experiment',
            name='experimentset',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='experiments', to='dataset.ExperimentSet', verbose_name='Experiment Set'),
        ),
        migrations.AddField(
            model_name='experiment',
            name='keywords',
            field=models.ManyToManyField(blank=True, to='metadata.Keyword'),
        ),
        migrations.AddField(
            model_name='experiment',
            name='last_edit_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='last_edited_experiment', to=settings.AUTH_USER_MODEL, verbose_name='Last edited by'),
        ),
        migrations.AddField(
            model_name='experiment',
            name='pmid_ids',
            field=models.ManyToManyField(blank=True, to='metadata.PubmedIdentifier'),
        ),
        migrations.AddField(
            model_name='experiment',
            name='sra_ids',
            field=models.ManyToManyField(blank=True, to='metadata.SraIdentifier'),
        ),
        migrations.AddField(
            model_name='experiment',
            name='target_organism',
            field=models.ManyToManyField(blank=True, to='genome.TargetOrganism'),
        ),
    ]