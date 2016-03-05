from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse

from models import Replay, PlayerAccount, Game
from views import hall_of_fame


class ReplaySitemap(Sitemap):
    changefreq = "monthly"

    def items(self):
        return Replay.objects.all()


class PlayerAccountSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return PlayerAccount.objects.filter(accountid__gt=0)


class HofSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return Game.objects.exclude(sldb_name="")

    def location(self, game):
        return reverse(hall_of_fame, args=[game.abbreviation])
