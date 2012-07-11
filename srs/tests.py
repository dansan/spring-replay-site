import datetime
import random
import hashlib

from django.db.models.signals import post_save, post_delete
from django.db import DatabaseError
from django.db.models import Max

from models import *

def add_500_replays():
    post_save.disconnect(replay_save_callback, sender=Replay)

    for i in range(0,500):
        gameid = hashlib.sha1(str(random.randint(0,1000000000000000))).hexdigest()

        r = Replay.objects.create(versionString="88.0",
                                  gameID=gameid,
                                  unixTime=datetime.datetime.strptime("2012-02-02 12:12:12", "%Y-%m-%d %H:%M:%S"),
                                  wallclockTime="2012-02-02 12:12:12",
                                  autohostname="testhost",
                                  gametype="test500",
                                  startpostype=0,
                                  title="test 500 - "+gameid[:10],
                                  short_text="test 500 - "+gameid[:10],
                                  long_text="testing adding 500 replays",
                                  notcomplete = True,
                                  map_info = Map.objects.get(id=1),
                                  map_img = MapImg.objects.get(id=1),
                                  uploader=User.objects.all()[0],
                                  replayfile=ReplayFile.objects.all()[0])
        r.tags.add(Tag.objects.get_or_create(name="test500", defaults={"name": "test500"})[0])
        r.save()

    post_save.connect(replay_save_callback, sender=Replay)
    update_stats()

def del_all_test500_replays():
    post_delete.disconnect(obj_del_callback)
    post_delete.disconnect(replay_del_callback, sender=Replay)

    try:
        Replay.objects.filter(tags__name="test500").delete()
    except DatabaseError:
        # "DatabaseError: too many SQL variables"
        # delete 500 at a time
        while Replay.objects.filter(tags__name="test500").count > 0:
            max_id = Replay.objects.all().aggregate(Max('id'))['id__max']
            Replay.objects.filter(tags__name="test500", id__gt=max_id-500).delete()

    post_delete.connect(obj_del_callback)
    post_delete.connect(replay_del_callback, sender=Replay)
    update_stats()
