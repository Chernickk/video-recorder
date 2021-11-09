import os
import threading
from datetime import datetime, timedelta
from time import sleep

import cv2

from utils.redis_client import redis_client
from logs.logger import Logger
from config import Config


class CamRecorder(threading.Thread):
    def __init__(self, url: str, camera_name: str, video_loop_size: timedelta, media_path):
        super().__init__()

        self.capture = cv2.VideoCapture(url)
        self.url = url
        self.fps = 15
        self.camera_name = camera_name
        self.filename = f'rec_{self.camera_name}.avi'
        self.image_size = (
            int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        )
        self.dest_size = Config.VIDEO_RESOLUTION
        self.out = None
        self.total_frames = int(video_loop_size.total_seconds()) * self.fps
        self.media_path = media_path
        self.logger = Logger(self.camera_name)

    def check_capture(self):
        """ Проверка получения видео из rtsp стрима """
        if not self.capture.isOpened():
            raise IOError('Stream stopped')
        status, _ = self.capture.read()
        if not status:
            raise IOError('Stream stopped')

        return True

    def make_filename(self):
        datetime_now = datetime.now()
        datetime_string = f'{datetime_now.date()}_{datetime_now.hour:02d}:' \
                          f'{datetime_now.minute:02d}:{datetime_now.second:02d}'

        return f'{datetime_string}_{self.filename}'

    def record_video(self):
        """ Запись одного видеофайла """
        # формирования строки с датой для названия видеофайла
        filename = self.make_filename()

        # создание экземпляра обьекта записи видео
        self.out = cv2.VideoWriter(os.path.join(self.media_path, filename),
                                   cv2.VideoWriter_fourcc(*'XVID'),
                                   self.fps,
                                   self.dest_size,
                                   True)

        # считывание кадров из rtsp стрима
        for i in range(self.total_frames):
            status, frame = self.capture.read()
            frame = cv2.resize(frame, self.dest_size)
            self.out.write(frame)

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
                if self.check_capture():
                    self.record_video()

            except Exception as e:

                self.logger.warning(f'Unexpected recorder error: {e}')
                self.capture.release()
                sleep(30)
                self.capture = cv2.VideoCapture(self.url)


class ArUcoCamRecorder(CamRecorder):
    def __init__(self, url: str, camera_name: str, video_loop_size: timedelta, media_path):
        super().__init__(url=url,
                         camera_name=camera_name,
                         video_loop_size=video_loop_size,
                         media_path=media_path)
        self.check_interval_in_seconds = Config.CHECK_MARKERS_INTERVAL

    def detect_markers(self, frame):
        dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_250)
        parameters = cv2.aruco.DetectorParameters_create()
        _, markers, _ = cv2.aruco.detectMarkers(frame, dictionary, parameters=parameters)

        if markers is not None:
            return True

        return False

    def record_video(self):
        """ Запись одного видеофайла """

        _, frame = self.capture.read()
        status = self.detect_markers(frame)

        if status:

            # формирования строки с датой для названия видеофайла
            filename = self.make_filename()

            # создание экземпляра обьекта записи видео
            self.out = cv2.VideoWriter(os.path.join(self.media_path, filename),
                                       cv2.VideoWriter_fourcc(*'XVID'),
                                       self.fps,
                                       self.image_size,
                                       True)

            for i in range(self.total_frames):
                _, frame = self.capture.read()

                # проверка один раз в заданное количество секунд
                if not i % (self.fps * self.check_interval_in_seconds):
                    status = self.detect_markers(frame)
                    if not status:
                        break

                self.out.write(frame)

            self.logger.info(f'file "{filename}" has been recorded')

            return filename

        return False

    def run(self):
        """
        Запуск бесконечного цикла записи видео.
        Если rtsp недоступен, повторная попытка начала записи производится через 30 секунд.
        """
        self.logger.info(f'start recording...')
        while True:
            try:
                if self.check_capture():
                    filename = self.record_video()
                    if filename:
                        redis_client.rpush('ready_to_send', filename)

            except Exception as e:

                self.logger.warning(f'Unexpected recorder error: {e}')
                self.capture.release()
                sleep(30)
                self.capture = cv2.VideoCapture(self.url)


if __name__ == '__main__':
    cam_rec = ArUcoCamRecorder(url='rtsp://admin:Ckj;ysqgfhjkm13@10.10.10.50/1',
                               camera_name='cam',
                               video_loop_size=timedelta(minutes=1),
                               media_path=Config.MEDIA_PATH,
                               )
    cam_rec.record_video()
