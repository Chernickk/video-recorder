import os
from config import Config

from loguru import logger

logger.add(
    os.path.join(Config.PATH, 'logs', 'data', 'logs.log'),
    level='DEBUG',
    rotation='1 MB',
    compression='zip',
    backtrace=True,
)


class Logger:
    def __init__(self, name):
        self.logger = logger
        self.name = name

    def exception(self, exception):
        self.logger.exception(f'{self.name} Error: {exception}')

    def warning(self, message):
        self.logger.warning(f'{self.name} {message}')

    def info(self, message):
        self.logger.info(f'{self.name} {message}')
