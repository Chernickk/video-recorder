import datetime
import threading
import random
import pickle
from time import sleep
from datetime import datetime

from utils.redis_client import redis_client_pickle
from utils.variables import COORDINATES
from logs.logger import Logger


class GPSEmulator(threading.Thread):
    """ Эмулятор gps трекера - генерирует случайные координаты """
    def __init__(self):
        super().__init__()
        self.logger = Logger('GPSTracker')

    def get_coordinates(self) -> dict:
        """
        Получение координат (сейчас рандомно), сделано для тестов
        :return: dict
        """
        latitude = random.randint(-900000, 900000) / 10000
        longitude = random.randint(-1800000, 1800000) / 10000

        gps = {
            'latitude': latitude,
            'longitude': longitude,
            'datetime': datetime.now()
        }

        return gps

    def run(self) -> None:
        """ Запуск потока """
        self.logger.info('start gps tracker')
        while True:
            try:
                coords = self.get_coordinates()
                redis_client_pickle.rpush(COORDINATES, pickle.dumps(coords))

                sleep(120)
            except Exception as error:
                self.logger.exception(f'Unexpected error {error}')
