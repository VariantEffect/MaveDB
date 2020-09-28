# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-09-07 01:58
from __future__ import unicode_literals

from django.db import migrations, models
import functools
import variant.validators.hgvs


class Migration(migrations.Migration):

    dependencies = [
        ("variant", "0006_variant_hgvs_tx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="variant",
            name="hgvs_nt",
            field=models.TextField(
                default=None,
                null=True,
                validators=[variant.validators.hgvs.validate_nt_variant],
            ),
        ),
        migrations.AlterField(
            model_name="variant",
            name="hgvs_pro",
            field=models.TextField(
                default=None,
                null=True,
                validators=[variant.validators.hgvs.validate_pro_variant],
            ),
        ),
    ]