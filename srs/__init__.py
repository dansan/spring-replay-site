import logging
from os.path import realpath, dirname

LOG_PATH        = realpath(dirname(__file__))+'/log'
DEBUG_FORMAT = '%(asctime)s %(levelname)-8s %(module)s.%(funcName)s:%(lineno)d  %(message)s'
INFO_FORMAT  = '%(asctime)s %(levelname)-8s %(message)s'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

logging.basicConfig(level=logging.DEBUG,
                    format=DEBUG_FORMAT,
                    datefmt=DATETIME_FORMAT,
                    filename=LOG_PATH+'/root_debug.log',
                    filemode='w')

logger = logging.getLogger()
ro = logging.FileHandler(LOG_PATH+'/root_debug.log')
ro.setLevel(logging.DEBUG)
ro.setFormatter(logging.Formatter(fmt=DEBUG_FORMAT, datefmt=DATETIME_FORMAT))
logger.addHandler(ro)

logger = logging.getLogger("django")
dj = logging.FileHandler(LOG_PATH+'/django_info.log')
dj.setLevel(logging.INFO)
dj.setFormatter(logging.Formatter(fmt=INFO_FORMAT, datefmt=DATETIME_FORMAT))
logger.addHandler(dj)

logger = logging.getLogger(__package__) # __package__ is here 'srs'
l1 = logging.FileHandler(LOG_PATH+'/srs_debug.log')
l1.setLevel(logging.DEBUG)
l1.setFormatter(logging.Formatter(fmt=DEBUG_FORMAT, datefmt=DATETIME_FORMAT))
logger.addHandler(l1)

l2 = logging.FileHandler(LOG_PATH+'/srs_info.log')
l2.setLevel(logging.INFO)
l2.setFormatter(logging.Formatter(fmt=INFO_FORMAT, datefmt=DATETIME_FORMAT))
logger.addHandler(l2)
