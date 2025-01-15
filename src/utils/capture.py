# utils/capture.py
import cv2

class WebcamCapture:
    def __init__(self, camera_index=0):
        self.capture = cv2.VideoCapture(camera_index)

    def get_frame(self):
        ret, frame = self.capture.read()
        if ret:
            return frame
        else:
            return None

    def release(self):
        self.capture.release()