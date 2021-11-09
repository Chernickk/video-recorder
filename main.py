import os

from threads.cam_recorder import CamRecorder, ArUcoCamRecorder
from threads.video_uploader import HomeServerConnector
from threads.gps_tracker import GPSEmulator
from threads.bot import CarBot
from threads.media_remover import MediaRemover
from utils.prepare import check_unfinished_records
from config import Config


if __name__ == '__main__':
    if not os.path.exists(Config.MEDIA_PATH):
        os.mkdir(Config.MEDIA_PATH)

    check_unfinished_records()  # добавление файлов, которые не записались до конца, в очередь на выгрузку

    video_uploader = HomeServerConnector(
        url=Config.STORAGE_SERVER_URL,
        username=Config.STORAGE_SERVER_USERNAME,
        password=Config.STORAGE_SERVER_PASSWORD,
        destination_path=Config.DESTINATION_PATH
    )
    video_uploader.start()

    for url, name in Config.CAMERAS:
        if name == 'BodyCam':
            cam_recorder = ArUcoCamRecorder(
                url=url,
                camera_name=name,
                video_loop_size=Config.VIDEO_DURATION,
                media_path=Config.MEDIA_PATH
            )
        else:
            cam_recorder = CamRecorder(
                url=url,
                camera_name=name,
                video_loop_size=Config.VIDEO_DURATION,
                media_path=Config.MEDIA_PATH
            )
        cam_recorder.start()

    gps_tracker = GPSEmulator()
    gps_tracker.start()

    car_bot = CarBot(Config.CAR_ID)
    car_bot.start()

    media_remover = MediaRemover(check_interval=Config.VIDEO_DURATION.total_seconds(),
                                 media_path=Config.MEDIA_PATH)
    media_remover.start()
