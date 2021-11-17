import os
import subprocess
import threading
from datetime import datetime, timedelta
from time import sleep

import cv2

from utils.redis_client import redis_client
from logs.logger import Logger
from config import Config


class CamRecorder(threading.Thread):
    def __init__(self, url: str, camera_name: str, video_loop_size: timedelta, media_path, fps):
        super().__init__()

        self.capture = cv2.VideoCapture(url)
        self.url = url
        self.fps = fps
        self.camera_name = camera_name
        self.filename = f'rec_{self.camera_name}.mp4'
        self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.out = None
        self.total_frames = int(video_loop_size.total_seconds()) * self.fps
        self.media_path = media_path
        self.logger = Logger(self.camera_name)

    def check_capture(self):
        """ Проверка получения видео из rtsp стрима """
        status, _ = self.capture.read()
        if not status or not self.capture.isOpened():
            raise IOError(f'Stream stopped. Frame status: {status}, capture: {self.capture.isOpened()}')

        return True

    def initial_check(self):
        """
        Дополнительная проверка для исключения ложных срабатываний
        :return:
        """
        for _ in range(5):
            status, frame = self.capture.read()
            if not status:
                return False

        return True

    def make_filename(self):
        datetime_string = datetime.strftime(datetime.now(), Config.DATETIME_FORMAT)

        return f'{datetime_string}_{self.filename}'

    def record_video(self):
        """ Запись одного видеофайла """
        # формирования строки с датой для названия видеофайла
        filename = self.make_filename()

        # создание экземпляра обьекта записи видео
        command = ['ffmpeg',
                   '-y',  # (optional) overwrite output file if it exists
                   '-f', 'rawvideo',
                   '-vcodec', 'rawvideo',
                   '-s', f'{self.width}x{self.height}',  # size of one frame
                   '-pix_fmt', 'bgr24',
                   '-r', '15',  # frames per second
                   '-i', '-',  # The input comes from a pipe
                   '-an',  # Tells FFMPEG not to expect any audio
                   '-c:v', 'mpeg4',
                   '-b:v', '1M',
                   f'{os.path.join(self.media_path, filename)}']

        with subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:

            # считывание кадров из rtsp стрима
            for i in range(self.total_frames):
                status, frame = self.capture.read()
                if status:
                    process.stdin.write(frame.tobytes())
                else:
                    break

        self.logger.info(f'file "{filename}" has been recorded')

        return filename

    def run(self):
        """
        Запуск бесконечного цикла записи видео.
        Если rtsp недоступен, повторная попытка начала записи производится через 30 секунд.
        """
        self.logger.info(f'start recording...')
        while True:
            try:
                if self.check_capture() and self.initial_check():
                    self.record_video()

            except Exception as e:

                self.logger.warning(f'Unexpected recorder error: {e}')
                self.capture.release()
                sleep(30)
                self.capture = cv2.VideoCapture(self.url)


class ArUcoCamRecorder(CamRecorder):
    def __init__(self, url: str, camera_name: str, video_loop_size: timedelta, media_path, fps):
        super().__init__(url, camera_name, video_loop_size, media_path, fps)

        self.check_interval_in_seconds = Config.CHECK_MARKERS_INTERVAL
        self.aruco_dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_250)
        self.aruco_params = cv2.aruco.DetectorParameters_create()

    def detect_markers(self, frame):
        _, markers, _ = cv2.aruco.detectMarkers(frame, self.aruco_dictionary, parameters=self.aruco_params)

        if markers is not None:
            return False

        return True

    def initial_check(self):
        """
        Дополнительная проверка для исключения ложных срабатываний
        :return:
        """
        for _ in range(5):
            status, frame = self.capture.read()
            if not status or not self.detect_markers(frame):
                return False

        return True

    def record_video(self):
        """ Запись одного видеофайла """
        # формирования строки с датой для названия видеофайла
        filename = self.make_filename()

        # создание экземпляра обьекта записи видео
        command = ['ffmpeg',
                   '-y',  # (optional) overwrite output file if it exists
                   '-f', 'rawvideo',
                   '-vcodec', 'rawvideo',
                   '-s', f'{self.width}x{self.height}',  # size of one frame
                   '-pix_fmt', 'bgr24',
                   '-r', '15',  # frames per second
                   '-i', '-',  # The input comes from a pipe
                   '-an',  # Tells FFMPEG not to expect any audio
                   '-c:v', 'mpeg4',
                   '-b:v', '1M',
                   f'{os.path.join(self.media_path, filename)}']

        with subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:

            for i in range(self.total_frames):
                record_status, frame = self.capture.read()
                if record_status:
                    # проверка один раз в заданное количество секунд
                    if i and not i % (self.fps * self.check_interval_in_seconds):
                        status = self.detect_markers(frame)
                        if not status:
                            break
                    process.stdin.write(frame.tobytes())

        self.logger.info(f'file "{filename}" has been recorded')

        return filename

    def run(self):
        """
        Запуск бесконечного цикла записи видео.
        Если rtsp недоступен, повторная попытка начала записи производится через 30 секунд.
        """
        self.logger.info(f'start recording...')
        while True:
            try:
                if self.check_capture() and self.initial_check():
                    filename = self.record_video()
                    if filename:
                        redis_client.rpush('ready_to_send', filename)
                else:
                    sleep(30)

            except Exception as e:

                self.logger.exception(f'Unexpected recorder error: {e}')
                self.capture.release()
                sleep(30)
                self.capture = cv2.VideoCapture(self.url)
