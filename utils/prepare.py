import os

from redis_client import redis_client
from config import Config


def check_unfinished_records():
    files = os.listdir(Config.MEDIA_PATH)
    for file in files:
        redis_client.rpush('ready_to_send', file)
