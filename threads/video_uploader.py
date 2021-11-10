import os
import threading
import pickle
from time import sleep

import paramiko
from paramiko.ssh_exception import SSHException

from utils.redis_client import redis_client, redis_client_pickle
from config import Config
from utils.db import DBConnect
from logs.logger import Logger


class HomeServerConnector(threading.Thread):
    def __init__(self, url: str, username: str, password: str, destination_path: str):
        super().__init__()

        self.url = url
        self.username = username
        self.password = password
        self.destination_path = destination_path
        self.logger = Logger('HomeServerConnector')

    def check_destination_path(self, sftp_client):
        try:
            sftp_client.stat(self.destination_path)
        except FileNotFoundError:
            self.logger.warning('Destination path doesnt exist!')
            sftp_client.mkdir(self.destination_path)

    def upload_files(self):
        """
        Выгрузка файлов на сервер с помощью SFTP
        Запись данных о файлах в удаленную базу данных
        """
        # создание SSH подключения

        if redis_client.llen('ready_to_send'):
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

                    self.check_destination_path(sftp)

                    for _ in range(redis_client.llen('ready_to_send')):

                        # получение имени файла из очереди в redis сервере
                        filename = redis_client.lrange('ready_to_send', 0, 0)[0]
                        filepath = os.path.join(Config.MEDIA_PATH, filename)
                        try:
                            # отправка файла на удаленный сервер
                            self.logger.info(f'start upload {filename}')
                            sftp.put(filepath, os.path.join(self.destination_path, filename))

                            # подключение к базе данных
                            with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
                                # запись данных о видео в удаленную бд
                                conn.add_record(filename=filename)
                        except FileNotFoundError:
                            redis_client.lpop('ready_to_send')
                        except OSError as e:
                            self.logger.exception(f'Some error occurred, {filename} not uploaded: {e}')
                        except EOFError as e:
                            self.logger.exception(f'SSH connection error: {e}')
                        else:
                            # удаление выгруженного файла из памяти и очереди в redis
                            os.remove(filepath)
                            redis_client.lpop('ready_to_send')
                            self.logger.info(f'{filepath} upload complete')

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
                    self.logger.exception(f'Some error occurred, coordinates not uploaded: {e}')
                else:
                    # удаление координат из очереди redis
                    redis_client_pickle.lpop('coordinates')
            else:
                self.logger.info(f'coordinates upload complete')

    def check_video_requests(self):
        pass

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
                self.logger.info(f"no connection, will try later {e}")
            except SSHException as e:
                self.logger.info(f"no connection, {e}")
            except Exception as e:
                self.logger.exception(f"Unexpected error: {e}")
            sleep(Config.VIDEO_DURATION.total_seconds() // 6)