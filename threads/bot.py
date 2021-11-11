import requests
import subprocess
from threading import Thread
from datetime import timedelta
from time import sleep

from config import Config
from utils.redis_client import redis_client
from logs.logger import Logger


class CarBot(Thread):
    def __init__(self, bot_token, chat_id, car_id, network_check_interval=timedelta(minutes=1)):
        super().__init__()
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.network_check_interval = network_check_interval.total_seconds()
        self.network_status = False
        self.has_files_to_upload = False
        self.has_requested_files_to_upload = False
        self.car_id = car_id
        self.logger = Logger('TelegramBot')

    def send_message(self, text):
        requests.get(f"https://api.telegram.org/bot{self.bot_token}"
                     f"/sendMessage?chat_id={self.chat_id}&text={text}")

    def check_connection(self):
        status = False
        try:
            ping_server = subprocess.Popen(
                ('ping', Config.STORAGE_SERVER_URL, '-c', '2'),
                stdout=subprocess.PIPE,
                encoding='utf-8'
            )

            for line in ping_server.stdout:
                if ' 0% packet loss' in line:
                    status = True
        except Exception as e:
            self.logger.exception(f"Bot error: {e}")

        if status:
            if not self.network_status:
                self.send_message(f'Машина {self.car_id} появилась в сети')
                self.network_status = True
        else:
            self.network_status = False

    def check_regular_files(self):
        files_to_upload = redis_client.llen('ready_to_send')

        if self.has_files_to_upload and not files_to_upload:
            self.send_message(f'Машина {self.car_id}. Записи выгружены на сервер')
            self.has_files_to_upload = False
        elif files_to_upload:
            self.has_files_to_upload = True

    def check_requested_files(self):
        files_to_upload = redis_client.llen('ready_requested_videos')

        if self.has_requested_files_to_upload and not files_to_upload:
            self.send_message(f'Машина {self.car_id}. Запрошенные записи выгружены на сервер')
            self.has_requested_files_to_upload = False
        elif files_to_upload:
            self.has_requested_files_to_upload = True

    def check_errors(self):
        for _ in range(redis_client.llen('error_messages')):
            message = redis_client.lpop('error_messages')
            self.send_message(message)

    def run(self):
        self.send_message(f'Машина {self.car_id}. Запуск.')

        while True:
            try:
                self.check_connection()
                if self.network_status:
                    self.check_errors()
                    self.check_regular_files()
                    self.check_requested_files()

                sleep(self.network_check_interval)

            except Exception as e:
                self.logger.exception(f'Bot. Unexpected error: {e}')
