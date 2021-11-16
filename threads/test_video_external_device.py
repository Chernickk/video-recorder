import os
from datetime import timedelta, datetime
from time import sleep
import pathlib

import psutil

from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

class Config:
    PATH = pathlib.Path(__file__).parent.parent.resolve()

    MEDIA_PATH = os.path.join(PATH, 'media')

    DATETIME_FORMAT = '%Y-%m-%d_%H:%M:%S'


class ExportMovieToExternalDrive:
    def __init__(self):
        self.check_interval = timedelta(minutes=1)
        self.disk_partitions = psutil.disk_partitions()
        self.new_device = None

    def check_new_partitions(self):
        partitions = psutil.disk_partitions()
        new_device = set(partitions) - set(self.disk_partitions)
        if new_device:
            self.new_device = new_device.pop()
            self.upload_latest_files_to_external_device()

        self.disk_partitions = partitions

    def make_clip(self, filename, start_time=None, finish_time=None):
        file_start = datetime.strptime(filename[:19], Config.DATETIME_FORMAT)
        if not start_time:
            start_time = file_start
        if not finish_time:
            finish_time = file_start + timedelta(hours=1)
        file_full_path = os.path.join(Config.MEDIA_PATH, filename)

        # Получение смещений для вырезки части клипа
        start_offset = start_time - file_start
        finish_offset = finish_time - file_start

        # Формирование имени выходного файла
        out_filename = f'{datetime.strftime(start_time, Config.DATETIME_FORMAT)}_' \
                       f'{filename.split("_")[-1]}'
        out_full_path = os.path.join(Config.MEDIA_PATH, "temp", out_filename)

        # Формирования выходного файла
        ffmpeg_extract_subclip(
            file_full_path,
            start_offset.total_seconds(),
            finish_offset.total_seconds(),
            targetname=out_full_path)

        return out_filename

    def make_clips_by_request(self, date_time):
        finish_time = date_time
        start_time = finish_time - timedelta(minutes=15)

        # Получение списка записанных файлов
        filenames = [file for file in os.listdir(Config.MEDIA_PATH)]
        filenames.remove('temp')

        request_files = []
        for filename in filenames:

            # Парсинг имени файла
            file_start = datetime.strptime(filename[:19], Config.DATETIME_FORMAT)
            file_finish = file_start + timedelta(minutes=59)

            # Проверка видео, подходит ли оно под запрос и формирование клипов
            if file_start <= start_time <= file_finish and file_start <= finish_time <= file_finish:
                print(f'full {filename}')
                out_filename = self.make_clip(filename,
                                              start_time=start_time,
                                              finish_time=finish_time)

                request_files.append(out_filename)
            elif file_start <= start_time <= file_finish:
                print(f'start {filename}')
                out_filename = self.make_clip(filename,
                                              start_time=start_time, )
                request_files.append(out_filename)
            elif file_start <= finish_time <= file_finish:
                print(f'finish {filename}')
                out_filename = self.make_clip(filename,
                                              finish_time=finish_time)
                request_files.append(out_filename)

        return request_files

    def upload_latest_files_to_external_device(self):
        files = self.make_clips_by_request(datetime(2021, 11, 16, 3, 59, 19, 72401))
        for file in files:
            with open(os.path.join(self.new_device.mountpoint, file.replace(':', '-')), 'wb') as ffile:
                with open(os.path.join(Config.MEDIA_PATH, 'temp', file), 'rb') as f:
                    for line in f:
                        ffile.write(line)
            os.remove(os.path.join(Config.MEDIA_PATH, 'temp', file))
        print('files export success')

    def run(self):
        while True:
            self.check_new_partitions()
            sleep(20)


if __name__ == '__main__':
    exp = ExportMovieToExternalDrive()
    exp.run()
    # dt = datetime(2021, 11, 15, 12, 30, 19, 72401)
