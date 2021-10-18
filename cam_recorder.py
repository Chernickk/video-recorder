import threading
from datetime import datetime, timedelta

import cv2

from redis_client import redis_client
from config import logger


class CamRecorder(threading.Thread):
    def __init__(self, url: str, filename: str, video_loop_size: timedelta):
        super().__init__()

        self.cap = cv2.VideoCapture(url)
        self.fps = 15

        self.filename = filename
        self.image_size = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        self.out = None
        self.loop_time_in_seconds = int(video_loop_size.total_seconds()) * self.fps

    def check_capture(self):
        if not self.cap.isOpened():
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

        for i in range(self.loop_time_in_seconds):
            ret, frame = self.cap.read()
            self.out.write(frame)

        logger.info(f'file "{datetime_string}_{self.filename}" has been recorded')
        redis_client.rpush('ready_to_send', f'{datetime_string}_{self.filename}')

    def run(self):
        try:
            logger.info(f'Start recording')
            while True:
                if self.check_capture():
                    self.record_video()

        except KeyboardInterrupt:
            logger.info('Recording stopped by user')
        except Exception as e:
            logger.warning(f'Some error occurred: {e}')
        finally:
            self.cap.release()
