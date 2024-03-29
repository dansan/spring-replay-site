# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-08-25 20:40
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("srs", "0006_playerstats"),
    ]

    operations = [
        migrations.CreateModel(
            name="TeamStats",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("stat_type", models.CharField(max_length=32)),
                ("stats", models.BinaryField(blank=True, default=None, null=True)),
                (
                    "replay",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
                ),
            ],
        ),
    ]
