import os
import shutil
from threading import Thread
from time import sleep

from config import logger


class MediaRemover(Thread):
    def __init__(self,
                 check_interval=3600,
                 min_free_space=10,
                 media_path='media'):
        super().__init__()
        self.check_interval = check_interval
        self.min_free_space = min_free_space  # Gb
        self.num_files_to_delete = 4
        self.media_path = media_path

    def get_free_space(self):
        total, used, free = shutil.disk_usage("/")

        return free / 2**30

    def get_files_to_delete(self):
        files = os.listdir(self.media_path).sort(key=lambda x: os.path.getctime(x))
        return files[:self.num_files_to_delete]

    def delete_files(self, files):
        for file in files:
            os.remove(os.path.join(self.media_path, file))
            logger.info(f'{file} has been removed')

    def run(self):
        while True:
            try:
                free_space = self.get_free_space()
                if free_space <= 10:

                    logger.warning('Low disk space! Removing older files...')
                    files_to_delete = self.get_files_to_delete()
                    self.delete_files(files_to_delete)
            except Exception as e:
                logger.warning(f'Unexpected error: {e}')
            sleep(self.check_interval)
