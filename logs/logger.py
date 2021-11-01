import os

from loguru import logger

logger.add(os.path.join('data', 'logs.log'), level='DEBUG', rotation='1 MB', compression='zip')
