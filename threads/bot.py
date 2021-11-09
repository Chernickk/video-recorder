import requests
import subprocess
from threading import Thread
from datetime import timedelta
from time import sleep

from config import Config
from utils.redis_client import redis_client
from logs.logger import Logger


class CarBot(Thread):
    def __init__(self, car_id, network_check_interval=timedelta(minutes=1)):
        super().__init__()
        self.network_check_interval = network_check_interval.total_seconds()
        self.network_status = False
        self.has_files_to_upload = False
        self.car_id = car_id
        self.logger = Logger('TelegramBot')

    def check_connection(self):
        try:
            ping_server = subprocess.Popen(
                ('ping', Config.STORAGE_SERVER_URL, '-c', '2'),
                stdout=subprocess.PIPE,
                encoding='utf-8'
            )

            for line in ping_server.stdout:
                if ' 0% packet loss' in line:
                    return True
        except Exception as e:
            self.logger.exception(f"Bot error: {e}")
        return False

    def check_files(self):
        files_to_upload = redis_client.llen('ready_to_send')
        return True if files_to_upload else False

    def send_message(self, text):
        requests.get(f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"
                     f"/sendMessage?chat_id={Config.CHAT_ID}&text={text}")

    def run(self):
        self.send_message(f'Машина {self.car_id}. Запуск.')

        while True:
            try:
                status = self.network_status

                if self.check_connection():
                    if not status:
                        self.send_message(f'Машина {self.car_id} появилась в сети')
                        self.network_status = True

                    if self.has_files_to_upload and not self.check_files():
                        self.send_message(f'Машина {self.car_id}. Все файлы выгружены на сервер')
                        self.has_files_to_upload = False
                    elif self.check_files():
                        self.has_files_to_upload = True

                else:
                    self.network_status = False

                sleep(self.network_check_interval)

            except Exception as e:
                self.logger.exception(f'Bot. Unexpected error: {e}')


if __name__ == '__main__':
    car_bot = CarBot(1)
    car_bot.start()
