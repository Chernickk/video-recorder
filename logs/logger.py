import os
from config import Config

from loguru import logger

logger.add(os.path.join(Config.PATH, 'logs', 'data', 'logs.log'), level='DEBUG', rotation='1 MB', compression='zip')
