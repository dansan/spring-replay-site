# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-01-27 08:51
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("srs", "0008_map_metadata2"),
    ]

    operations = [
        migrations.RemoveField(model_name="map", name="metadata",),
    ]
