from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from srs.feeds import LatestUploadsFeed, UploaderFeed, SRSLatestCommentFeed
from srs.sitemap import ReplaySitemap, PlayerAccountSitemap, HofSitemap
from srs.ajax_views import BrowseReplaysDTView, CommentDTView

admin.autodiscover()

sitemaps = {"replays": ReplaySitemap,
            "players": PlayerAccountSitemap,
            "hall of fame": HofSitemap}

urlpatterns = patterns(
    '',
    url(r'^$', 'srs.views.index'),
    url(r'^index_replay_range/(?P<range_end>[\d]+)/(?P<game_pref>[\d]+)/$',
        'srs.views.index_replay_range', name="index_replay_range"),
    url(r'^djangojs/', include('djangojs.urls')),
    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    url(r'^upload/$', 'srs.upload_views.upload'),
    url(r'^upload_media/(?P<gameID>[0-9,a-f]+)/$', 'srs.upload_views.upload_media'),
    url(r'^media/(?P<mediaid>[0-9]+)/$', 'srs.views.media'),
    url(r'^settings/$', 'srs.views.user_settings'),
    url(r'^login/$', 'srs.views.login'),
    url(r'^logout/$', 'srs.views.logout'),
    url(r'^all_comments/', 'srs.views.all_comments'),
    url(r'^comment_tbl_src$', CommentDTView.as_view(), name='comment_tbl_src$'),
    url(r'^comments/', include('django.contrib.comments.urls')),
    url(r'^download/(?P<gameID>[0-9,a-f]+)/$', 'srs.views.download'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^xmlrpc/$', 'django_xmlrpc.views.handle_xmlrpc', name='xmlrpc'),
    url(r'^maplinks_modal/(?P<gameID>[0-9,a-f]+)/$', 'srs.ajax_views.maplinks_modal', name="maplinks_modal"),
    url(r'^modlinks_modal/(?P<gameID>[0-9,a-f]+)/$', 'srs.ajax_views.modlinks_modal', name="modlinks_modal"),
    url(r'^feeds/latest_comments/$', SRSLatestCommentFeed()),
    url(r'^feeds/latest/$', LatestUploadsFeed()),
    url(r'^feeds/uploader/(?P<username>[\w\ .:()\[\]-]+)/$', UploaderFeed()),
    url(r'^sldb_privacy_mode/$', 'srs.views.sldb_privacy_mode'),
    url(r'^browse/(?P<bfilter>.*)$', 'srs.views.browse_archive'),
    url(r'^browse_tbl_src$', BrowseReplaysDTView.as_view(), name='browse_tbl_src'),
    url(r'^replay/(?P<gameID>[0-9,a-f]+)/$', 'srs.views.replay', name="replay_detail"),
    url(r'^replay_by_id/(?P<replayid>[\d-]+)/$', 'srs.views.replay_by_id', name="replay_by_id"),
    url(r'^edit_replay/(?P<gameID>[0-9,a-f]+)/$', 'srs.views.edit_replay'),
    url(r'^player/(?P<accountid>[\d-]+)/$', 'srs.views.player', name="player_detail"),
    url(r'^ts_history_graph/(?P<game_abbr>[A-Z,0-9]+)/(?P<accountid>[\d]+)/(?P<match_type>[1,T,F,G,L])/$',
        'srs.views.ts_history_graph', name="ts_history_graph"),
    url(r'^ts_history_modal/(?P<game_abbr>[A-Z,0-9]+)/(?P<accountid>[\d]+)/(?P<match_type>[1,T,F,G,L])/$',
        'srs.ajax_views.ratinghistorygraph_modal', name="ratinghistorygraph_modal"),
    url(r'^gamerelease/(?P<gameid>[\d-]+)/$', 'srs.ajax_views.gamerelease_modal', name="gamerelease_modal"),
    url(r'^hall_of_fame/(?P<abbreviation>[\w\ .:()\[\]-]+)/$', 'srs.views.hall_of_fame', name="hall_of_fame"),
    url(r'^hof_tbl_src/(?P<leaderboardid>[\d-]+)/$', 'srs.ajax_views.hof_tbl_src', name='hof_tbl_src'),
    url(r'^ajax_player_lookup/(?P<name>.+)/$', 'srs.ajax_views.ajax_player_lookup', name="ajax_player_lookup"),
    url(r'^ajax_map_lookup/(?P<name>.+)/$', 'srs.ajax_views.ajax_map_lookup', name="ajax_map_lookup"),
    url(r'^ajax_playerrating_tbl_src/(?P<accountid>[\d-]+)/$', 'srs.ajax_views.ajax_playerrating_tbl_src',
        name='ajax_playerrating_tbl_src'),
    url(r'^ajax_winloss_tbl_src/(?P<accountid>[\d-]+)/$', 'srs.ajax_views.ajax_winloss_tbl_src',
        name='ajax_winloss_tbl_src'),
    url(r'^ajax_playerreplays_tbl_src/(?P<accountid>[\d-]+)/$', 'srs.ajax_views.ajax_playerreplays_tbl_src',
        name='ajax_playerreplays_tbl_src'),
    url(r'^infolog/', include('infolog_upload.urls')),
)

urlpatterns += staticfiles_urlpatterns()
