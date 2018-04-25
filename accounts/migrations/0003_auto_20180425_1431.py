# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-04-25 04:31
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20180425_1428'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='creation_date',
            field=models.DateField(default=datetime.date(2018, 4, 25), verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='modification_date',
            field=models.DateField(auto_now=True, verbose_name='Modification date'),
        ),
    ]
