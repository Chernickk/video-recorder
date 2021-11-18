import os
from time import sleep

from threads.cam_recorder import CamRecorder, ArUcoCamRecorder
from threads.test_video_external_device import ExportMovieToExternalDrive
from threads.server_connector import HomeServerConnector
from threads.gps_tracker import GPSEmulator
from threads.bot import CarBot
from threads.media_remover import MediaRemover
from utils.utils import check_unfinished_records
from config import Config

from logs.logger import Logger

logger = Logger('Main')


if __name__ == '__main__':
    if not os.path.exists(Config.MEDIA_PATH):
        os.mkdir(Config.MEDIA_PATH)
    if not os.path.exists(Config.TEMP_PATH):
        os.mkdir(Config.TEMP_PATH)

    logger.info('_'*50)
    logger.info('Start')

    check_unfinished_records()  # добавление файлов, которые не записались до конца, в очередь на выгрузку

    server_connector = HomeServerConnector(
        url=Config.STORAGE_SERVER_URL,
        username=Config.STORAGE_SERVER_USERNAME,
        password=Config.STORAGE_SERVER_PASSWORD,
        destination_path=Config.DESTINATION_PATH
    )
    server_connector.start()

    car_bot = CarBot(Config.TELEGRAM_BOT_TOKEN, Config.CHAT_ID, Config.CAR_ID)
    car_bot.start()

    media_remover = MediaRemover(check_interval=Config.VIDEO_DURATION.total_seconds(),
                                 media_path=Config.MEDIA_PATH)
    media_remover.start()

    sleep(30)  # Ожидание инициализации камер

    for url, name in Config.ARUCO_CAMERAS:
        cam_recorder = ArUcoCamRecorder(
            url=url,
            camera_name=name,
            video_loop_size=Config.VIDEO_DURATION,
            media_path=Config.MEDIA_PATH,
            fps=Config.FPS,
        )
        cam_recorder.start()

    for url, name in Config.CAMERAS:
        cam_recorder = CamRecorder(
            url=url,
            camera_name=name,
            video_loop_size=Config.VIDEO_DURATION,
            media_path=Config.MEDIA_PATH,
            fps=Config.FPS,
        )
        cam_recorder.start()

    media_exporter = ExportMovieToExternalDrive()
    media_exporter.start()

    # gps_tracker = GPSEmulator()
    # gps_tracker.start()
    #