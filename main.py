import os
from datetime import timedelta

from cam_recorder import CamRecorder
from video_uploader import VideoUploader
from config import single_url, camera_urls_names, STORAGE_SERVER_URL, STORAGE_SERVER_USERNAME, STORAGE_SERVER_PASSWORD


if __name__ == '__main__':
    if not os.path.exists('media'):
        os.mkdir('media')

    # for url, name in camera_urls_names:
    #     cam_recorder = CamRecorder(
    #         url=url,
    #         filename=f'res:{name}.avi',
    #         video_loop_size=timedelta(minutes=1)
    #     )
    #     cam_recorder.start()

    video_uploader = VideoUploader(
        url=STORAGE_SERVER_URL,
        username=STORAGE_SERVER_USERNAME,
        password=STORAGE_SERVER_PASSWORD,
        destination_path='/home/user/videoserver/'
    )
    video_uploader.start()
