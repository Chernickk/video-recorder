import os
import threading
import pickle
from time import sleep
from datetime import datetime, timedelta
from typing import List, Dict

import paramiko
from paramiko.sftp_client import SFTPClient
from paramiko.ssh_exception import SSHException
from psycopg2 import OperationalError
from utils.redis_client import redis_client, redis_client_pickle
from utils.utils import get_duration, extract_name, ping_server, extract_datetime, merge_clips, get_clips_by_name
from utils.db import DBConnect
from utils.variables import READY_TO_UPLOAD, READY_REQUESTED_FILES, COORDINATES, REQUESTS
from config import Config
from logs.logger import Logger


class HomeServerConnector(threading.Thread):
    """
    Class that connect to home_server,
    upload regular and requested files, logs,
    send_coordinates (if needed),
    """
    def __init__(self, url: str, username: str, password: str, destination_path: str):
        super().__init__()

        self.url = url
        self.username = username
        self.password = password
        self.destination_path = destination_path
        self.network_status = True
        self.logger = Logger('HomeServerConnector')

    def check_connection(self) -> None:
        """ Set network_status parameter """
        self.network_status = ping_server(Config.STORAGE_SERVER_URL)

    def check_destination_path(self, sftp_client: SFTPClient) -> None:
        """
        Check if remote path exists,
        create folder if not
        :param sftp_client:
        """
        try:
            sftp_client.stat(self.destination_path)
        except FileNotFoundError:
            self.logger.warning('Destination path doesnt exist!')
            sftp_client.mkdir(self.destination_path)

    def upload_regular_file(self, sftp: SFTPClient) -> None:
        """ Upload files that should be upload regularly """
        # получение имени файла из очереди в redis
        filename = redis_client.lrange(READY_TO_UPLOAD, 0, 0)[0]
        filepath = os.path.join(Config.MEDIA_PATH, filename)
        try:
            # отправка файла на удаленный сервер
            self.logger.info(f'{filename} - start upload')

            start_time = datetime.strptime(extract_datetime(filename), Config.DATETIME_FORMAT)
            duration = get_duration(filename)
            if duration:
                finish_time = start_time + timedelta(seconds=int(duration))
                sftp.put(filepath, os.path.join(Config.DESTINATION_TEMP, filename))
                # подключение к базе данных
                with DBConnect(Config.DATABASE_URL, Config.CAR_LICENSE_TABLE) as conn:
                    # запись данных о видео в удаленную бд
                    conn.add_record(filename=filename,
                                    start_time=start_time,
                                    finish_time=finish_time)
            else:
                self.logger.warning(f'Corrupt file {filename}')
                raise FileNotFoundError

        except FileNotFoundError:
            redis_client.lpop(READY_TO_UPLOAD)
        except OSError as error:
            self.logger.exception(f'Some error occurred, {filename} not uploaded: {error}')
        except EOFError as error:
            self.logger.exception(f'SSH connection error: {error}')
        else:
            # удаление выгруженного файла из памяти и очереди в redis
            os.remove(filepath)
            redis_client.lpop(READY_TO_UPLOAD)
            self.logger.info(f'{filename} - upload complete')

    def upload_requested_files(self, sftp: SFTPClient) -> None:
        """Upload files that should be upload on request"""
        # получение имени файлов из очереди в redis
        request = pickle.loads(redis_client_pickle.lrange(READY_REQUESTED_FILES, 0, 0)[0])
        pk = request['request_pk']
        files = request['files']
        try:
            for filename in files:
                filepath = os.path.join(Config.TEMP_PATH, filename)

                # отправка файла на удаленный сервер
                self.logger.info(f'{filename} - start upload')
                sftp.put(filepath, os.path.join(Config.DESTINATION_REQUEST, filename))
                start_time = datetime.strptime(extract_datetime(filename), Config.DATETIME_FORMAT)

                # подключение к базе данных
                with DBConnect(Config.DATABASE_URL, Config.CAR_LICENSE_TABLE) as conn:
                    # запись данных о видео в удаленную бд
                    conn.add_record(filename=filename,
                                    start_time=start_time,
                                    finish_time=None,
                                    pk=pk)

                os.remove(filepath)
                self.logger.info(f'{filename} - upload complete')

        except FileNotFoundError:
            self.logger.warning('Not found file to upload')
            redis_client_pickle.lpop(READY_REQUESTED_FILES)
        except OSError as error:
            self.logger.exception(f'Some error occurred, request {pk} files not uploaded: {error}')
        except EOFError as error:
            self.logger.exception(f'SSH connection error: {error}')
        else:
            # удаление выгруженного файла из памяти и очереди в redis
            redis_client_pickle.lpop(READY_REQUESTED_FILES)

            with DBConnect(Config.DATABASE_URL, Config.CAR_LICENSE_TABLE) as conn:
                # запись данных о видео в удаленную бд
                status = bool(files)
                conn.set_request_status(pk=pk, status=status)

    def upload_logs(self, sftp: SFTPClient) -> None:
        try:
            local_logs_path = os.path.join(Config.PATH, 'logs', 'data', 'logs.log')
            out_filename = f'Car{Config.CAR_LICENSE_TABLE}_logs.log'
            remote_file_path = os.path.join(Config.DESTINATION_LOGS, out_filename)
            sftp.put(local_logs_path, remote_file_path)
        except OSError as error:
            self.logger.exception(f'Some error occurred, logs not uploaded: {error}')

    def upload_files(self) -> None:
        """
        Выгрузка файлов на сервер с помощью SFTP
        Запись данных о файлах в удаленную базу данных
        """
        # создание SSH подключения

        if redis_client.llen(READY_TO_UPLOAD) or redis_client.llen(READY_REQUESTED_FILES):
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
                    sftp.chdir(Config.DESTINATION_DISK)

                    self.check_destination_path(sftp)
                    self.upload_logs(sftp)
                    for _ in range(redis_client.llen(READY_TO_UPLOAD)):
                        self.upload_regular_file(sftp)
                    for _ in range(redis_client.llen(READY_REQUESTED_FILES)):
                        self.upload_requested_files(sftp)

    def send_coordinates(self) -> None:
        """Отправка координат в удаленную базу данных"""
        # подключение к базе данных
        with DBConnect(Config.DATABASE_URL, Config.CAR_LICENSE_TABLE) as conn:
            if redis_client.llen(COORDINATES):
                for _ in range(redis_client.llen(COORDINATES)):
                    try:
                        # получение и десериализация координат из очереди redis
                        coordinates = pickle.loads(redis_client_pickle.lrange(COORDINATES, 0, 0)[0])
                        # отправка координат в бд
                        conn.add_coordinates(coordinates)
                    except Exception as error:
                        self.logger.exception(f'Some error occurred, coordinates not uploaded: {error}')
                    else:
                        # удаление координат из очереди redis
                        redis_client_pickle.lpop(COORDINATES)

                self.logger.info('coordinates upload complete')

    def check_video_requests(self) -> None:
        """
        Check record requests from home server
        push requests to redis queue
        """
        with DBConnect(Config.DATABASE_URL, Config.CAR_LICENSE_TABLE) as conn:
            # получение запросов на видеозаписи
            requests = conn.get_record_requests()
            for request in requests:
                redis_client_pickle.lpush(REQUESTS, pickle.dumps(request))

    def create_clips_by_request(self) -> None:
        """
        Create clips, for request
        Push clips names to redis queue
        """
        for _ in range(redis_client_pickle.llen(REQUESTS)):
            # Получение запроса
            request = pickle.loads(redis_client_pickle.lpop(REQUESTS))
            clips = self.find_clips_by_request(request)
            camera_names = [cam[1] for cam in Config.CAMERAS]

            request_files = []
            for camera_name in camera_names:
                camera_clips = get_clips_by_name(clips, camera_name)
                if camera_clips:
                    request_files.append(merge_clips(camera_clips))

            result_dict = {
                'request_pk': request['id'],
                'files': request_files,
            }

            redis_client_pickle.lpush(READY_REQUESTED_FILES, pickle.dumps(result_dict))

    def find_clips_by_request(self, request: Dict) -> List[str]:
        """ Find clips, which are suitable to request """

        filenames = os.listdir(Config.MEDIA_PATH)

        request_files = []
        start_time = request['start_time'].replace(tzinfo=None)
        finish_time = request['finish_time'].replace(tzinfo=None)

        for filename in filenames:

            # Парсинг имени файла
            file_start = datetime.strptime(extract_datetime(filename), Config.DATETIME_FORMAT)
            duration = int(get_duration(filename))
            if not duration:
                continue
            file_finish = file_start + timedelta(seconds=duration)

            # Проверка видео, подходит ли оно под запрос и формирование видео
            if file_start <= start_time <= file_finish and file_start <= finish_time <= file_finish:
                request_files.append(filename)
            elif start_time <= file_start and file_finish <= finish_time:
                request_files.append(filename)
            elif file_start <= start_time <= file_finish:
                request_files.append(filename)
            elif file_start <= finish_time <= file_finish:
                request_files.append(filename)

        return request_files

    def run(self):
        """
        Запуск бесконечного цикла.
        Попытка выгрузки файлов и координат в каждой итерации.
        В случае неудачи следущая попытка осуществляется через (хронометраж видео).
        """

        while True:
            try:
                self.check_connection()
                if self.network_status:
                    self.send_coordinates()
                    self.check_video_requests()
                    self.create_clips_by_request()
                    self.upload_files()
            except (AttributeError, SSHException, OperationalError) as error:
                self.logger.info(f"Unable to connect: {error}")
            except Exception as error:
                self.logger.exception(f"Unexpected error: {error}")
            sleep(Config.VIDEO_DURATION.total_seconds())
