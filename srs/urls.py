from django.conf.urls import patterns, include, url
from django.contrib import admin
from ajax_select import urls as ajax_select_urls

from feeds import LatestUploadsFeed, UploaderFeed, SRSLatestCommentFeed

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'srs.views.index'),
    url(r'^upload/$', 'srs.upload.upload'),
    url(r'^search/$', 'srs.views.search'),
    url(r'^settings/$', 'srs.views.user_settings'),
    url(r'^login/$', 'srs.views.login'),
    url(r'^logout/$', 'srs.views.logout'),
    url(r'^all_comments/', 'srs.views.all_comments'),
    url(r'^comments/', include('django.contrib.comments.urls')),
    url(r'^download/(?P<gameID>[0-9,a-f]+)/$', 'srs.views.download'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^xmlrpc/$', 'django_xmlrpc.views.handle_xmlrpc', name='xmlrpc'),
    url(r'^mapmodlinks/(?P<gameID>\w+)/$', 'srs.views.mapmodlinks'),
    url(r'^feeds/latest_comments/$', SRSLatestCommentFeed()),
    url(r'^feeds/latest/$', LatestUploadsFeed()),
    url(r'^feeds/uploader/(?P<username>[\w\ .:()\[\]-]+)/$', UploaderFeed()),

    url(r'^replays/$', 'srs.views.replays'),
    url(r'^replay/(?P<gameID>\w+)/$', 'srs.views.replay', name="replay_detail"),
    url(r'^edit_replay/(?P<gameID>\w+)/$', 'srs.views.edit_replay'),

    url(r'^tags/$', 'srs.views.tags'),
    url(r'^tag/(?P<reqtag>[\w\ .:()\[\]-]+)/$', 'srs.views.tag', name="tag_detail"),

    url(r'^maps/$', 'srs.views.maps'),
    url(r'^map/(?P<mapname>.+)/$', 'srs.views.rmap', name="map_detail"),

    url(r'^players/$', 'srs.views.players'),
    url(r'^player/(?P<accountid>[\d-]+)/$', 'srs.views.player', name="player_detail"),

    url(r'^game/(?P<name>.+)/$', 'srs.views.game', name="game_detail"),

    url(r'^games/$', 'srs.views.games'),
    url(r'^gamerelease/(?P<gametype>.+)/$', 'srs.views.gamerelease', name="gamerelease_detail"),

    url(r'^users/$', 'srs.views.users'),
    url(r'^user/(?P<username>[\w\ .:()\[\]-]+)/$', 'srs.views.see_user', name="user_detail"),

    url(r'^match_date/(?P<shortdate>[\d-]+)/$', 'srs.views.match_date'),
    url(r'^upload_date/(?P<shortdate>[\d-]+)/$', 'srs.views.upload_date'),

    url(r'^initial_rating/$', 'srs.rating.initial_rating', name="initial_rating"),
    url(r'^rating_history/$', 'srs.views.rating_history', name="rating_history"),
    url(r'^manual_rating_history/$', 'srs.views.manual_rating_history', name="manual_rating_history"),
    url(r'^account_unification_history/$', 'srs.views.account_unification_history', name="account_unification_history"),
    url(r'^hall_of_fame/(?P<abbreviation>[\w\ .:()\[\]-]+)/$', 'srs.views.hall_of_fame', name="hall_of_fame"),
    url(r'^ba1v1tourney/$', 'srs.views.ba1v1tourney', name="ba1v1tourney"),
    url(r'^lookups/', include(ajax_select_urls)),
)
