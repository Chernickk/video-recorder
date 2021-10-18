import os
import threading
from time import sleep

import pysftp
from paramiko.ssh_exception import SSHException
from redis_client import redis_client
from config import logger


class VideoUploader(threading.Thread):
    def __init__(self, url: str, username: str, password: str, destination_path: str):
        super().__init__()

        self.url = url
        self.username = username
        self.password = password
        self.destination_path = destination_path

    def upload_files(self):
        with pysftp.Connection(self.url, username=self.username, password=self.password) as sftp:
            for _ in range(redis_client.llen('ready_to_send')):
                try:
                    filename = redis_client.lrange('ready_to_send', 0, 0)[0]
                    logger.info(f'start upload {filename}')
                    sftp.put(filename, os.path.join(self.destination_path, filename))
                    logger.info(f'{filename} upload complete')

                except OSError as e:
                    logger.warning(f'Some error occured, {filename} not uploaded')
                else:
                    os.remove(filename)
                    redis_client.lpop('ready_to_send')

    def run(self):
        while True:
            try:
                self.upload_files()
            except AttributeError as e:
                logger.info("no connection, will try later")
            except SSHException as e:
                logger.info(f"no connection, {e}")
            sleep(61)