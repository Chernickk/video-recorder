import os
from time import sleep

from threads.cam_recorder import CamRecorder, ArUcoCamRecorder

from threads.server_connector import HomeServerConnector
from threads.gps_tracker import GPSEmulator
from threads.bot import CarBot
from threads.media_remover import MediaRemover
from utils.prepare import check_unfinished_records
from config import Config

from logs.logger import Logger

logger = Logger('Main')


if __name__ == '__main__':
    if not os.path.exists(Config.MEDIA_PATH):
        os.mkdir(Config.MEDIA_PATH)
    if not os.path.exists(os.path.join(Config.MEDIA_PATH, 'temp')):
        os.mkdir(os.path.join(Config.MEDIA_PATH, 'temp'))

    logger.info('_'*30)
    logger.info('Start')

    # check_unfinished_records()  # добавление файлов, которые не записались до конца, в очередь на выгрузку
    #
    # video_uploader = HomeServerConnector(
    #     url=Config.STORAGE_SERVER_URL,
    #     username=Config.STORAGE_SERVER_USERNAME,
    #     password=Config.STORAGE_SERVER_PASSWORD,
    #     destination_path=Config.DESTINATION_PATH
    # )
    # video_uploader.start()
    #
    # gps_tracker = GPSEmulator()
    # gps_tracker.start()
    #
    # car_bot = CarBot(Config.TELEGRAM_BOT_TOKEN, Config.CHAT_ID, Config.CAR_ID)
    # car_bot.start()
    #
    # media_remover = MediaRemover(check_interval=Config.VIDEO_DURATION.total_seconds(),
    #                              media_path=Config.MEDIA_PATH)
    # media_remover.start()

    # sleep(30)  # Ожидание инициализации камер

    for url, name in Config.CAMERAS:
        if name == 'BodyCam':
            cam_recorder = ArUcoCamRecorder(
                url=url,
                camera_name=name,
                video_loop_size=Config.VIDEO_DURATION,
                media_path=Config.MEDIA_PATH,
                fps=Config.FPS,
            )
        else:
            cam_recorder = CamRecorder(
                url=url,
                camera_name=name,
                video_loop_size=Config.VIDEO_DURATION,
                media_path=Config.MEDIA_PATH,
                fps=Config.FPS,
            )
        cam_recorder.start()
