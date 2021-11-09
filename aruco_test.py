import cv2
import os

def record_video():
    """ Запись одного видеофайла """
    # формирования строки с датой для названия видеофайла
    capture = cv2.VideoCapture('rtsp://admin:Ckj;ysqgfhjkm13@10.10.10.50/1')

    dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)
    parameters = cv2.aruco.DetectorParameters_create()

    status, frame = capture.read()


    print(capture.isOpened())

    # frame = cv2.cvtColor(
    #     frame,
    #     cv2.COLOR_BGR2GRAY
    # )

    # frame = cv2.GaussianBlur(frame, (3, 3), 0)

    # _, frame = cv2.threshold(frame, 150, 255,
    #                               cv2.THRESH_BINARY)

    cv2.imwrite('test1.png', frame)

    marker_corners, marker_ids, rejected_candidates = cv2.aruco.detectMarkers(frame, dictionary, parameters=parameters)
    print(marker_ids)
    print(len(marker_ids))

if __name__ == '__main__':
    record_video()
