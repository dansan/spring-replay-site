# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Tag'
        db.create_table(u'srs_tag', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128, db_index=True)),
        ))
        db.send_create_signal(u'srs', ['Tag'])

        # Adding model 'Map'
        db.create_table(u'srs_map', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('startpos', self.gf('django.db.models.fields.CharField')(max_length=1024, null=True, blank=True)),
            ('height', self.gf('django.db.models.fields.IntegerField')()),
            ('width', self.gf('django.db.models.fields.IntegerField')()),
            ('metadata', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'srs', ['Map'])

        # Adding model 'MapImg'
        db.create_table(u'srs_mapimg', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('startpostype', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('map_info', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Map'])),
        ))
        db.send_create_signal(u'srs', ['MapImg'])

        # Adding model 'Replay'
        db.create_table(u'srs_replay', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('versionString', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('gameID', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32, db_index=True)),
            ('unixTime', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('wallclockTime', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('autohostname', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=128, null=True, blank=True)),
            ('gametype', self.gf('django.db.models.fields.CharField')(max_length=256, db_index=True)),
            ('startpostype', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=256, db_index=True)),
            ('short_text', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
            ('long_text', self.gf('django.db.models.fields.CharField')(max_length=513, db_index=True)),
            ('notcomplete', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('map_info', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Map'], null=True, blank=True)),
            ('map_img', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.MapImg'], null=True, blank=True)),
            ('uploader', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('upload_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('download_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('comment_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('rated', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'srs', ['Replay'])

        # Adding M2M table for field tags on 'Replay'
        m2m_table_name = db.shorten_name(u'srs_replay_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('replay', models.ForeignKey(orm[u'srs.replay'], null=False)),
            ('tag', models.ForeignKey(orm[u'srs.tag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['replay_id', 'tag_id'])

        # Adding model 'AdditionalReplayInfo'
        db.create_table(u'srs_additionalreplayinfo', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('replay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=512)),
        ))
        db.send_create_signal(u'srs', ['AdditionalReplayInfo'])

        # Adding model 'Allyteam'
        db.create_table(u'srs_allyteam', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('numallies', self.gf('django.db.models.fields.IntegerField')()),
            ('startrectbottom', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('startrectleft', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('startrectright', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('startrecttop', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('winner', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('replay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
            ('num', self.gf('django.db.models.fields.SmallIntegerField')()),
        ))
        db.send_create_signal(u'srs', ['Allyteam'])

        # Adding model 'PlayerAccount'
        db.create_table(u'srs_playeraccount', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('accountid', self.gf('django.db.models.fields.IntegerField')(unique=True)),
            ('countrycode', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('preffered_name', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('sldb_privacy_mode', self.gf('django.db.models.fields.SmallIntegerField')(default=1)),
        ))
        db.send_create_signal(u'srs', ['PlayerAccount'])

        # Adding model 'Player'
        db.create_table(u'srs_player', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('account', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.PlayerAccount'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('rank', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('skill', self.gf('django.db.models.fields.CharField')(max_length=16, blank=True)),
            ('skilluncertainty', self.gf('django.db.models.fields.SmallIntegerField')(default=-1, blank=True)),
            ('spectator', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('team', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Team'], null=True, blank=True)),
            ('replay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
            ('startposx', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('startposy', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('startposz', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'srs', ['Player'])

        # Adding model 'Team'
        db.create_table(u'srs_team', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('allyteam', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Allyteam'])),
            ('handicap', self.gf('django.db.models.fields.IntegerField')()),
            ('rgbcolor', self.gf('django.db.models.fields.CharField')(max_length=23)),
            ('side', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('startposx', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('startposy', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('startposz', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('teamleader', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', to=orm['srs.Player'])),
            ('replay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
            ('num', self.gf('django.db.models.fields.SmallIntegerField')()),
        ))
        db.send_create_signal(u'srs', ['Team'])

        # Adding model 'MapModOption'
        db.create_table(u'srs_mapmodoption', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('replay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
        ))
        db.send_create_signal(u'srs', ['MapModOption'])

        # Adding model 'MapOption'
        db.create_table(u'srs_mapoption', (
            (u'mapmodoption_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['srs.MapModOption'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'srs', ['MapOption'])

        # Adding model 'ModOption'
        db.create_table(u'srs_modoption', (
            (u'mapmodoption_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['srs.MapModOption'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'srs', ['ModOption'])

        # Adding model 'NewsItem'
        db.create_table(u'srs_newsitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('post_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('show', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'srs', ['NewsItem'])

        # Adding model 'UploadTmp'
        db.create_table(u'srs_uploadtmp', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('replay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
        ))
        db.send_create_signal(u'srs', ['UploadTmp'])

        # Adding model 'SiteStats'
        db.create_table(u'srs_sitestats', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('replays', self.gf('django.db.models.fields.IntegerField')()),
            ('tags', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('maps', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('active_players', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('all_players', self.gf('picklefield.fields.PickledObjectField')()),
            ('comments', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('games', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('bawards', self.gf('picklefield.fields.PickledObjectField')()),
        ))
        db.send_create_signal(u'srs', ['SiteStats'])

        # Adding model 'Game'
        db.create_table(u'srs_game', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256, db_index=True)),
            ('abbreviation', self.gf('django.db.models.fields.CharField')(max_length=64, db_index=True)),
            ('sldb_name', self.gf('django.db.models.fields.CharField')(max_length=64, db_index=True)),
        ))
        db.send_create_signal(u'srs', ['Game'])

        # Adding model 'GameRelease'
        db.create_table(u'srs_gamerelease', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256, db_index=True)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Game'])),
        ))
        db.send_create_signal(u'srs', ['GameRelease'])

        # Adding model 'Rating'
        db.create_table(u'srs_rating', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Game'])),
            ('match_type', self.gf('django.db.models.fields.CharField')(max_length=1, db_index=True)),
            ('playeraccount', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.PlayerAccount'])),
            ('playername', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=128, null=True, blank=True)),
            ('trueskill_mu', self.gf('django.db.models.fields.FloatField')(default=25.0)),
            ('trueskill_sigma', self.gf('django.db.models.fields.FloatField')(default=8.333333333333334)),
        ))
        db.send_create_signal(u'srs', ['Rating'])

        # Adding model 'RatingHistory'
        db.create_table(u'srs_ratinghistory', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Game'])),
            ('match_type', self.gf('django.db.models.fields.CharField')(max_length=1, db_index=True)),
            ('playeraccount', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.PlayerAccount'])),
            ('playername', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=128, null=True, blank=True)),
            ('trueskill_mu', self.gf('django.db.models.fields.FloatField')(default=25.0)),
            ('trueskill_sigma', self.gf('django.db.models.fields.FloatField')(default=8.333333333333334)),
            ('match', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
            ('match_date', self.gf('django.db.models.fields.DateTimeField')(db_index=True, null=True, blank=True)),
        ))
        db.send_create_signal(u'srs', ['RatingHistory'])

        # Adding model 'AdditionalReplayOwner'
        db.create_table(u'srs_additionalreplayowner', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uploader', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('additional_owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.PlayerAccount'])),
        ))
        db.send_create_signal(u'srs', ['AdditionalReplayOwner'])

        # Adding model 'ExtraReplayMedia'
        db.create_table(u'srs_extrareplaymedia', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('replay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
            ('uploader', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('upload_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.CharField')(max_length=513)),
            ('media', self.gf('django.db.models.fields.files.FileField')(max_length=100, blank=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('media_magic_text', self.gf('django.db.models.fields.CharField')(max_length=1024, null=True, blank=True)),
            ('media_magic_mime', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
        ))
        db.send_create_signal(u'srs', ['ExtraReplayMedia'])

        # Adding model 'SldbLeaderboardGame'
        db.create_table(u'srs_sldbleaderboardgame', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Game'])),
            ('match_type', self.gf('django.db.models.fields.CharField')(max_length=1, db_index=True)),
        ))
        db.send_create_signal(u'srs', ['SldbLeaderboardGame'])

        # Adding model 'SldbLeaderboardPlayer'
        db.create_table(u'srs_sldbleaderboardplayer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('leaderboard', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.SldbLeaderboardGame'])),
            ('account', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.PlayerAccount'])),
            ('rank', self.gf('django.db.models.fields.IntegerField')()),
            ('trusted_skill', self.gf('django.db.models.fields.FloatField')()),
            ('estimated_skill', self.gf('django.db.models.fields.FloatField')()),
            ('uncertainty', self.gf('django.db.models.fields.FloatField')()),
            ('inactivity', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'srs', ['SldbLeaderboardPlayer'])

        # Adding model 'SldbMatchSkillsCache'
        db.create_table(u'srs_sldbmatchskillscache', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('gameID', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32, db_index=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'srs', ['SldbMatchSkillsCache'])

        # Adding model 'BAwards'
        db.create_table(u'srs_bawards', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('replay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
            ('ecoKillAward1st', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('ecoKillAward1stScore', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('ecoKillAward2nd', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('ecoKillAward2ndScore', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('ecoKillAward3rd', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('ecoKillAward3rdScore', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('fightKillAward1st', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('fightKillAward1stScore', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('fightKillAward2nd', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('fightKillAward2ndScore', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('fightKillAward3rd', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('fightKillAward3rdScore', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('effKillAward1st', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('effKillAward1stScore', self.gf('django.db.models.fields.FloatField')(default=-1)),
            ('effKillAward2nd', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('effKillAward2ndScore', self.gf('django.db.models.fields.FloatField')(default=-1)),
            ('effKillAward3rd', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('effKillAward3rdScore', self.gf('django.db.models.fields.FloatField')(default=-1)),
            ('cowAward', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('cowAwardScore', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('ecoAward', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('ecoAwardScore', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('dmgRecAward', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('dmgRecAwardScore', self.gf('django.db.models.fields.FloatField')(default=-1)),
            ('sleepAward', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='+', null=True, to=orm['srs.Player'])),
            ('sleepAwardScore', self.gf('django.db.models.fields.IntegerField')(default=-1)),
        ))
        db.send_create_signal(u'srs', ['BAwards'])


    def backwards(self, orm):
        # Deleting model 'Tag'
        db.delete_table(u'srs_tag')

        # Deleting model 'Map'
        db.delete_table(u'srs_map')

        # Deleting model 'MapImg'
        db.delete_table(u'srs_mapimg')

        # Deleting model 'Replay'
        db.delete_table(u'srs_replay')

        # Removing M2M table for field tags on 'Replay'
        db.delete_table(db.shorten_name(u'srs_replay_tags'))

        # Deleting model 'AdditionalReplayInfo'
        db.delete_table(u'srs_additionalreplayinfo')

        # Deleting model 'Allyteam'
        db.delete_table(u'srs_allyteam')

        # Deleting model 'PlayerAccount'
        db.delete_table(u'srs_playeraccount')

        # Deleting model 'Player'
        db.delete_table(u'srs_player')

        # Deleting model 'Team'
        db.delete_table(u'srs_team')

        # Deleting model 'MapModOption'
        db.delete_table(u'srs_mapmodoption')

        # Deleting model 'MapOption'
        db.delete_table(u'srs_mapoption')

        # Deleting model 'ModOption'
        db.delete_table(u'srs_modoption')

        # Deleting model 'NewsItem'
        db.delete_table(u'srs_newsitem')

        # Deleting model 'UploadTmp'
        db.delete_table(u'srs_uploadtmp')

        # Deleting model 'SiteStats'
        db.delete_table(u'srs_sitestats')

        # Deleting model 'Game'
        db.delete_table(u'srs_game')

        # Deleting model 'GameRelease'
        db.delete_table(u'srs_gamerelease')

        # Deleting model 'Rating'
        db.delete_table(u'srs_rating')

        # Deleting model 'RatingHistory'
        db.delete_table(u'srs_ratinghistory')

        # Deleting model 'AdditionalReplayOwner'
        db.delete_table(u'srs_additionalreplayowner')

        # Deleting model 'ExtraReplayMedia'
        db.delete_table(u'srs_extrareplaymedia')

        # Deleting model 'SldbLeaderboardGame'
        db.delete_table(u'srs_sldbleaderboardgame')

        # Deleting model 'SldbLeaderboardPlayer'
        db.delete_table(u'srs_sldbleaderboardplayer')

        # Deleting model 'SldbMatchSkillsCache'
        db.delete_table(u'srs_sldbmatchskillscache')

        # Deleting model 'BAwards'
        db.delete_table(u'srs_bawards')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'srs.additionalreplayinfo': {
            'Meta': {'object_name': 'AdditionalReplayInfo'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'replay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        u'srs.additionalreplayowner': {
            'Meta': {'ordering': "['uploader__username']", 'object_name': 'AdditionalReplayOwner'},
            'additional_owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.PlayerAccount']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'uploader': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'srs.allyteam': {
            'Meta': {'object_name': 'Allyteam'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num': ('django.db.models.fields.SmallIntegerField', [], {}),
            'numallies': ('django.db.models.fields.IntegerField', [], {}),
            'replay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"}),
            'startrectbottom': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'startrectleft': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'startrectright': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'startrecttop': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'winner': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'srs.bawards': {
            'Meta': {'object_name': 'BAwards'},
            'cowAward': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'cowAwardScore': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'dmgRecAward': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'dmgRecAwardScore': ('django.db.models.fields.FloatField', [], {'default': '-1'}),
            'ecoAward': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'ecoAwardScore': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'ecoKillAward1st': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'ecoKillAward1stScore': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'ecoKillAward2nd': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'ecoKillAward2ndScore': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'ecoKillAward3rd': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'ecoKillAward3rdScore': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'effKillAward1st': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'effKillAward1stScore': ('django.db.models.fields.FloatField', [], {'default': '-1'}),
            'effKillAward2nd': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'effKillAward2ndScore': ('django.db.models.fields.FloatField', [], {'default': '-1'}),
            'effKillAward3rd': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'effKillAward3rdScore': ('django.db.models.fields.FloatField', [], {'default': '-1'}),
            'fightKillAward1st': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'fightKillAward1stScore': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'fightKillAward2nd': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'fightKillAward2ndScore': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'fightKillAward3rd': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'fightKillAward3rdScore': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'replay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"}),
            'sleepAward': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'+'", 'null': 'True', 'to': u"orm['srs.Player']"}),
            'sleepAwardScore': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        u'srs.extrareplaymedia': {
            'Meta': {'ordering': "['-upload_date']", 'object_name': 'ExtraReplayMedia'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '513'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'media': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'media_magic_mime': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'media_magic_text': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'replay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"}),
            'upload_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'uploader': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'srs.game': {
            'Meta': {'ordering': "['name']", 'object_name': 'Game'},
            'abbreviation': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'db_index': 'True'}),
            'sldb_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'})
        },
        u'srs.gamerelease': {
            'Meta': {'ordering': "['name', 'version']", 'object_name': 'GameRelease'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'db_index': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        u'srs.map': {
            'Meta': {'ordering': "['name']", 'object_name': 'Map'},
            'height': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'metadata': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'startpos': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        u'srs.mapimg': {
            'Meta': {'object_name': 'MapImg'},
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'map_info': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Map']"}),
            'startpostype': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'srs.mapmodoption': {
            'Meta': {'object_name': 'MapModOption'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'replay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        u'srs.mapoption': {
            'Meta': {'object_name': 'MapOption', '_ormbases': [u'srs.MapModOption']},
            u'mapmodoption_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['srs.MapModOption']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'srs.modoption': {
            'Meta': {'object_name': 'ModOption', '_ormbases': [u'srs.MapModOption']},
            u'mapmodoption_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['srs.MapModOption']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'srs.newsitem': {
            'Meta': {'object_name': 'NewsItem'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'show': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        u'srs.player': {
            'Meta': {'ordering': "['name']", 'object_name': 'Player'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.PlayerAccount']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'rank': ('django.db.models.fields.SmallIntegerField', [], {}),
            'replay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"}),
            'skill': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'skilluncertainty': ('django.db.models.fields.SmallIntegerField', [], {'default': '-1', 'blank': 'True'}),
            'spectator': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'startposx': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'startposy': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'startposz': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'team': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Team']", 'null': 'True', 'blank': 'True'})
        },
        u'srs.playeraccount': {
            'Meta': {'ordering': "['accountid']", 'object_name': 'PlayerAccount'},
            'accountid': ('django.db.models.fields.IntegerField', [], {'unique': 'True'}),
            'countrycode': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'preffered_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'sldb_privacy_mode': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'})
        },
        u'srs.rating': {
            'Meta': {'ordering': "['-trueskill_mu']", 'object_name': 'Rating'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'match_type': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'playeraccount': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.PlayerAccount']"}),
            'playername': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'trueskill_mu': ('django.db.models.fields.FloatField', [], {'default': '25.0'}),
            'trueskill_sigma': ('django.db.models.fields.FloatField', [], {'default': '8.333333333333334'})
        },
        u'srs.ratinghistory': {
            'Meta': {'ordering': "['-match_date', 'playername']", 'object_name': 'RatingHistory'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'match': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"}),
            'match_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'match_type': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'}),
            'playeraccount': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.PlayerAccount']"}),
            'playername': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'trueskill_mu': ('django.db.models.fields.FloatField', [], {'default': '25.0'}),
            'trueskill_sigma': ('django.db.models.fields.FloatField', [], {'default': '8.333333333333334'})
        },
        u'srs.replay': {
            'Meta': {'ordering': "['-upload_date']", 'object_name': 'Replay'},
            'autohostname': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'comment_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'download_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'gameID': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32', 'db_index': 'True'}),
            'gametype': ('django.db.models.fields.CharField', [], {'max_length': '256', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'long_text': ('django.db.models.fields.CharField', [], {'max_length': '513', 'db_index': 'True'}),
            'map_img': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.MapImg']", 'null': 'True', 'blank': 'True'}),
            'map_info': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Map']", 'null': 'True', 'blank': 'True'}),
            'notcomplete': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'short_text': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'startpostype': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['srs.Tag']", 'symmetrical': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256', 'db_index': 'True'}),
            'unixTime': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'upload_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'uploader': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'versionString': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'wallclockTime': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'srs.sitestats': {
            'Meta': {'object_name': 'SiteStats'},
            'active_players': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'all_players': ('picklefield.fields.PickledObjectField', [], {}),
            'bawards': ('picklefield.fields.PickledObjectField', [], {}),
            'comments': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'games': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'maps': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'replays': ('django.db.models.fields.IntegerField', [], {}),
            'tags': ('django.db.models.fields.CharField', [], {'max_length': '1000'})
        },
        u'srs.sldbleaderboardgame': {
            'Meta': {'object_name': 'SldbLeaderboardGame'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Game']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'match_type': ('django.db.models.fields.CharField', [], {'max_length': '1', 'db_index': 'True'})
        },
        u'srs.sldbleaderboardplayer': {
            'Meta': {'ordering': "['rank']", 'object_name': 'SldbLeaderboardPlayer'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.PlayerAccount']"}),
            'estimated_skill': ('django.db.models.fields.FloatField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inactivity': ('django.db.models.fields.IntegerField', [], {}),
            'leaderboard': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.SldbLeaderboardGame']"}),
            'rank': ('django.db.models.fields.IntegerField', [], {}),
            'trusted_skill': ('django.db.models.fields.FloatField', [], {}),
            'uncertainty': ('django.db.models.fields.FloatField', [], {})
        },
        u'srs.sldbmatchskillscache': {
            'Meta': {'object_name': 'SldbMatchSkillsCache'},
            'gameID': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'srs.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128', 'db_index': 'True'})
        },
        u'srs.team': {
            'Meta': {'object_name': 'Team'},
            'allyteam': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Allyteam']"}),
            'handicap': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num': ('django.db.models.fields.SmallIntegerField', [], {}),
            'replay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"}),
            'rgbcolor': ('django.db.models.fields.CharField', [], {'max_length': '23'}),
            'side': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'startposx': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'startposy': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'startposz': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'teamleader': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['srs.Player']"})
        },
        u'srs.uploadtmp': {
            'Meta': {'object_name': 'UploadTmp'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'replay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"})
        }
    }

    complete_apps = ['srs']