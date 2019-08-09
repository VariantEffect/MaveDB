# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-07-30 07:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("main", "0005_auto_20180615_1346")]

    operations = [
        migrations.AlterField(
            model_name="licence",
            name="long_name",
            field=models.CharField(
                default=None,
                max_length=200,
                unique=True,
                verbose_name="Long name",
            ),
        ),
        migrations.AlterField(
            model_name="licence",
            name="short_name",
            field=models.CharField(
                default=None,
                max_length=200,
                unique=True,
                verbose_name="Short name",
            ),
        ),
    ]