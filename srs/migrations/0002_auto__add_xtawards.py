# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'XTAwards'
        db.create_table(u'srs_xtawards', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('replay', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Replay'])),
            ('isAlive', self.gf('django.db.models.fields.SmallIntegerField')(default=-1)),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['srs.Player'])),
            ('unit', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('kills', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('age', self.gf('django.db.models.fields.IntegerField')(default=-1)),
        ))
        db.send_create_signal(u'srs', ['XTAwards'])


    def backwards(self, orm):
        # Deleting model 'XTAwards'
        db.delete_table(u'srs_xtawards')


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
        },
        u'srs.xtawards': {
            'Meta': {'object_name': 'XTAwards'},
            'age': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isAlive': ('django.db.models.fields.SmallIntegerField', [], {'default': '-1'}),
            'kills': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Player']"}),
            'replay': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['srs.Replay']"}),
            'unit': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
        }
    }

    complete_apps = ['srs']