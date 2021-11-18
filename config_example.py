import os
import pathlib
from datetime import timedelta


class Config:
    PATH = pathlib.Path(__file__).parent.resolve()
    TEMP_PATH = os.path.join(PATH, 'temp')
    MEDIA_PATH = os.path.join(PATH, 'media')

    ARUCO_CAMERAS = [
        # ('rtsp://login:password@127.0.0.1/1', 'CameraName'),
    ]
    CAMERAS = [
        # ('rtsp://login:password@127.0.0.1/1', 'CameraName'),
        # ('rtsp://login:password@127.0.0.1/1', 'CameraName'),
        # ('rtsp://login:password@127.0.0.1/1', 'CameraName'),
    ]

    VIDEO_DURATION = timedelta(minutes=5)
    DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
    FPS = 15 # int
    CHECK_MARKERS_INTERVAL = 30  # in seconds

    STORAGE_SERVER_URL = '192.168.1.1'
    STORAGE_SERVER_USERNAME = 'username'
    STORAGE_SERVER_PASSWORD = 'password'
    DESTINATION_PATH = '/home/user/videoserver/media/'
    DATABASE_URL = 'postgresql+psycopg2://<username>:<password>@<192.168.1.1>/<db_name>'
    CAR_ID = 1

    TELEGRAM_BOT_TOKEN = 'bot_token'
    CHAT_ID = 12345678


