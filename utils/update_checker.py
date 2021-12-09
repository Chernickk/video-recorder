from time import sleep
import sys

from git import Git

from config import Config
from logs.logger import Logger


def check_updates():
    logger = Logger('UPDATE')
    g = Git(Config.PATH)
    result = (g.pull('origin', 'main'))
    if result != 'Already up to date.':
        logger.warning('')
        sleep(5)
        sys.exit()

    logger.info('everything up to date')
