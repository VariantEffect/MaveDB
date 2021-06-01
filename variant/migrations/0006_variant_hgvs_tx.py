# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-08-18 06:44
from __future__ import unicode_literals

from django.db import migrations, models
import variant.validators.hgvs


class Migration(migrations.Migration):

    dependencies = [
        ("variant", "0005_auto_20190729_1501"),
    ]

    operations = [
        migrations.AddField(
            model_name="variant",
            name="hgvs_tx",
            field=models.TextField(
                default=None,
                null=True,
                validators=[variant.validators.hgvs.validate_splice_variant],
            ),
        ),
    ]
