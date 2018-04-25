# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-04-25 04:28
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_auto_20180420_2012'),
    ]

    operations = [
        migrations.AlterField(
            model_name='licence',
            name='creation_date',
            field=models.DateTimeField(default=datetime.datetime(2018, 4, 25, 14, 28, 19, 31529), verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='licence',
            name='modification_date',
            field=models.DateTimeField(auto_now=True, verbose_name='Modification date'),
        ),
        migrations.AlterField(
            model_name='news',
            name='creation_date',
            field=models.DateTimeField(default=datetime.datetime(2018, 4, 25, 14, 28, 19, 31529), verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='news',
            name='modification_date',
            field=models.DateTimeField(auto_now=True, verbose_name='Modification date'),
        ),
        migrations.AlterField(
            model_name='siteinformation',
            name='creation_date',
            field=models.DateTimeField(default=datetime.datetime(2018, 4, 25, 14, 28, 19, 31529), verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='siteinformation',
            name='modification_date',
            field=models.DateTimeField(auto_now=True, verbose_name='Modification date'),
        ),
    ]
