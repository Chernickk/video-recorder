import os

import cv2

from utils.redis_client import redis_client
from config import Config


def extract_datetime(filename):
    return filename[:19]


def extract_name(filename):
    """
    :param filename:
    :return: camera name: str
    """
    return filename.split('.')[0].split('_')[-1]


def ping_server(host):
    if os.system("ping -c 1 " + host) == 0:
        return True
    return False


def check_unfinished_records():
    files = os.listdir(Config.MEDIA_PATH)
    for file in files:
        if 'BodyCam' in file:
            redis_client.rpush('ready_to_send', file)


def get_duration(filename, folder=None):
    if folder is None:
        folder = Config.MEDIA_PATH

    video = cv2.VideoCapture(os.path.join(folder, filename))
    frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = int(frame_count / Config.FPS)

    return duration
