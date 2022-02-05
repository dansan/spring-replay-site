# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-01 19:39
from __future__ import unicode_literals

import django.db.models.deletion
import picklefield.fields  # removed with #124 (pip install django-picklefield==2.0)
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AdditionalReplayInfo",
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
                ("key", models.CharField(max_length=32)),
                ("value", models.CharField(max_length=512)),
            ],
        ),
        migrations.CreateModel(
            name="AdditionalReplayOwner",
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
            ],
            options={
                "ordering": ["uploader__username"],
            },
        ),
        migrations.CreateModel(
            name="Allyteam",
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
                ("numallies", models.IntegerField()),
                ("startrectbottom", models.FloatField(blank=True, null=True)),
                ("startrectleft", models.FloatField(blank=True, null=True)),
                ("startrectright", models.FloatField(blank=True, null=True)),
                ("startrecttop", models.FloatField(blank=True, null=True)),
                ("winner", models.BooleanField(default=False)),
                ("num", models.SmallIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name="BAwards",
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
                ("ecoKillAward1stScore", models.IntegerField(default=-1)),
                ("ecoKillAward2ndScore", models.IntegerField(default=-1)),
                ("ecoKillAward3rdScore", models.IntegerField(default=-1)),
                ("fightKillAward1stScore", models.IntegerField(default=-1)),
                ("fightKillAward2ndScore", models.IntegerField(default=-1)),
                ("fightKillAward3rdScore", models.IntegerField(default=-1)),
                ("effKillAward1stScore", models.FloatField(default=-1)),
                ("effKillAward2ndScore", models.FloatField(default=-1)),
                ("effKillAward3rdScore", models.FloatField(default=-1)),
                ("cowAwardScore", models.IntegerField(default=-1)),
                ("ecoAwardScore", models.IntegerField(default=-1)),
                ("dmgRecAwardScore", models.FloatField(default=-1)),
                ("sleepAwardScore", models.IntegerField(default=-1)),
            ],
        ),
        migrations.CreateModel(
            name="ExtraReplayMedia",
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
                ("upload_date", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("comment", models.CharField(max_length=513)),
                ("media", models.FileField(blank=True, upload_to=b"media/%Y/%m/%d")),
                ("image", models.ImageField(blank=True, upload_to=b"image/%Y/%m/%d")),
                (
                    "media_magic_text",
                    models.CharField(blank=True, max_length=1024, null=True),
                ),
                (
                    "media_magic_mime",
                    models.CharField(blank=True, max_length=128, null=True),
                ),
            ],
            options={
                "ordering": ["-upload_date"],
            },
        ),
        migrations.CreateModel(
            name="Game",
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
                ("name", models.CharField(db_index=True, max_length=256)),
                ("abbreviation", models.CharField(db_index=True, max_length=64)),
                ("sldb_name", models.CharField(db_index=True, max_length=64)),
                (
                    "developer",
                    models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="GameRelease",
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
                ("name", models.CharField(db_index=True, max_length=256)),
                ("version", models.CharField(max_length=64)),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Game"),
                ),
            ],
            options={
                "ordering": ["name", "version"],
            },
        ),
        migrations.CreateModel(
            name="Map",
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
                ("name", models.CharField(db_index=True, max_length=128)),
                ("startpos", models.CharField(blank=True, max_length=1024, null=True)),
                ("height", models.IntegerField()),
                ("width", models.IntegerField()),
                (
                    "metadata",
                    picklefield.fields.PickledObjectField(blank=True, editable=False, null=True),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="MapImg",
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
                ("filename", models.CharField(max_length=128)),
                (
                    "startpostype",
                    models.IntegerField(blank=True, null=True, verbose_name=b"-1 means full image"),
                ),
                (
                    "map_info",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Map"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MapModOption",
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
                ("name", models.CharField(max_length=128)),
                ("value", models.CharField(max_length=512)),
            ],
        ),
        migrations.CreateModel(
            name="NewsItem",
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
                ("text", models.CharField(max_length=256)),
                ("post_date", models.DateTimeField(auto_now=True)),
                ("show", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Player",
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
                ("name", models.CharField(db_index=True, max_length=128)),
                ("rank", models.SmallIntegerField()),
                ("skill", models.CharField(blank=True, max_length=16)),
                ("skilluncertainty", models.SmallIntegerField(blank=True, default=-1)),
                ("spectator", models.BooleanField(default=False)),
                ("startposx", models.FloatField(blank=True, null=True)),
                ("startposy", models.FloatField(blank=True, null=True)),
                ("startposz", models.FloatField(blank=True, null=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="PlayerAccount",
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
                ("accountid", models.IntegerField(unique=True)),
                ("countrycode", models.CharField(max_length=2)),
                ("preffered_name", models.CharField(db_index=True, max_length=128)),
                ("sldb_privacy_mode", models.SmallIntegerField(default=1)),
            ],
            options={
                "ordering": ["accountid"],
            },
        ),
        migrations.CreateModel(
            name="Rating",
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
                (
                    "match_type",
                    models.CharField(
                        choices=[
                            (b"1", "1v1"),
                            (b"T", "Team"),
                            (b"F", "FFA"),
                            (b"G", "TeamFFA"),
                            (b"L", "Global"),
                        ],
                        db_index=True,
                        max_length=1,
                    ),
                ),
                (
                    "playername",
                    models.CharField(blank=True, db_index=True, max_length=128, null=True),
                ),
                ("trueskill_mu", models.FloatField(default=25.0)),
                ("trueskill_sigma", models.FloatField(default=8.333333333333334)),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Game"),
                ),
                (
                    "playeraccount",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="srs.PlayerAccount",
                    ),
                ),
            ],
            options={
                "ordering": ["-trueskill_mu"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="RatingHistory",
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
                (
                    "match_type",
                    models.CharField(
                        choices=[
                            (b"1", "1v1"),
                            (b"T", "Team"),
                            (b"F", "FFA"),
                            (b"G", "TeamFFA"),
                            (b"L", "Global"),
                        ],
                        db_index=True,
                        max_length=1,
                    ),
                ),
                (
                    "playername",
                    models.CharField(blank=True, db_index=True, max_length=128, null=True),
                ),
                ("trueskill_mu", models.FloatField(default=25.0)),
                ("trueskill_sigma", models.FloatField(default=8.333333333333334)),
                (
                    "match_date",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Game"),
                ),
            ],
            options={
                "ordering": ["-match_date", "playername"],
            },
        ),
        migrations.CreateModel(
            name="Replay",
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
                ("versionString", models.CharField(max_length=32)),
                ("gameID", models.CharField(db_index=True, max_length=32, unique=True)),
                (
                    "unixTime",
                    models.DateTimeField(db_index=True, verbose_name=b"date of match"),
                ),
                (
                    "wallclockTime",
                    models.CharField(max_length=32, verbose_name=b"length of match"),
                ),
                (
                    "autohostname",
                    models.CharField(blank=True, db_index=True, max_length=128, null=True),
                ),
                ("gametype", models.CharField(db_index=True, max_length=256)),
                ("startpostype", models.IntegerField(blank=True, null=True)),
                ("title", models.CharField(db_index=True, max_length=256)),
                ("short_text", models.CharField(db_index=True, max_length=50)),
                ("long_text", models.CharField(db_index=True, max_length=513)),
                ("notcomplete", models.BooleanField(default=True)),
                ("upload_date", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("filename", models.CharField(max_length=256)),
                ("path", models.CharField(max_length=256)),
                ("download_count", models.IntegerField(default=0)),
                ("comment_count", models.IntegerField(default=0)),
                ("rated", models.BooleanField(default=False)),
                ("published", models.BooleanField(default=False)),
                (
                    "map_img",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="srs.MapImg",
                    ),
                ),
                (
                    "map_info",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="srs.Map",
                    ),
                ),
            ],
            options={
                "ordering": ["-upload_date"],
                "get_latest_by": "upload_date",
            },
        ),
        migrations.CreateModel(
            name="SiteStats",
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
                ("last_modified", models.DateTimeField(auto_now=True)),
                ("replays", models.IntegerField()),
                ("tags", models.CharField(max_length=1000)),
                ("maps", models.CharField(max_length=1000)),
                ("active_players", models.CharField(max_length=1000)),
                ("all_players", picklefield.fields.PickledObjectField(editable=False)),
                ("comments", models.CharField(max_length=1000)),
                ("games", models.CharField(max_length=1000)),
                ("bawards", picklefield.fields.PickledObjectField(editable=False)),
            ],
        ),
        migrations.CreateModel(
            name="SldbLeaderboardGame",
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
                ("last_modified", models.DateTimeField(auto_now_add=True)),
                (
                    "match_type",
                    models.CharField(
                        choices=[
                            (b"1", "1v1"),
                            (b"T", "Team"),
                            (b"F", "FFA"),
                            (b"G", "TeamFFA"),
                            (b"L", "Global"),
                        ],
                        db_index=True,
                        max_length=1,
                    ),
                ),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Game"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SldbLeaderboardPlayer",
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
                ("rank", models.IntegerField()),
                ("trusted_skill", models.FloatField()),
                ("estimated_skill", models.FloatField()),
                ("uncertainty", models.FloatField()),
                ("inactivity", models.IntegerField()),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="srs.PlayerAccount",
                    ),
                ),
                (
                    "leaderboard",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="srs.SldbLeaderboardGame",
                    ),
                ),
            ],
            options={
                "ordering": ["rank"],
            },
        ),
        migrations.CreateModel(
            name="SldbMatchSkillsCache",
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
                ("last_modified", models.DateTimeField(auto_now_add=True)),
                ("gameID", models.CharField(db_index=True, max_length=32, unique=True)),
                ("text", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="SldbPlayerTSGraphCache",
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
                ("last_modified", models.DateTimeField(auto_now_add=True)),
                ("filepath_global", models.CharField(max_length=256)),
                ("filepath_duel", models.CharField(max_length=256)),
                ("filepath_ffa", models.CharField(max_length=256)),
                ("filepath_team", models.CharField(max_length=256)),
                ("filepath_teamffa", models.CharField(max_length=256)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="srs.PlayerAccount",
                    ),
                ),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Game"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Tag",
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
                ("name", models.CharField(db_index=True, max_length=128, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Team",
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
                ("handicap", models.IntegerField()),
                ("rgbcolor", models.CharField(max_length=23)),
                ("side", models.CharField(max_length=32)),
                ("startposx", models.IntegerField(blank=True, null=True)),
                ("startposy", models.IntegerField(blank=True, null=True)),
                ("startposz", models.IntegerField(blank=True, null=True)),
                ("num", models.SmallIntegerField()),
                (
                    "allyteam",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Allyteam"),
                ),
                (
                    "replay",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
                ),
                (
                    "teamleader",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="srs.Player",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UploadTmp",
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
                (
                    "replay",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="XTAwards",
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
                ("isAlive", models.SmallIntegerField(default=-1)),
                ("unit", models.CharField(max_length=1024)),
                ("kills", models.IntegerField(default=-1)),
                ("age", models.IntegerField(default=-1)),
                (
                    "player",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Player"),
                ),
                (
                    "replay",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MapOption",
            fields=[
                (
                    "mapmodoption_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="srs.MapModOption",
                    ),
                ),
            ],
            bases=("srs.mapmodoption",),
        ),
        migrations.CreateModel(
            name="ModOption",
            fields=[
                (
                    "mapmodoption_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="srs.MapModOption",
                    ),
                ),
            ],
            bases=("srs.mapmodoption",),
        ),
        migrations.AddField(
            model_name="replay",
            name="tags",
            field=models.ManyToManyField(to="srs.Tag"),
        ),
        migrations.AddField(
            model_name="replay",
            name="uploader",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="ratinghistory",
            name="match",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
        ),
        migrations.AddField(
            model_name="ratinghistory",
            name="playeraccount",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.PlayerAccount"),
        ),
        migrations.AddField(
            model_name="player",
            name="account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="srs.PlayerAccount",
            ),
        ),
        migrations.AddField(
            model_name="player",
            name="replay",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
        ),
        migrations.AddField(
            model_name="player",
            name="team",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="srs.Team",
            ),
        ),
        migrations.AddField(
            model_name="mapmodoption",
            name="replay",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
        ),
        migrations.AddField(
            model_name="extrareplaymedia",
            name="replay",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
        ),
        migrations.AddField(
            model_name="extrareplaymedia",
            name="uploader",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="bawards",
            name="cowAward",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="dmgRecAward",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="ecoAward",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="ecoKillAward1st",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="ecoKillAward2nd",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="ecoKillAward3rd",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="effKillAward1st",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="effKillAward2nd",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="effKillAward3rd",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="fightKillAward1st",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="fightKillAward2nd",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="fightKillAward3rd",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="bawards",
            name="replay",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
        ),
        migrations.AddField(
            model_name="bawards",
            name="sleepAward",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="srs.Player",
            ),
        ),
        migrations.AddField(
            model_name="allyteam",
            name="replay",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
        ),
        migrations.AddField(
            model_name="additionalreplayowner",
            name="additional_owner",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.PlayerAccount"),
        ),
        migrations.AddField(
            model_name="additionalreplayowner",
            name="uploader",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="additionalreplayinfo",
            name="replay",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="srs.Replay"),
        ),
    ]
