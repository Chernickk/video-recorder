import os
import shutil
import subprocess
import socket

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


def get_free_space() -> float:
    total, used, free = shutil.disk_usage("/")

    return free / 2**30


def merge_clips(clips: list[str]) -> list[str]:
    """
    Merge clips from same camera
    :param clips: list
    :return merged clips: list
    """
    camera_names = [camera[1] for camera in Config.CAMERAS]
    result_files = []

    for camera in camera_names:
        camera_clips = [clip for clip in clips if camera in clip]
        if camera_clips:
            camera_clips.sort()

            output_name = f'{camera_clips[0].split(".")[0]}_all.mp4'

            output_path = os.path.join(Config.TEMP_PATH, output_name)
            first_file = os.path.join(Config.MEDIA_PATH, camera_clips[0])

            other_files = [f'+{os.path.join(Config.MEDIA_PATH, camera_clip)}' for camera_clip in camera_clips[1:]]
            command = ['mkvmerge',
                       '-o', output_path,
                       first_file]
            command += other_files

            subprocess.call(command)

            result_files.append(output_name)

    return result_files


def get_self_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()

        return ip_address
    except OSError:
        return '???'
