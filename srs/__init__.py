import logging
import settings

logging.basicConfig(level=logging.DEBUG, format=settings.DEBUG_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT)

if settings.DEBUG:
    ro = logging.FileHandler(settings.LOG_PATH + '/root_debug.log')
    ro.setLevel(logging.DEBUG)
    ro.setFormatter(logging.Formatter(fmt=settings.DEBUG_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
    logger = logging.getLogger()
    logger.addHandler(ro)

dj = logging.FileHandler(settings.LOG_PATH + '/django_info.log')
dj.setLevel(logging.INFO)
dj.setFormatter(logging.Formatter(fmt=settings.INFO_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
logger = logging.getLogger("django")
logger.addHandler(dj)

l1 = logging.FileHandler(settings.LOG_PATH + '/srs_debug.log')
l1.setLevel(logging.DEBUG)
l1.setFormatter(logging.Formatter(fmt=settings.DEBUG_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
l2 = logging.FileHandler(settings.LOG_PATH + '/srs_info.log')
l2.setLevel(logging.INFO)
l2.setFormatter(logging.Formatter(fmt=settings.INFO_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
logger = logging.getLogger("srs")
logger.addHandler(l1)
logger.addHandler(l2)
