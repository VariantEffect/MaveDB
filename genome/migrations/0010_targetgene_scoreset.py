# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-04-14 12:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dataset', '0012_remove_scoreset_target'),
        ('genome', '0009_auto_20180413_2255'),
    ]

    operations = [
        migrations.AddField(
            model_name='targetgene',
            name='scoreset',
            field=models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='target', to='dataset.ScoreSet'),
        ),
    ]