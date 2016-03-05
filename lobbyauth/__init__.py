import logging
import srs.settings as settings

logger = logging.getLogger("srs.auth")  # __package__ is here 'lobbybackend'
l1 = logging.FileHandler(settings.LOG_PATH + '/lobbybackend_debug.log')
l1.setLevel(logging.DEBUG)
l1.setFormatter(logging.Formatter(fmt=settings.DEBUG_FORMAT, datefmt=settings.LOG_DATETIME_FORMAT))
logger.addHandler(l1)
