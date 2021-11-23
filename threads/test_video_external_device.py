import os
from datetime import timedelta, datetime
from time import sleep
from threading import Thread

import psutil

from utils.utils import get_duration, merge_clips
from config import Config
from logs.logger import Logger


class ExportMovieToExternalDrive(Thread):
    def __init__(self):
        super().__init__()
        self.check_interval = timedelta(minutes=1)
        self.disk_partitions = psutil.disk_partitions()
        self.new_device = None
        self.logger = Logger('exporter')

    def check_new_partitions(self) -> None:
        """
        Check for new partition
        Set connected device to 'self.new_device'
        """
        partitions = psutil.disk_partitions()
        new_device = set(partitions) - set(self.disk_partitions)
        if new_device:
            self.new_device = new_device.pop()
            self.upload_latest_files_to_external_device()

        self.disk_partitions = partitions

    def upload_latest_files_to_external_device(self) -> None:
        """ Upload files, which contains last 20 minutes, to external device """
        files = self.create_clips_for_export()
        for file in files:
            with open(os.path.join(self.new_device.mountpoint, file), 'wb') as out_file:
                with open(os.path.join(Config.TEMP_PATH, file), 'rb') as input_file:
                    for line in input_file:
                        out_file.write(line)
            os.remove(os.path.join(Config.TEMP_PATH, file))
        self.logger.info('Files exported to flash drive!')

    def create_clips_for_export(self):
        """ Find clips, which contains last 20 minutes and merge them """
        finish_time = datetime.now()
        start_time = finish_time - timedelta(minutes=20)

        # Получение списка записанных файлов
        filenames = os.listdir(Config.MEDIA_PATH)

        request_files = []
        for filename in filenames:

            # Парсинг имени файла
            file_start = datetime.strptime(filename[:19], Config.DATETIME_FORMAT)
            duration = get_duration(filename)
            if not duration:
                continue

            file_finish = file_start + timedelta(seconds=duration)

            # Проверка видео, подходит ли оно под запрос и формирование клипов
            if file_start <= start_time <= file_finish and file_start <= finish_time <= file_finish:
                request_files.append(filename)
            elif start_time <= file_start and file_finish <= finish_time:
                request_files.append(filename)
            elif file_start <= start_time <= file_finish:
                request_files.append(filename)
            elif file_start <= finish_time <= file_finish:
                request_files.append(filename)

        request_files = merge_clips(request_files)

        return request_files

    def run(self):
        """ Run thread """
        while True:
            try:
                self.check_new_partitions()
            except Exception as error:
                self.logger.exception(f'Unexpected error: {error}')
            finally:
                sleep(20)
