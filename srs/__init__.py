import logging
import settings

logging.basicConfig(level=logging.DEBUG,
                    format=settings.DEBUG_FORMAT,
                    datefmt=settings.LOG_DATETIME_FORMAT,
                    filename=settings.LOG_PATH+'/root_debug.log',
                    filemode='w')

logger = logging.getLogger()
ro = logging.FileHandler(settings.LOG_PATH+'/root_debug.log')
ro.setLevel(logging.DEBUG)
ro.setFormatter(logging.Formatter(fmt=settings.DEBUG_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
logger.addHandler(ro)

logger = logging.getLogger("django")
dj = logging.FileHandler(settings.LOG_PATH+'/django_info.log')
dj.setLevel(logging.INFO)
dj.setFormatter(logging.Formatter(fmt=settings.INFO_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
logger.addHandler(dj)

logger = logging.getLogger(__package__) # __package__ is here 'srs'
l1 = logging.FileHandler(settings.LOG_PATH+'/srs_debug.log')
l1.setLevel(logging.DEBUG)
l1.setFormatter(logging.Formatter(fmt=settings.DEBUG_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
logger.addHandler(l1)

l2 = logging.FileHandler(settings.LOG_PATH+'/srs_info.log')
l2.setLevel(logging.INFO)
l2.setFormatter(logging.Formatter(fmt=settings.INFO_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
logger.addHandler(l2)
