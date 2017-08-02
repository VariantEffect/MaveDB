# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-08-02 06:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiment', '0002_auto_20170802_1627'),
    ]

    operations = [
        migrations.AddField(
            model_name='experiment',
            name='doi_id',
            field=models.TextField(blank=True, default='', verbose_name='DOI identifier'),
        ),
        migrations.AddField(
            model_name='experiment',
            name='sra_id',
            field=models.TextField(blank=True, default='', verbose_name='SRA identifier'),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='method_desc',
            field=models.TextField(blank=True, default='', verbose_name='Method description'),
        ),
    ]
