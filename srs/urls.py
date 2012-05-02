from django.conf.urls import patterns, include, url
from django.contrib.comments.feeds import LatestCommentFeed

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'srs.views.index'),
    url(r'^upload/$', 'srs.views.upload'),
    url(r'^search/$', 'srs.views.search'),
    url(r'^settings/$', 'srs.views.user_settings'),
    url(r'^accounts/', include('registration.backends.default.urls')),
    url(r'^all_comments/', 'srs.views.all_comments'),
    url(r'^comments/', include('django.contrib.comments.urls')),
    url(r'^download/(?P<gameID>[0-9,a-f]+)/$', 'srs.views.download'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^feeds/latest_comments/$', LatestCommentFeed()),

    url(r'^replays/$', 'srs.views.replays'),
    url(r'^replay/(?P<gameID>\w+)/$', 'srs.views.replay', name="replay_detail"),

    url(r'^tags/$', 'srs.views.tags'),
    url(r'^tag/(?P<reqtag>[\w\ .]+)/$', 'srs.views.tag', name="tag_detail"),

    url(r'^maps/$', 'srs.views.maps'),
    url(r'^map/(?P<mapname>[\w\ .-]+)/$', 'srs.views.rmap', name="map_detail"),

    url(r'^players/$', 'srs.views.players'),
    url(r'^player/(?P<accountid>[\d-]+)/$', 'srs.views.player', name="player_detail"),

    url(r'^games/$', 'srs.views.games'),
    url(r'^game/(?P<gametype>[\w\ .()-]+)/$', 'srs.views.game', name="game_detail"),

    url(r'^users/$', 'srs.views.users'),
    url(r'^user/(?P<username>[\w\ .()-]+)/$', 'srs.views.see_user', name="user_detail"),

    url(r'^match_date/(?P<shortdate>[\d-]+)/$', 'srs.views.match_date'),
    url(r'^upload_date/(?P<shortdate>[\d-]+)/$', 'srs.views.upload_date'),
)
