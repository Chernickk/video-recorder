import os
from threading import Thread
from time import sleep
from datetime import timedelta
from typing import List

from logs.logger import Logger
from config import Config
from utils.utils import get_free_space


class MediaRemover(Thread):
    def __init__(self, check_interval=3600, min_free_space=10, media_path='media'):
        super().__init__()
        self.check_interval = check_interval
        self.min_free_space = min_free_space  # Gb
        self.num_files_to_delete = int(timedelta(hours=1) / Config.VIDEO_DURATION) * 4
        self.media_path = media_path
        self.logger = Logger('MediaRemover')

    def get_files_to_delete(self) -> List[str]:
        """
        :return: list of files to delete
        """
        files = os.listdir(self.media_path)
        files.sort()
        return files[:self.num_files_to_delete]

    def delete_files(self, files: List[str]) -> None:
        """
        Remove files from given list
        :param files: list
        """
        for file in files:
            os.remove(os.path.join(self.media_path, file))
            self.logger.info(f'{file} has been removed')

    def run(self) -> None:
        """
        Run media remover thread
        """
        while True:
            try:
                free_space = get_free_space()
                if free_space <= 10:

                    self.logger.info(f'Low disk space: {free_space:.2f} Gb! Removing older files...')
                    files_to_delete = self.get_files_to_delete()
                    self.delete_files(files_to_delete)
            except Exception as error:
                self.logger.exception(f'Unexpected error: {error}')
            sleep(self.check_interval)
