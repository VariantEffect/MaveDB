# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-09-03 04:08
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scoreset', '0008_auto_20170903_1356'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scoreset',
            name='replaces',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='replaced_by', to='scoreset.ScoreSet', verbose_name='Replaces'),
        ),
    ]
