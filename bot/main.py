import requests
import subprocess
from threading import Thread
from datetime import timedelta

from bot.bot_config import SENDER_TOKEN, CHAT_ID
from config import Config


class CarBot(Thread):
    def __init__(self, network_check_interval=timedelta(minutes=1)):
        super().__init__()
        self.network_check_interval = network_check_interval.total_seconds()
        self.network_status = True

    def check_connection(self):
        ping_server = subprocess.Popen(
            ('ping', Config.STORAGE_SERVER_URL, '-c', '2'),
            stdout=subprocess.PIPE,
            encoding='utf-8'
        )

        for line in ping_server.stdout:
            if '100% packet loss' in line:
                return False

        return False

    def send_message(self, text):
        requests.get(f"https://api.telegram.org/bot{SENDER_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}")


if __name__ == '__main__':
    car_bot = CarBot()
    car_bot.check_connection()
