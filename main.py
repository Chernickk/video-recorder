import os

from threads.cam_recorder import CamRecorder
from threads.video_uploader import VideoUploader
from threads.gps_tracker import GPSEmulator
from threads.bot import CarBot
from threads.media_remover import MediaRemover
from config import Config


if __name__ == '__main__':
    if not os.path.exists(Config.MEDIA_PATH):
        os.mkdir(Config.MEDIA_PATH)

    for url, name in Config.CAMERAS:
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
