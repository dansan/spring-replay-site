import logging
import os.path
from logging.handlers import TimedRotatingFileHandler
import settings

logging.basicConfig(level=logging.DEBUG, format=settings.DEBUG_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT)

if settings.DEBUG:
    ro = TimedRotatingFileHandler(os.path.join(settings.LOG_PATH, 'root_debug.log'), when='d', interval=1, backupCount=14)
    ro.setLevel(logging.DEBUG)
    ro.setFormatter(logging.Formatter(fmt=settings.DEBUG_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
    logger = logging.getLogger()
    logger.addHandler(ro)

dj = TimedRotatingFileHandler(os.path.join(settings.LOG_PATH, 'django_info.log'), when='d', interval=1, backupCount=14)
dj.setLevel(logging.INFO)
dj.setFormatter(logging.Formatter(fmt=settings.INFO_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
logger = logging.getLogger("django")
logger.addHandler(dj)

l1 = TimedRotatingFileHandler(os.path.join(settings.LOG_PATH, 'srs_debug.log'), when='d', interval=1, backupCount=14)
l1.setLevel(logging.DEBUG)
l1.setFormatter(logging.Formatter(fmt=settings.DEBUG_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
l2 = TimedRotatingFileHandler(os.path.join(settings.LOG_PATH, 'srs_info.log'), when='d', interval=1, backupCount=14)
l2.setLevel(logging.INFO)
l2.setFormatter(logging.Formatter(fmt=settings.INFO_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
logger = logging.getLogger("srs")
logger.addHandler(l1)
logger.addHandler(l2)
