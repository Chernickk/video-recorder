import os
import threading
from time import sleep

import pysftp
from paramiko.ssh_exception import SSHException

from redis_client import redis_client
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
            with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:

                for _ in range(redis_client.llen('ready_to_send')):
                    try:
                        filename = redis_client.lrange('ready_to_send', 0, 0)[0]
                        filepath = os.path.join('media', filename)

                        logger.info(f'start upload {filename}')
                        sftp.put(filepath, os.path.join(self.destination_path, filename))
                        conn.add_record(filename=filename, video_duration=Config.VIDEO_DURATION)
                        logger.info(f'{filepath} upload complete')

                    except OSError as e:
                        logger.warning(f'Some error occured, {filename} not uploaded')
                    else:
                        os.remove(filepath)
                        redis_client.lpop('ready_to_send')

    def run(self):
        while True:
            try:
                self.upload_files()
            except AttributeError as e:
                logger.info("no connection, will try later")
            except SSHException as e:
                logger.info(f"no connection, {e}")
            sleep(Config.VIDEO_DURATION.total_seconds())
