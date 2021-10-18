import os

from cam_recorder import CamRecorder
from video_uploader import VideoUploader
from config import camera_urls_names, Config


if __name__ == '__main__':
    if not os.path.exists('media'):
        os.mkdir('media')

    for url, name in camera_urls_names:
        cam_recorder = CamRecorder(
            url=url,
            filename=f'res:{name}.avi',
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
