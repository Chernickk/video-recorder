import pysftp
import os
import time


start_time = time.time()

with pysftp.Connection('192.168.202.94', username='user', password='videopsw') as sftp:
    with sftp.cd('/home/user/videoserver/media'):
        for filename in sftp.listdir():
            print(f'start download {filename}')
            # if filename not in os.listdir():
            #     sftp.get(filename)
            if filename.startswith('2021-10-13_14'):
                print(f'start download {filename}')
                sftp.get(filename)
                print(f'{filename} download complete')

        print("Download files successfully")

print(f'total time: {time.time() - start_time}')
