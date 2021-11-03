import os
import threading
import time
from datetime import datetime, timedelta
from time import sleep

import cv2

from utils.redis_client import redis_client
from logs.logger import logger
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
        self.out = None
        self.total_frames = int(video_loop_size.total_seconds()) * self.fps
        self.media_path = media_path

    def log_info(self, message: str) -> None:
        logger.info(f'!{self.camera_name} {message}')

    def log_warning(self, message: str) -> None:
        logger.warning(f'!{self.camera_name} {message}')

    def check_capture(self):
        """ Проверка получения видео из rtsp стрима """
        if not self.capture.isOpened():
            raise IOError('Stream stopped')
        status, _ = self.capture.read()
        if not status:
            raise IOError('Stream stopped')

        return True

    def record_video(self):
        """ Запись одного видеофайла """
        # формирования строки с датой для названия видеофайла
        datetime_now = datetime.now()
        datetime_string = f'{datetime_now.date()}_{datetime_now.hour:02d}:' \
                          f'{datetime_now.minute:02d}:{datetime_now.second:02d}'
        filename = f'{datetime_string}_{self.filename}'

        # создание экземпляра обьекта записи видео
        self.out = cv2.VideoWriter(os.path.join(self.media_path, filename),
                                   cv2.VideoWriter_fourcc(*'XVID'),
                                   self.fps,
                                   self.image_size,
                                   True)

        # считывание кадров из rtsp стрима
        for i in range(self.total_frames):
            status, frame = self.capture.read()
            self.out.write(frame)

        self.log_info(f'file "{self.filename}" has been recorded')

        return filename

    def run(self):
        """
        Запуск бесконечного цикла записи видео.
        Если rtsp недоступен, повторная попытка начала записи производится через 30 секунд.
        """
        logger.info(f'{self.camera_name}: start recording...')
        while True:
            try:
                if self.check_capture():
                    filename = self.record_video()
                    redis_client.rpush('ready_to_send', filename)
            except Exception as e:
                self.log_warning(f'Unexpected recorder error: {e}')
                self.capture.release()
                sleep(30)
                self.capture = cv2.VideoCapture(self.url)


class TestCamRecorder(CamRecorder):
    def __init__(self, camera_name: str, video_loop_size: timedelta, media_path):
        super().__init__(url='rtsp://admin:Ckj;ysqgfhjkm13@192.168.204.55/1',
                         camera_name='None',
                         video_loop_size=timedelta(minutes=1),
                         media_path='')
        self.capture = cv2.VideoCapture('rtsp://admin:Ckj;ysqgfhjkm13@192.168.200.54/1')
        # self.capture = cv2.VideoCapture('../2021-10-30_11:32:38_rec_cam1.avi')
        self.url = '2021-10-30_11:32:38_rec_cam1.avi'
        self.fps = 15
        self.camera_name = camera_name
        self.filename = f'rec_{self.camera_name}.avi'
        # self.image_size = ((
        #     1280,
        #     720)
        # )
        self.image_size = (
            int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        )
        self.out = None
        self.total_frames = int(video_loop_size.total_seconds()) * self.fps
        self.media_path = media_path
        self.width_from = 0
        self.width_to = 600
        self.height_from = 100
        self.height_to = 720
        self.check_interval_in_seconds = 10

    def check_is_open(self, orb, sample_des, frame):
        frame_copy = cv2.cvtColor(
            frame[self.height_from:self.height_to, self.width_from:self.width_to],
            cv2.COLOR_BGR2GRAY
        )
        kp2, des2 = orb.detectAndCompute(frame_copy, None)
        bf = cv2.BFMatcher()
        matches = bf.knnMatch(sample_des, des2, k=2)

        correct_matches = [m for m, n in matches if m.distance < 0.85 * n.distance]

        if len(correct_matches) < 220:
            return True

        return False

    def record_video(self):
        """ Запись одного видеофайла """
        # формирования строки с датой для названия видеофайла
        filename = f'test_{self.filename}'

        # создание экземпляра обьекта записи видео
        self.out = cv2.VideoWriter(os.path.join(self.media_path, filename),
                                   cv2.VideoWriter_fourcc(*'XVID'),
                                   self.fps,
                                   self.image_size,
                                   True)

        # Открытие снимка-примера и поиск ключевых точек
        sample = cv2.imread('../vlcsnap-2021-11-03-15h21m33s342.png', cv2.IMREAD_GRAYSCALE)
        orb = cv2.ORB_create()
        kp1, des1 = orb.detectAndCompute(
            sample[self.height_from:self.height_to, self.width_from:self.width_to],
            None
        )

        # статус записи - false до тех пор пока изображение не будет отличаться от эталона
        status = False

        for i in range(self.total_frames):
            _, frame = self.capture.read()
            if not i % (self.fps * self.check_interval_in_seconds):  # проверка один раз в заданное количество секунд
                status = self.check_is_open(orb, des1, frame)

            if status:
                self.out.write(frame)


class TestCamRecorderOnOpen(CamRecorder):
    def __init__(self, camera_name: str, video_loop_size: timedelta, media_path):
        super().__init__(url='rtsp://admin:Ckj;ysqgfhjkm13@192.168.204.55/1',
                         camera_name='None',
                         video_loop_size=timedelta(minutes=1),
                         media_path='')
        self.capture = cv2.VideoCapture('../2021-10-30_11:32:38_rec_cam1.avi')
        self.url = '2021-10-30_11:32:38_rec_cam1.avi'
        self.fps = 15
        self.camera_name = camera_name
        self.filename = f'rec_{self.camera_name}.avi'
        self.image_size = ((
            1280,
            720)
        )
        self.out = None
        self.loop_time_in_seconds = int(video_loop_size.total_seconds()) * self.fps
        self.media_path = media_path

    def check_is_open(self):
        pass

    def record_video(self):
        """ Запись одного видеофайла """
        # формирования строки с датой для названия видеофайла

        filename = f'ttest_{self.filename}'
        print(self.media_path)

        # создание экземпляра обьекта записи видео
        self.out = cv2.VideoWriter(os.path.join(self.media_path, filename),
                                   cv2.VideoWriter_fourcc(*'XVID'),
                                   self.fps,
                                   self.image_size,
                                   True)

        status = False

        # считывание кадров из rtsp стрима
        for i in range(self.loop_time_in_seconds):
            _, frame = self.capture.read()

            if not i % 15:
                door = frame[0:800, 0:500]
                wall = frame[0:400, 600:1280]

                door_average_brightness = sum(cv2.mean(door)) / 3
                wall_average_brightness = sum(cv2.mean(wall)) / 3

                if abs(door_average_brightness - wall_average_brightness) > 30:
                    status = True
                else:
                    status = False

            if status:
                self.out.write(frame)


if __name__ == '__main__':
    cam_rec = TestCamRecorder(camera_name='cam', video_loop_size=timedelta(hours=1), media_path=Config.MEDIA_PATH)
    cam_rec.record_video()
