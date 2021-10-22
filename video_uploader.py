import os
import threading
import pickle
from time import sleep
from datetime import timedelta

import pysftp
from paramiko.ssh_exception import SSHException
from moviepy.editor import VideoFileClip

from redis_client import redis_client, redis_client_pickle
from config import logger, Config
from db import DBConnect


class VideoUploader(threading.Thread):
    def __init__(self, url: str, username: str, password: str, destination_path: str):
        super().__init__()

        self.url = url
        self.username = username
        self.password = password
        self.destination_path = destination_path
        self._cnopts = pysftp.CnOpts()
        self._cnopts.hostkeys = None

    def upload_files(self):
        with pysftp.Connection(self.url, username=self.username, password=self.password, cnopts=self._cnopts) as sftp:
            for _ in range(redis_client.llen('ready_to_send')):
                try:
                    filename = redis_client.lrange('ready_to_send', 0, 0)[0]
                    filepath = os.path.join('media', filename)
                    duration = timedelta(seconds=VideoFileClip(filepath).duration)

                    logger.info(f'start upload {filename}')
                    sftp.put(filepath, os.path.join(self.destination_path, filename))

                    with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
                        conn.add_record(filename=filename, video_duration=duration)

                    logger.info(f'{filepath} upload complete')

                except OSError as e:
                    logger.warning(f'Some error occurred, {filename} not uploaded: {e}')
                else:
                    os.remove(filepath)
                    redis_client.lpop('ready_to_send')

    def send_coordinates(self):
        with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
            for _ in range(redis_client.llen('coordinates')):
                try:
                    coordinates = pickle.loads(redis_client_pickle.lrange('coordinates', 0, 0)[0])
                    conn.add_coordinates(coordinates)
                except Exception as e:
                    logger.warning(f'Some error occurred, coordinates not uploaded: {e}')
                else:
                    redis_client_pickle.lpop('coordinates')
            else:
                logger.info(f'coordinates upload complete')

    def run(self):
        while True:
            try:
                self.upload_files()
                self.send_coordinates()
            except AttributeError as e:
                logger.info("no connection, will try later")
            except SSHException as e:
                logger.info(f"no connection, {e}")
            sleep(Config.VIDEO_DURATION.total_seconds() // 3)
