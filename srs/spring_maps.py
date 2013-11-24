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
from PIL import Image, ImageChops, ImageFont, ImageDraw, ImageColor

from django.conf import settings
from models import Allyteam, Player

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
    if Allyteam.objects.filter(replay=replay).count() > 6:
        # random colors for the remaining AllyTeams
        for _ in range(0, Allyteam.objects.filter(replay=replay).count()-6):
            colors.append((random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    c_count  = 0
    x,y = img.size
    for at in Allyteam.objects.filter(replay=replay):
        # work around bugged replays (startpostype=2, but has no boxes)
        if at.startrectleft != None and at.startrecttop != None and at.startrectright != None and at.startrectbottom != None:
            # transparency mask
            team_layer = Image.new('RGBA',
                                   (int(at.startrectright*x)-int(at.startrectleft*x),
                                    int(at.startrectbottom*y)-int(at.startrecttop*y)),
                                   (256,256,256,96))
            # draw border of box (no transparency)
            draw = ImageDraw.Draw(team_layer)
            tl_x, tl_y = team_layer.size
            for i in range(4): # 4px border
                draw.rectangle([(0+i,0+i), (tl_x-i, tl_y-i)], fill=None, outline=(256,256,256,256))
            del draw
            # overlay map with partly transparent box
            img.paste(colors[c_count], box=(int(at.startrectleft*x),
                                                   int(at.startrecttop*y),
                                                   int(at.startrectright*x),
                                                   int(at.startrectbottom*y)), mask=team_layer)
            c_count += 1
    # draw players actual start positions
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(settings.FONTS_PATH+"VeraMono.ttf", 28)
    # map positions for players are in pixel
    # map pixel size = Spring Map Size (like 16x16) * 512
    # from: http://springrts.com/wiki/Mapdev:diffuse#Image_File
    if replay.map_info.width > 128:
        map_px_x = replay.map_info.width
        map_px_y = replay.map_info.height
    else:
        map_px_x = replay.map_info.width * 512
        map_px_y = replay.map_info.height * 512
    map_img_mult_x = map_px_x / x
    map_img_mult_y = map_px_y / y
    for player in Player.objects.filter(replay=replay, spectator=False, startposx__isnull=False, startposz__isnull=False):
        pl_img_pos_x = player.startposx / map_img_mult_x
        pl_img_pos_y = player.startposz / map_img_mult_y   # z is in spring what y is in img
        team_color = ImageColor.getrgb("#"+player.team.rgbcolor)
        # center number and circle above startpoint --> move up and left by text-size/2
        text_w, text_h = font.getsize(str(player.team.num))
        if player.team.num > 9:
            w = 15
        else:
            w = 0
        draw.ellipse((pl_img_pos_x-12-text_w/2, pl_img_pos_y-12-text_h/2, pl_img_pos_x+30+w-text_w/2,pl_img_pos_y+32-text_h/2), outline=team_color, fill=None)
        draw.ellipse((pl_img_pos_x-11-text_w/2, pl_img_pos_y-11-text_h/2, pl_img_pos_x+29+w-text_w/2,pl_img_pos_y+31-text_h/2), outline=team_color, fill=None)
        draw.ellipse((pl_img_pos_x-10-text_w/2, pl_img_pos_y-10-text_h/2, pl_img_pos_x+28+w-text_w/2,pl_img_pos_y+30-text_h/2), outline=team_color, fill=None)
        draw.ellipse((pl_img_pos_x- 9-text_w/2, pl_img_pos_y- 9-text_h/2, pl_img_pos_x+27+w-text_w/2,pl_img_pos_y+29-text_h/2), outline=team_color, fill="black")
        draw.text((pl_img_pos_x-text_w/2, pl_img_pos_y-text_h/2), str(player.team.num), font=font)
    del draw
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
