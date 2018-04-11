# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-04-11 04:23
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('genome', '0001_initial'),
        ('dataset', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='experiment',
            old_name='last_edit_by',
            new_name='modified_by',
        ),
        migrations.RenameField(
            model_name='experimentset',
            old_name='last_edit_by',
            new_name='modified_by',
        ),
        migrations.RenameField(
            model_name='scoreset',
            old_name='last_edit_by',
            new_name='modified_by',
        ),
        migrations.RemoveField(
            model_name='experiment',
            name='last_edit_date',
        ),
        migrations.RemoveField(
            model_name='experiment',
            name='target',
        ),
        migrations.RemoveField(
            model_name='experiment',
            name='target_organism',
        ),
        migrations.RemoveField(
            model_name='experiment',
            name='wt_sequence',
        ),
        migrations.RemoveField(
            model_name='experimentset',
            name='last_edit_date',
        ),
        migrations.RemoveField(
            model_name='scoreset',
            name='last_edit_date',
        ),
        migrations.AddField(
            model_name='experiment',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AddField(
            model_name='experiment',
            name='targets',
            field=models.ManyToManyField(to='genome.TargetGene'),
        ),
        migrations.AddField(
            model_name='experimentset',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AddField(
            model_name='scoreset',
            name='modification_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Modification date'),
        ),
        migrations.AddField(
            model_name='scoreset',
            name='target',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.PROTECT, to='genome.TargetGene', verbose_name='Target gene'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='creation_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='experimentset',
            name='creation_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='creation_date',
            field=models.DateField(default=datetime.date.today, verbose_name='Creation date'),
        ),
    ]