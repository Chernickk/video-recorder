import os
import threading
import pickle
from time import sleep
from datetime import timedelta

import paramiko
from moviepy.editor import VideoFileClip
from paramiko.ssh_exception import SSHException

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


    def upload_files(self):
        """
        Выгрузка файлов на сервер с помощью SFTP
        Запись данных о файлах в удаленную базу данных
        """
        # создание SSH подключения
        with paramiko.SSHClient() as client:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=self.url,
                           username=self.username,
                           password=self.password,
                           auth_timeout=30,
                           timeout=30,
                           banner_timeout=30)

            # создание sftp поверх ssh
            with client.open_sftp() as sftp:
                sftp.get_channel().settimeout(30)

                for _ in range(redis_client.llen('ready_to_send')):

                    # получение имени файла из очереди в redis сервере
                    filename = redis_client.lrange('ready_to_send', 0, 0)[0]
                    filepath = os.path.join('media', filename)
                    try:
                        duration = timedelta(seconds=VideoFileClip(filepath).duration)

                        # отправка файла на удаленный сервер
                        logger.info(f'start upload {filename}')
                        sftp.put(filepath, os.path.join(self.destination_path, filename))

                        # подключение к базе данных
                        with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
                            # запись данных о видео в удаленную бд
                            conn.add_record(filename=filename, video_duration=duration)

                    except OSError as e:
                        logger.warning(f'Some error occurred, {filename} not uploaded: {e}')
                    except EOFError as e:
                        logger.warning(f'SSH connection error: {e}')
                    else:
                        # удаление выгруженного файла из памяти и очереди в redis
                        os.remove(filepath)
                        redis_client.lpop('ready_to_send')
                        logger.info(f'{filepath} upload complete')

    def send_coordinates(self):
        """Отправка координат в удаленную базу данных"""
        # подключение к базе данных
        with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
            for _ in range(redis_client.llen('coordinates')):
                try:
                    # получение и десериализация координат из очереди redis
                    coordinates = pickle.loads(redis_client_pickle.lrange('coordinates', 0, 0)[0])
                    # отправка координат в бд
                    conn.add_coordinates(coordinates)
                except Exception as e:
                    logger.warning(f'Some error occurred, coordinates not uploaded: {e}')
                else:
                    # удаление координат из очереди redis
                    redis_client_pickle.lpop('coordinates')
            else:
                logger.info(f'coordinates upload complete')

    def run(self):
        """
        Запуск бесконечного цикла.
        Попытка выгрузки файлов и координат в каждой итерации.
        В случае неудачи следущая попытка осуществляется через (хронометраж видео / 6).
        """
        while True:
            try:
                self.upload_files()
                self.send_coordinates()
            except AttributeError as e:
                logger.info(f"no connection, will try later {e}")
            except SSHException as e:
                logger.info(f"no connection, {e}")
            except Exception as e:
                logger.warning(f"Unexpected error: {e}")
            sleep(Config.VIDEO_DURATION.total_seconds() // 6)
