from threading import Thread
from datetime import timedelta
from time import sleep

import requests

from config import Config
from utils.redis_client import redis_client
from utils.utils import ping_server, get_self_ip
from utils.variables import READY_TO_UPLOAD, READY_REQUESTED_FILES, ERROR_MESSAGES
from logs.logger import Logger


class CarBot(Thread):
    def __init__(self,
                 bot_token: str,
                 chat_id: int,
                 car_name: str,
                 network_check_interval=timedelta(minutes=1)):
        super().__init__()
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.network_check_interval = network_check_interval.total_seconds()
        self.network_status = False
        self.has_files_to_upload = False
        self.has_requested_files_to_upload = False
        self.car_name = car_name
        self.notified = False
        self.logger = Logger('TelegramBot')

    def send_message(self, text: str) -> None:
        """
        Send message using telegram API url
        :param text: str
        """
        sleep(5)
        requests.get(f"https://api.telegram.org/bot{self.bot_token}"
                     f"/sendMessage?chat_id={self.chat_id}&text={Config.CAR_LICENSE_TABLE}:{text}")

    def check_connection(self) -> None:
        """
        Check connection to home server
        Set 'self.network_status' param
        """
        status = False
        try:
            status = ping_server(Config.STORAGE_SERVER_URL)
        except Exception as error:
            self.logger.exception(f"Bot error: {error}")

        if status:
            if not self.network_status:
                local_ip = get_self_ip()
                self.send_message(f'Машина в сети. Адрес: {local_ip}')
                self.network_status = True
        else:
            self.network_status = False
            self.notified = False

    def check_regular_files(self) -> None:
        """
        Check files that should be upload regularly
        set 'self.has_files_to_upload' param
        """
        if not self.notified:
            files_to_upload = redis_client.llen(READY_TO_UPLOAD)

            if self.has_files_to_upload and not files_to_upload:
                self.send_message(f'Машина {self.car_name}. Записи выгружены на сервер')
                self.has_files_to_upload = False
                self.notified = True
            elif files_to_upload:
                self.has_files_to_upload = True

    def check_requested_files(self) -> None:
        """
        Check files that should be upload on request
        set 'self.has_requested_files_to_upload' param
        """
        files_to_upload = redis_client.llen(READY_REQUESTED_FILES)

        if self.has_requested_files_to_upload and not files_to_upload:
            self.send_message(f'Машина {self.car_name}. Запрошенные записи выгружены на сервер')
            self.has_requested_files_to_upload = False
        elif files_to_upload:
            self.has_requested_files_to_upload = True

    def check_errors(self) -> None:
        """
        Send error messages to telegram chat
        """
        for _ in range(redis_client.llen(ERROR_MESSAGES)):
            message = redis_client.lpop(ERROR_MESSAGES)
            self.send_message(message)

    def run(self) -> None:
        """
        Run telegram 'bot' thread
        """
        self.send_message(f'Запуск.')

        while True:
            try:
                self.check_connection()
                if self.network_status:
                    self.check_errors()
                    self.check_regular_files()
                    self.check_requested_files()
                    if not self.notified:
                        self.notified = True

            except Exception as error:
                self.logger.exception(f'Bot. Unexpected error: {error}')
            finally:
                sleep(self.network_check_interval)
