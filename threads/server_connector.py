import os
import subprocess
import threading
import pickle
from time import sleep
from datetime import datetime, timedelta

import paramiko
from paramiko.ssh_exception import SSHException
from psycopg2 import OperationalError
from utils.redis_client import redis_client, redis_client_pickle
from utils.utils import get_duration, extract_name, ping_server
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
        self.network_status = True
        self.logger = Logger('HomeServerConnector')

    def check_connection(self):
        self.network_status = ping_server(Config.STORAGE_SERVER_URL)

    def check_destination_path(self, sftp_client):
        try:
            sftp_client.stat(self.destination_path)
        except FileNotFoundError:
            self.logger.warning('Destination path doesnt exist!')
            sftp_client.mkdir(self.destination_path)

    def upload_regular_file(self, sftp):
        # получение имени файла из очереди в redis сервере
        filename = redis_client.lrange('ready_to_send', 0, 0)[0]
        filepath = os.path.join(Config.MEDIA_PATH, filename)
        try:
            # отправка файла на удаленный сервер
            self.logger.info(f'{filename} - start upload')

            start_time = datetime.strptime(filename[:19], Config.DATETIME_FORMAT)
            duration = get_duration(filename)
            if duration:
                finish_time = start_time + timedelta(seconds=int(duration))
                sftp.put(filepath, os.path.join(self.destination_path, filename))
                # подключение к базе данных
                with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
                    # запись данных о видео в удаленную бд
                    conn.add_record(filename=filename,
                                    start_time=start_time,
                                    finish_time=finish_time)
            else:
                self.logger.warning(f'Corrupt file {filename}')
                redis_client.lpop('ready_to_send')
                os.remove(filepath)  # TODO remove it
                raise IOError

        except FileNotFoundError:
            redis_client.delete(filename)
            redis_client.lpop('ready_to_send')
        except OSError as e:
            self.logger.exception(f'Some error occurred, {filename} not uploaded: {e}')
        except EOFError as e:
            self.logger.exception(f'SSH connection error: {e}')
        else:
            # удаление выгруженного файла из памяти и очереди в redis
            os.remove(filepath)
            redis_client.lpop('ready_to_send')
            self.logger.info(f'{filename} - upload complete')

    def upload_requested_files(self, sftp):
        # получение имени файлов из очереди в redis сервере
        request = pickle.loads(redis_client_pickle.lrange('ready_requested_videos', 0, 0)[0])
        pk = request['request_pk']
        files = request['files']
        duration = request['duration']

        for filename in files:
            filepath = os.path.join(Config.TEMP_PATH, filename)
            try:
                # отправка файла на удаленный сервер
                self.logger.info(f'{filename} - start upload')
                sftp.put(filepath, os.path.join(self.destination_path, filename))
                start_time = datetime.strptime(filename[:19], Config.DATETIME_FORMAT)
                finish_time = start_time + duration

                # подключение к базе данных
                with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
                    # запись данных о видео в удаленную бд
                    conn.add_record(filename=filename,
                                    start_time=start_time,
                                    finish_time=finish_time,
                                    pk=pk)
            except FileNotFoundError:
                self.logger.warning('Not found file to upload')
                redis_client_pickle.lpop('ready_requested_videos')
            except OSError as e:
                self.logger.exception(f'Some error occurred, {filename} not uploaded: {e}')
            except EOFError as e:
                self.logger.exception(f'SSH connection error: {e}')
            else:
                # удаление выгруженного файла из памяти и очереди в redis
                os.remove(filepath)
                redis_client_pickle.lpop('ready_requested_videos')
                self.logger.info(f'{filename} - upload complete')

        with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
            # запись данных о видео в удаленную бд
            status = True if files else False

            conn.set_request_status(pk=pk, status=status)

    def upload_logs(self, sftp):
        remote_path = os.path.join(self.destination_path, '..', 'logs')
        try:
            sftp.chdir(remote_path)
        except IOError:
            sftp.mkdir(remote_path)

        try:
            local_logs_path = os.path.join(Config.PATH, 'logs', 'data', 'logs.log')
            out_filename = f'Car{Config.CAR_ID}_logs.log'
            remote_file_path = os.path.join(remote_path, out_filename)
            sftp.put(local_logs_path, remote_file_path)
        except OSError as e:
            self.logger.exception(f'Some error occurred, logs not uploaded: {e}')

    def upload_files(self):
        """
        Выгрузка файлов на сервер с помощью SFTP
        Запись данных о файлах в удаленную базу данных
        """
        # создание SSH подключения

        if redis_client.llen('ready_to_send') or redis_client.llen('ready_requested_videos'):
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
                    self.upload_logs(sftp)
                    print(redis_client.llen('ready_to_send'))
                    print(redis_client.llen('ready_requested_videos'))
                    for _ in range(redis_client.llen('ready_to_send')):
                        self.upload_regular_file(sftp)
                    for _ in range(redis_client.llen('ready_requested_videos')):
                        self.upload_requested_files(sftp)

    def send_coordinates(self):
        """Отправка координат в удаленную базу данных"""
        # подключение к базе данных
        with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
            if redis_client.llen('coordinates'):
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
        with DBConnect(Config.DATABASE_URL, Config.CAR_ID) as conn:
            # получение запросов на видеозаписи
            requests = conn.get_record_requests()
            for request in requests:
                redis_client_pickle.lpush('requests', pickle.dumps(request))

    def merge_clips(self, clips):
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

    def make_clips_by_request(self):
        # Получение запросов
        self.check_video_requests()
        # Получение списка записанных файлов
        camera_names = [cam[1] for cam in Config.CAMERAS]
        filenames = [file for file in os.listdir(Config.MEDIA_PATH) if extract_name(file) in camera_names]

        for _ in range(redis_client_pickle.llen('requests')):
            request = pickle.loads(redis_client_pickle.lpop('requests'))

            request_files = []
            start_time = request['start_time'].replace(tzinfo=None)
            finish_time = request['finish_time'].replace(tzinfo=None)

            for filename in filenames:

                # Парсинг имени файла
                file_start = datetime.strptime(filename[:19], Config.DATETIME_FORMAT)
                file_finish = file_start + timedelta(seconds=int(get_duration(filename)))

                # Проверка видео, подходит ли оно под запрос и формирование видео
                if file_start <= start_time <= file_finish and file_start <= finish_time <= file_finish:
                    request_files.append(filename)
                elif start_time <= file_start and file_finish <= finish_time:
                    request_files.append(filename)
                elif file_start <= start_time <= file_finish:
                    request_files.append(filename)
                elif file_start <= finish_time <= file_finish:
                    request_files.append(filename)

            request_files = self.merge_clips(request_files)

            result_dict = {
                'request_pk': request['id'],
                'files': request_files,
                'duration': finish_time - start_time,
            }

            redis_client_pickle.lpush('ready_requested_videos', pickle.dumps(result_dict))

    def run(self):
        """
        Запуск бесконечного цикла.
        Попытка выгрузки файлов и координат в каждой итерации.
        В случае неудачи следущая попытка осуществляется через (хронометраж видео / 6).
        """

        while True:
            try:
                self.check_connection()
                if self.network_status:
                    self.send_coordinates()
                    self.make_clips_by_request()
                    self.upload_files()
            except (AttributeError, SSHException, OperationalError) as e:
                self.logger.info(f"Unable to connect: {e}")
            except Exception as e:
                self.logger.exception(f"Unexpected error: {e}")
            sleep(Config.VIDEO_DURATION.total_seconds())
