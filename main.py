import os

from cam_recorder import CamRecorder
from video_uploader import VideoUploader
from gps_tracker import GPSEmulator
from bot import CarBot
from config import camera_urls_names, Config
from media_remover import MediaRemover


if __name__ == '__main__':
    if not os.path.exists(Config.MEDIA_PATH):
        os.mkdir(Config.MEDIA_PATH)

    for url, name in camera_urls_names:
        cam_recorder = CamRecorder(
            url=url,
            camera_name=name,
            video_loop_size=Config.VIDEO_DURATION,
            media_path=Config.MEDIA_PATH
        )
        cam_recorder.start()

    video_uploader = VideoUploader(
        url=Config.STORAGE_SERVER_URL,
        username=Config.STORAGE_SERVER_USERNAME,
        password=Config.STORAGE_SERVER_PASSWORD,
        destination_path=Config.DESTINATION_PATH
    )
    video_uploader.start()

    gps_tracker = GPSEmulator()
    gps_tracker.start()

    car_bot = CarBot(Config.CAR_ID)
    car_bot.start()

    media_remover = MediaRemover(check_interval=Config.VIDEO_DURATION.total_seconds(),
                                 media_path=Config.MEDIA_PATH)
    media_remover.start()
