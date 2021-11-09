import datetime
import threading
import random
import pickle
from time import sleep
from datetime import datetime

from utils.redis_client import redis_client_pickle
from logs.logger import Logger


class GPSEmulator(threading.Thread):
    """ Эмулятор gps трекера - генерирует случайные координаты """
    def __init__(self):
        super().__init__()
        self.logger = Logger('GPSTracker')

    def get_coordinates(self):
        latitude = random.randint(-900000, 900000) / 10000
        longitude = random.randint(-1800000, 1800000) / 10000

        gps = {
            'latitude': latitude,
            'longitude': longitude,
            'datetime': datetime.now()
        }

        return gps

    def run(self):
        self.logger.info('start gps tracker')
        while True:
            try:
                coords = self.get_coordinates()
                redis_client_pickle.rpush('coordinates', pickle.dumps(coords))

                sleep(120)
            except Exception as e:
                self.logger.exception('Unexpected error')

