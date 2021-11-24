import os
import shutil
import subprocess
import socket
from typing import List

import cv2

from utils.redis_client import redis_client
from config import Config


def extract_datetime(filename):
    return filename[:19]


def extract_name(filename):
    """
    :param filename: str
    :return camera name: str
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


def get_free_space() -> float:
    total, used, free = shutil.disk_usage("/")

    return free / 2 ** 30


def get_clips_by_name(clips: List[str], name: str):
    camera_clips = [clip for clip in clips if name in clip]
    if camera_clips:
        camera_clips.sort()
        return camera_clips
    return None


def merge_clips(clips: List[str]) -> str:
    """
    Merge clips
    :param clips: list
    :return output merged clip: str
    """

    output_name = f'{clips[0].split(".")[0]}_all.mp4'
    output_path = os.path.join(Config.TEMP_PATH, output_name)

    with open('input.txt', 'w') as f:
        for filename in clips:
            f.write(f"file '{os.path.join(Config.MEDIA_PATH, filename)}'\n")

    subprocess.call(['ffmpeg',
                     '-f', 'concat',
                     '-safe', '0',
                     '-i', 'input.txt',
                     '-c', 'copy',
                     '-y', output_path])

    os.remove('input.txt')

    return output_name


def get_self_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()

        return ip_address
    except OSError:
        return '???'
