import threading
from datetime import datetime, timedelta
from time import sleep

import cv2

from redis_client import redis_client
from config import logger


class CamRecorder(threading.Thread):
    def __init__(self, url: str, filename: str, video_loop_size: timedelta):
        super().__init__()

        self.capture = cv2.VideoCapture(url)
        self.url = url
        self.fps = 15
        self.filename = filename
        self.image_size = (
            int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        )
        self.out = None
        self.loop_time_in_seconds = int(video_loop_size.total_seconds()) * self.fps

    def check_capture(self):
        if not self.capture.isOpened():
            raise IOError('Stream stopped')
        status, _ = self.capture.read()
        if not status:
            raise IOError('Stream stopped')

        return True

    def record_video(self):
        datetime_now = datetime.now()
        datetime_string = f'{datetime_now.date()}_{datetime_now.hour:02d}:' \
                          f'{datetime_now.minute:02d}:{datetime_now.second:02d}'

        self.out = cv2.VideoWriter(f'media/{datetime_string}_{self.filename}',
                                   cv2.VideoWriter_fourcc(*'XVID'),
                                   self.fps,
                                   self.image_size,
                                   True)
        filename = f'{datetime_string}_{self.filename}'

        for i in range(self.loop_time_in_seconds):
            status, frame = self.capture.read()
            self.out.write(frame)

        logger.info(f'file "{datetime_string}_{self.filename}" has been recorded')

        return filename

    def run(self):
        logger.info(f'Start recording')
        while True:
            try:
                self.capture = cv2.VideoCapture(self.url)
                if self.check_capture():
                    filename = self.record_video()
                    redis_client.rpush('ready_to_send', filename)
            except Exception as e:
                logger.warning(f'Some error occurred: {e}')
                sleep(30)
            finally:
                self.capture.release()
