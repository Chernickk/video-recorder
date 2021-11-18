import os
from datetime import timedelta, datetime
from time import sleep
from threading import Thread
import subprocess

import psutil

from utils.utils import get_duration
from config import Config
from logs.logger import Logger


class ExportMovieToExternalDrive(Thread):
    def __init__(self):
        super().__init__()
        self.check_interval = timedelta(minutes=1)
        self.disk_partitions = psutil.disk_partitions()
        self.new_device = None
        self.logger = Logger('exporter')

    def check_new_partitions(self):
        partitions = psutil.disk_partitions()
        new_device = set(partitions) - set(self.disk_partitions)
        if new_device:
            self.new_device = new_device.pop()
            self.upload_latest_files_to_external_device()

        self.disk_partitions = partitions

    def merge_clips(self, clips):
        camera_names = [camera[1] for camera in Config.CAMERAS]
        result_files = []

        for camera in camera_names:
            camera_clips = [clip for clip in clips if camera in clip]
            if camera_clips:
                camera_clips.sort()

                output_name = f'all_{camera_clips[0]}'

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

    def make_clips_for_export(self):
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

        request_files = self.merge_clips(request_files)

        return request_files

    def upload_latest_files_to_external_device(self):
        files = self.make_clips_for_export()
        for file in files:
            with open(os.path.join(self.new_device.mountpoint, file), 'wb') as out_file:
                with open(os.path.join(Config.TEMP_PATH, file), 'rb') as input_file:
                    for line in input_file:
                        out_file.write(line)
            os.remove(os.path.join(Config.TEMP_PATH, file))
        self.logger.info('Files exported to flash drive!')

    def run(self):
        while True:
            try:
                self.check_new_partitions()
            except Exception as e:
                self.logger.exception(f'Unexpected error: {e}')
            finally:
                sleep(20)


if __name__ == '__main__':
    exp = ExportMovieToExternalDrive()
    exp.run()
