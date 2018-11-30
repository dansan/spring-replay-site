from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
import django.contrib.sitemaps.views

from srs.feeds import LatestUploadsFeed, GameFeed, UploaderFeed, SRSLatestCommentFeed
from srs.sitemap import ReplaySitemap, PlayerAccountSitemap, HofSitemap
from srs.views import (all_comments, browse_archive, download, edit_replay, hall_of_fame, index, index_replay_range,
                       login, logout, media, player, replay, replay_by_id, sldb_privacy_mode, team_stat_div,
                       ts_history_graph, user_settings)
from srs.ajax_views import (BrowseReplaysDTView, CommentDTView, ajax_map_lookup, ajax_player_lookup,
                            ajax_playerrating_tbl_src, ajax_playerreplays_tbl_src, ajax_winloss_tbl_src,
                            gamerelease_modal, hof_tbl_src, maplinks_modal, modlinks_modal, ratinghistorygraph_modal,
                            stats_modal, enginelinks_modal)
from srs.upload_views import upload, upload_media
import django_xmlrpc.views

admin.autodiscover()

sitemaps = {'replays': ReplaySitemap,
            'players': PlayerAccountSitemap,
            'hall of fame': HofSitemap}

urlpatterns = [url(r'^$', index, name='srs/index'),
               url(r'^index_replay_range/(?P<range_end>[\d]+)/(?P<game_pref>[\d]+)/$', index_replay_range,
                   name='srs/index_replay_range'),
               url(r'^djangojs/', include('djangojs.urls')),
               url(r'^sitemap\.xml$', django.contrib.sitemaps.views.sitemap, {'sitemaps': sitemaps}),
               url(r'^upload/$', upload, name='srs/upload'),
               url(r'^upload_media/(?P<gameID>[0-9,a-f]+)/$', upload_media, name='srs/upload_media'),
               url(r'^media/(?P<mediaid>[0-9]+)/$', media, name='srs/media'),
               url(r'^settings/$', user_settings, name='srs/settings'),
               url(r'^login/$', login, name='srs/login'),
               url(r'^logout/$', logout, name='srs/logout'),
               url(r'^all_comments/', all_comments, name='srs/all_comments'),
               url(r'^comment_tbl_src$', CommentDTView.as_view(), name='srs/comment_tbl_src$'),
               url(r'^comments/', include('django_comments.urls')),
               url(r'^download/(?P<gameID>[0-9a-f]+)/$', download, name='srs/download'),
               url(r'^admin/', admin.site.urls),
               url(r'^xmlrpc/$', django_xmlrpc.views.handle_xmlrpc, name='srs/xmlrpc'),
               url(r'^maplinks_modal/(?P<gameID>[0-9a-f]+)/$', maplinks_modal, name='srs/maplinks_modal'),
               url(r'^modlinks_modal/(?P<gameID>[0-9a-f]+)/$', modlinks_modal, name='srs/modlinks_modal'),
               url(r'^enginelinks_modal/(?P<gameID>[0-9a-f]+)/$', enginelinks_modal, name='srs/enginelinks_modal'),
               url(r'^stats_modal/(?P<gameID>[0-9a-f]+)/$', stats_modal, name='srs/stats_modal'),
               url(r'^feeds/latest_comments/$', SRSLatestCommentFeed(), name='srs/feeds/latest_comments'),
               url(r'^feeds/latest/$', LatestUploadsFeed(), name='srs/feeds/latest'),
               url(r'^feeds/game/(?P<game>[\w ]+)/$', GameFeed(), name='srs/feeds/game'),
               url(r'^feeds/uploader/(?P<username>[\w\ .:()\[\]-]+)/$', UploaderFeed(), name='srs/feeds/uploader'),
               url(r'^sldb_privacy_mode/$', sldb_privacy_mode, name='srs/sldb_privacy_mode'),
               url(r'^browse/(?P<bfilter>.*)$', browse_archive, name='srs/browse_archive'),
               url(r'^browse_tbl_src$', BrowseReplaysDTView.as_view(), name='srs/browse_tbl_src'),
               url(r'^replay/(?P<gameID>[0-9,a-f]+)/$', replay, name='srs/replay'),
               url(r'^replay_by_id/(?P<replayid>[\d-]+)/$', replay_by_id, name='srs/replay_by_id'),
               url(r'^edit_replay/(?P<gameID>[0-9a-f]+)/$', edit_replay, name='srs/edit_replay'),
               url(r'^player/(?P<accountid>[\d-]+)/$', player, name='srs/player'),
               url(r'^ts_history_graph/(?P<game_abbr>[A-Z0-9]+)/(?P<accountid>[\d]+)/(?P<match_type>[1TFGL])/$',
                   ts_history_graph, name='srs/ts_history_graph'),
               url(r'^ts_history_modal/(?P<game_abbr>[A-Z0-9]+)/(?P<accountid>[\d]+)/(?P<match_type>[1TFGL])/$',
                   ratinghistorygraph_modal, name='srs/ratinghistorygraph_modal'),
               url(r'^team_stat_div/(?P<ts_id>[\d-]+)/$', team_stat_div, name='srs/team_stat_div'),
               url(r'^gamerelease/(?P<gameid>[\d-]+)/$', gamerelease_modal, name='srs/gamerelease_modal'),
               url(r'^hall_of_fame/(?P<abbreviation>[\w\ .:()\[\]-]+)/$', hall_of_fame, name='srs/hall_of_fame'),
               url(r'^hof_tbl_src/(?P<leaderboardid>[\d-]+)/$', hof_tbl_src, name='srs/hof_tbl_src'),
               url(r'^ajax_player_lookup/(?P<name>.+)/$', ajax_player_lookup, name='srs/ajax_player_lookup'),
               url(r'^ajax_map_lookup/(?P<name>.+)/$', ajax_map_lookup, name='srs/ajax_map_lookup'),
               url(r'^ajax_playerrating_tbl_src/(?P<accountid>[\d-]+)/$', ajax_playerrating_tbl_src,
                   name='srs/ajax_playerrating_tbl_src'),
               url(r'^ajax_winloss_tbl_src/(?P<accountid>[\d-]+)/$', ajax_winloss_tbl_src,
                   name='srs/ajax_winloss_tbl_src'),
               url(r'^ajax_playerreplays_tbl_src/(?P<accountid>[\d-]+)/$', ajax_playerreplays_tbl_src,
                   name='srs/ajax_playerreplays_tbl_src'),
               url(r'^infolog/', include('infolog_upload.urls')),
               ]

urlpatterns += staticfiles_urlpatterns()
