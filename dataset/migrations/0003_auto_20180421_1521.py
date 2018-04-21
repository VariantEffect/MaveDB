# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-04-21 05:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataset', '0002_experiment_targets'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experiment',
            name='short_description',
            field=models.TextField(default='', verbose_name='Short description'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='title',
            field=models.CharField(default='', max_length=250, verbose_name='Short title'),
        ),
        migrations.AlterField(
            model_name='experimentset',
            name='short_description',
            field=models.TextField(default='', verbose_name='Short description'),
        ),
        migrations.AlterField(
            model_name='experimentset',
            name='title',
            field=models.CharField(default='', max_length=250, verbose_name='Short title'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='short_description',
            field=models.TextField(default='', verbose_name='Short description'),
        ),
        migrations.AlterField(
            model_name='scoreset',
            name='title',
            field=models.CharField(default='', max_length=250, verbose_name='Short title'),
        ),
    ]
