from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'srs.views.index'),
    url(r'^upload/$', 'srs.views.upload'),
    url(r'^search/$', 'srs.views.search'),
    url(r'^login/$', 'srs.views.login'),
    url(r'^logout/$', 'srs.views.logout'),
    url(r'^register/$', 'srs.views.register'),
    url(r'^download/(?P<gameID>[0-9,a-f]+)/$', 'srs.views.download'),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^replays/$', 'srs.views.replays'),
    url(r'^replay/(?P<gameID>\w+)/$', 'srs.views.replay'),

    url(r'^tags/$', 'srs.views.tags'),
    url(r'^tag/(?P<reqtag>[\w\ .]+)/$', 'srs.views.tag'),

    url(r'^maps/$', 'srs.views.maps'),
    url(r'^map/(?P<mapname>[\w\ ]+)/$', 'srs.views.rmap'),

    url(r'^players/$', 'srs.views.players'),
    url(r'^player/(?P<accountid>\d+)/$', 'srs.views.player'),

    url(r'^comments/$', 'srs.views.comments'),
    url(r'^comment/(?P<commentid>\d+)/$', 'srs.views.comment'),

    url(r'^games/$', 'srs.views.games'),
    url(r'^game/(?P<gametype>[\w\ .()-]+)/$', 'srs.views.game'),
)
