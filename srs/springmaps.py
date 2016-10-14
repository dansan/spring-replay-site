#!/usr/bin/env python

# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from xmlrpclib import ServerProxy
import pprint
import urllib
import random
from PIL import Image, ImageFont, ImageDraw, ImageColor
import logging
from shutil import copyfile

from django.conf import settings
from srs.models import Allyteam, Player

logger = logging.getLogger("srs.views")


class SpringMaps():
    def __init__(self, mapname):
        self.map_name = mapname
        self.full_img = None
        self.map_info = None
        self.thumb = None

    def fetch_info(self):
        """
        fetches map information from api.springfiles.com, stores it in self.map_info
        - may raise an Exception when connecting to server
        """
        proxy = ServerProxy('http://api.springfiles.com/xmlrpc.php', verbose=False)
        searchstring = {
            "category": "map",
            #         "logical" : "or",
            #         "tag" : self.map_name,
            #         "filename" : self.map_name,
            "springname": self.map_name,
            "torrent": False,
            "metadata": True,
            "nosensitive": True,
            "images": True}

        try:
            self.map_info = proxy.springfiles.search(searchstring)
        except:
            logger.exception("FIXME: to broad exception handling.")
            self.map_info = None

    def fetch_img(self):
        """
        fetches map image from api.springfiles.com
        """
        if not hasattr(self, "map_info"):
            self.fetch_info()
        self.full_img = self.map_name + ".jpg"
        if self.map_info:
            urllib.urlretrieve(self.map_info[0]['mapimages'][0], settings.MAPS_PATH + self.full_img)
        else:
            # no img for this map available
            copyfile(settings.IMG_PATH + "map_img_not_avail.jpg", settings.MAPS_PATH + self.full_img)
        return self.full_img

    def make_home_thumb(self):
        if not hasattr(self, "full_img"):
            self.fetch_img()
        image = Image.open(settings.MAPS_PATH + self.full_img)
        size = settings.THUMBNAIL_SIZES["home"]
        image.thumbnail(size, Image.ANTIALIAS)
        self.thumb = self.map_name + "_home.jpg"
        image.save(settings.MAPS_PATH + self.thumb, "JPEG")
        return self.thumb

    def create_map_with_boxes(self, replay):
        """
        create a map picture with start boxes (if any) and player start positions
        """
        # open image from api.springfiles.com
        try:
            img = Image.open(settings.MAPS_PATH + self.full_img)
        except:
            logger.exception("Could not open '%s'.", settings.MAPS_PATH + self.full_img)
            raise

        full_img_x, full_img_y = img.size
        # map positions for players are in pixel
        # map pixel size = Spring Map Size (like 16x16) * 512
        # from: http://springrts.com/wiki/Mapdev:diffuse#Image_File
        if replay.map_info.width > 128:
            # api.springfiles.com returnd pixel size
            map_px_x = replay.map_info.width
            map_px_y = replay.map_info.height
        else:
            # api.springfiles.com returnd Spring Map Size
            map_px_x = replay.map_info.width * 512
            map_px_y = replay.map_info.height * 512

        map_img_mult_x = map_px_x / full_img_x
        map_img_mult_y = map_px_y / full_img_y

        #
        # create start boxes
        #
        allyteams = Allyteam.objects.filter(replay=replay,
                                            startrectleft__isnull=False,
                                            startrecttop__isnull=False,
                                            startrectright__isnull=False,
                                            startrectbottom__isnull=False)
        if allyteams.exists():
            # 6 defined colors
            colors = [(200, 0, 0), (0, 200, 0), (0, 0, 200), (200, 200, 0), (200, 0, 200), (0, 200, 200)]
            if Allyteam.objects.filter(replay=replay).count() > 6:
                # random colors for the remaining AllyTeams
                for _ in range(0, Allyteam.objects.filter(replay=replay).count() - 6):
                    colors.append((random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
            c_count = 0
            for at in allyteams:
                # transparency mask
                team_layer = Image.new('RGBA',
                                       (int(at.startrectright * full_img_x) - int(at.startrectleft * full_img_x),
                                        int(at.startrectbottom * full_img_y) - int(at.startrecttop * full_img_y)),
                                       (256, 256, 256, 96))
                # draw border of box (no transparency)
                draw = ImageDraw.Draw(team_layer)
                tl_x, tl_y = team_layer.size
                for i in range(4):  # 4px border
                    draw.rectangle([(0 + i, 0 + i), (tl_x - i, tl_y - i)], fill=None, outline=(256, 256, 256, 256))
                del draw
                # overlay map with partly transparent box
                img.paste(colors[c_count],
                          box=(int(at.startrectleft * full_img_x),
                               int(at.startrecttop * full_img_y),
                               int(at.startrectright * full_img_x),
                               int(at.startrectbottom * full_img_y)),
                          mask=team_layer)
                c_count += 1

        draw = ImageDraw.Draw(img)
        players = Player.objects.filter(replay=replay, spectator=False, startposx__isnull=False,
                                        startposz__isnull=False)
        if players.exists():
            #
            # draw players actual start positions
            #
            font = ImageFont.truetype(settings.FONTS_PATH + "VeraMono.ttf", 28)
            for player in players:
                pl_img_pos_x = player.startposx / map_img_mult_x
                pl_img_pos_y = player.startposz / map_img_mult_y  # z is in spring what y is in img
                team_color = ImageColor.getrgb("#" + player.team.rgbcolor)
                # center number and circle above startpoint --> move up and left by text-size/2
                text_w, text_h = font.getsize(str(player.team.num))
                if player.team.num > 9:
                    w = 15
                else:
                    w = 0
                draw.ellipse((pl_img_pos_x - 12 - text_w / 2, pl_img_pos_y - 8 - text_h / 2,
                              pl_img_pos_x + 30 + w - text_w / 2, pl_img_pos_y + 36 - text_h / 2
                              ),
                             outline=team_color,
                             fill=None)
                draw.ellipse((pl_img_pos_x - 11 - text_w / 2, pl_img_pos_y - 7 - text_h / 2,
                              pl_img_pos_x + 29 + w - text_w / 2, pl_img_pos_y + 35 - text_h / 2
                              ),
                             outline=team_color,
                             fill=None)
                draw.ellipse((pl_img_pos_x - 10 - text_w / 2, pl_img_pos_y - 6 - text_h / 2,
                              pl_img_pos_x + 28 + w - text_w / 2, pl_img_pos_y + 34 - text_h / 2
                              ),
                             outline=team_color,
                             fill=None)
                draw.ellipse((pl_img_pos_x - 9 - text_w / 2, pl_img_pos_y - 5 - text_h / 2,
                              pl_img_pos_x + 27 + w - text_w / 2, pl_img_pos_y + 33 - text_h / 2
                              ),
                             outline=team_color,
                             fill="black")
                draw.text((pl_img_pos_x - text_w / 2, pl_img_pos_y - text_h / 2), str(player.team.num), font=font)
        else:
            #
            # draw start positions saved in map
            #
            for startpos in [(float(pair.split(",")[0]), float(pair.split(",")[1])) for pair in
                             replay.map_info.startpos.split("|")]:
                draw_pos_x = startpos[0] / map_img_mult_x
                draw_pos_y = startpos[1] / map_img_mult_y
                draw.ellipse((draw_pos_x - 5, draw_pos_y - 5, draw_pos_x + 5, draw_pos_y + 5), outline="white",
                             fill="green")
        del draw

        # img.thumbnail(settings.THUMBNAIL_SIZES["replay"], Image.ANTIALIAS)
        filename = replay.map_info.name + "_" + str(replay.gameID) + ".jpg"
        try:
            img.save(settings.MAPS_PATH + filename, "JPEG")
        except:
            logger.exception("FIXME: to broad exception handling.")
            logger.exception("Could not save '%s'", path_join(settings.MAPS_PATH, filename))
        return filename


def main(argv=None):
    if argv is None:
        argv = sys.argv
        if len(argv) == 1:
            print "Usage: %s map_name" % (argv[0])
            return 1

        rmap = SpringMaps(argv[1])
        rmap.fetch_info()

        pp = pprint.PrettyPrinter(depth=6)

        print "################## map_info ##########################"
        print "map matches: %d" % len(rmap.map_info)
        print "##################"
        pp = pprint.PrettyPrinter(depth=6)
        pp.pprint(rmap.map_info)
        print "######################################################"
        return 0


if __name__ == "__main__":
    sys.exit(main())
