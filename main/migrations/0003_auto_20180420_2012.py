# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-04-20 10:12
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_auto_20180420_1643'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='news',
            options={'ordering': ['-creation_date'], 'verbose_name': 'News item', 'verbose_name_plural': 'News items'},
        ),
    ]