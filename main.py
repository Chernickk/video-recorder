import os

from cam_recorder import CamRecorder
from video_uploader import VideoUploader
from gps_tracker import GPSEmulator
from config import camera_urls_names, Config


if __name__ == '__main__':
    if not os.path.exists('media'):
        os.mkdir('media')

    for url, name in camera_urls_names:
        cam_recorder = CamRecorder(
            url=url,
            camera_name=name,
            video_loop_size=Config.VIDEO_DURATION
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
