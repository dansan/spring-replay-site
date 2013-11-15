#!/usr/bin/env python

# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from xmlrpclib import ServerProxy
import pprint
import urllib
import random
from PIL import Image, ImageChops, ImageFont, ImageDraw

from django.conf import settings
from models import Allyteam

class Spring_maps():
    def __init__(self, mapname):
        self.mapname = mapname

    def fetch_info(self):
        """
        fetches map information from api.springfiles.com, stores it in self.map_info
        - may raise an Exception when connecting to server
        """
        proxy = ServerProxy('http://api.springfiles.com/xmlrpc.php', verbose=False)
        searchstring = {
#    "category" : "Spring Maps",
        "logical" : "or",
        "tag" : self.mapname,
        "filename" : self.mapname,
        "springname" : self.mapname,
        "torrent" : True,
        "metadata" : True,
        "nosensitive" : True,
        "images" : True}

        try:
            self.map_info = proxy.springfiles.search(searchstring)
        except:
            self.map_info = None

    def fetch_img(self):
        """
        fetches map image from api.springfiles.com
        """
        urllib.urlretrieve (self.map_info[0]['mapimages'][0], settings.MAPS_PATH+self.mapname+".jpg")
        return self.mapname+".jpg"

    def make_home_thumb(self):
        image = Image.open(settings.MAPS_PATH+self.mapname+".jpg")
        size = settings.THUMBNAIL_SIZES["home"]
        image.thumbnail(size, Image.ANTIALIAS)
        image.save(settings.MAPS_PATH+self.mapname+"_home.jpg", "JPEG")
        return self.mapname+"_home.jpg"

def startpos_coord_to_img_coord(smap, st_coord, img):
#    # magic numbers: font size 14 -> number has around 7x10 px size
#    # move text a little up and left to show startpos more exact
#    x_move = -3
#    y_move = -5
    
    x_draw = st_coord[0] / smap.width  * img.size[0]
    y_draw = st_coord[1] / smap.height * img.size[1]

#    return (x_draw+x_move, y_draw+y_move)
    return (x_draw, y_draw)

def create_map_with_positions(smap):
    """
    create a map picture with start positions
    """
    img  = Image.open(settings.MAPS_PATH+smap.name+".jpg")
    img.thumbnail(settings.THUMBNAIL_SIZES["replay"], Image.ANTIALIAS)
    draw = ImageDraw.Draw(img)
#    font = ImageFont.truetype(settings.FONTS_PATH+"VeraMono.ttf", 14)
#    i = 1
    for startpos in [(float(pair.split(",")[0]), float(pair.split(",")[1])) for pair in smap.startpos.split("|")]:
        draw_pos = startpos_coord_to_img_coord(smap, startpos, img)
#        draw.text(draw_pos, str(i), font=font)
        draw.ellipse((draw_pos[0]-5, draw_pos[1]-5, draw_pos[0]+5,draw_pos[1]+5), outline="white", fill="green")
#        i += 1
    del draw
    img.save(settings.MAPS_PATH+smap.name+"_positions.jpg", "JPEG")
    return smap.name+"_positions.jpg"

def create_map_with_boxes(replay):
    """
    create a map picture with start boxes
    """
    img  = Image.open(settings.MAPS_PATH+replay.map_info.name+".jpg")
    colors   = [(200, 0, 0), (0, 200, 0), (0, 0, 200), (200,200,0), (200, 0, 200), (0, 200, 200)] # 6 defined colors
    if len(Allyteam.objects.filter(replay=replay)) > 6:
        # colors for up to 32 AllyTeams
        for _ in range(0, 26):
            colors.append((random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    c_count  = 0
    team_layer = Image.new('RGB', img.size, (256,256,256))
    x,y = img.size
    for at in Allyteam.objects.filter(replay=replay):
        # work around bugged replays (startpostype=2, but has no boxes)
        if at.startrectleft != None and at.startrecttop != None and at.startrectright != None and at.startrectbottom != None:
            team_layer.paste(colors[c_count], (int(at.startrectleft*x),
                                               int(at.startrecttop*y),
                                               int(at.startrectright*x),
                                               int(at.startrectbottom*y)))
            c_count += 1
    img = ImageChops.multiply(img, team_layer)
    img.thumbnail(settings.THUMBNAIL_SIZES["replay"], Image.ANTIALIAS)
    filename = replay.map_info.name+"_"+str(replay.gameID)+".jpg"
    img.save(settings.MAPS_PATH+filename, "JPEG")
    return filename

def main(argv=None):
    if argv is None:
        argv = sys.argv
        if len(argv) == 1:
            print "Usage: %s mapname" % (argv[0])
            return 1

        rmap = Spring_maps(argv[1])
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

