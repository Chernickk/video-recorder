import os
from datetime import datetime, timedelta
import threading

import cv2

from config import logger, single_url
# from bot.main import send_message


class CamRecorder(threading.Thread):
    def __init__(self, url: str, filename: str, video_loop_size: timedelta):
        super().__init__()

        self.cap = cv2.VideoCapture(url)
        # .get(cv2.CAP_PROP_FPS) may return incorrect result
        # self.fps = int(self.cap.get(cv2.CAP_PROP_FPS)) if self.cap.get(cv2.CAP_PROP_FPS) < 100 else 15
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
        # send_message(f'file "{datetime_string}_{self.filename}" has been recorded')

    def run(self):
        try:
            logger.info(f'Start recording')
            # send_message(f'Start recording')
            while True:
                if self.check_capture():
                    self.record_video()

        except KeyboardInterrupt:
            logger.info('Recording stopped by user')
        except Exception as e:
            logger.warning(f'Some error occurred: {e}')
        finally:
            self.cap.release()


if __name__ == '__main__':
    if not os.path.exists('media'):
        os.mkdir('media')

    cam_recorder = CamRecorder(
        url=single_url,
        filename='res.avi',
        video_loop_size=timedelta(minutes=10)
    )
    cam_recorder.run()
