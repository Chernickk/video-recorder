import os
from datetime import timedelta, datetime
from time import sleep
from threading import Thread
from multiprocessing import Process
import subprocess

import psutil
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

from utils.utils import get_duration
from config import Config


class ExportMovieToExternalDrive(Thread):
    def __init__(self):
        super().__init__()
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
            finish_time = file_start + timedelta(seconds=get_duration(filename))
        file_full_path = os.path.join(Config.MEDIA_PATH, filename)

        # Получение смещений для вырезки части клипа
        start_offset = start_time - file_start
        finish_offset = finish_time - file_start

        # Формирование имени выходного файла
        out_filename = f'{datetime.strftime(start_time, Config.DATETIME_FORMAT)}_' \
                       f'{filename.split("_")[-1]}'
        out_full_path = os.path.join(Config.TEMP_PATH, out_filename)

        # Формирования выходного файла
        ffmpeg_extract_subclip(
            file_full_path,
            start_offset.total_seconds(),
            finish_offset.total_seconds(),
            targetname=out_full_path)

        return out_filename

    def merge_clips(self, clips):
        camera_names = [camera[1] for camera in Config.CAMERAS]
        result_files = []

        for camera in camera_names:
            camera_clips = [clip for clip in clips if camera in clip]
            if camera_clips:
                camera_clips.sort()
                output_name = f'all_{camera_clips[0]}'
                output_path = os.path.join(Config.TEMP_PATH, output_name)
                first_file = os.path.join(Config.TEMP_PATH, camera_clips[0])
                other_files = [f'+{os.path.join(Config.TEMP_PATH, camera_clip)}' for camera_clip in camera_clips[1:]]
                command = ['mkvmerge',
                           '-o', output_path,
                           first_file]
                command += other_files

                subprocess.call(command)

                result_files.append(output_name)

            for file in camera_clips:
                os.remove(os.path.join(Config.TEMP_PATH, file))

        return result_files


    def make_clips_for_export(self):
        finish_time = datetime.now()
        start_time = finish_time - timedelta(minutes=15)

        # Получение списка записанных файлов
        filenames = [file for file in os.listdir(Config.MEDIA_PATH) if 'BodyCam' not in file]

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
                out_filename = self.make_clip(filename,
                                              start_time=start_time,
                                              finish_time=finish_time)

                request_files.append(out_filename)
            elif start_time <= file_start and file_finish <= finish_time:
                out_filename = self.make_clip(filename)
                request_files.append(out_filename)

            elif file_start <= start_time <= file_finish:
                out_filename = self.make_clip(filename,
                                              start_time=start_time, )
                request_files.append(out_filename)
            elif file_start <= finish_time <= file_finish:
                out_filename = self.make_clip(filename,
                                              finish_time=finish_time)
                request_files.append(out_filename)

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
        print('files export success')

    def run(self):
        while True:
            self.check_new_partitions()
            sleep(20)


if __name__ == '__main__':
    exp = ExportMovieToExternalDrive()
    exp.run()
