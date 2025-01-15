import os
import cv2
from urllib.request import urlretrieve

class FaceDetector:
    def __init__(self, model_path="src/models/deploy.prototxt", weights_path="src/models/res10_300x300_ssd_iter_140000_fp16.caffemodel"):
        self.download_model(model_path, weights_path)
        self.net = cv2.dnn.readNetFromCaffe(model_path, weights_path)
        self.in_width = 300
        self.in_height = 300
        self.mean = [104, 117, 123]
        self.conf_threshold = 0.7

    def download_model(self, model_path, weights_path):
        if not os.path.exists(model_path) or not os.path.exists(weights_path):
            print("Downloading model files...")
            urlretrieve("https://github.com/spmallick/learnopencv/raw/master/FaceDetectionComparison/models/deploy.prototxt", model_path)
            urlretrieve("https://github.com/spmallick/learnopencv/raw/master/FaceDetectionComparison/models/res10_300x300_ssd_iter_140000_fp16.caffemodel", weights_path)
            print("Download complete!")

    def detect_faces(self, frame):
        frame_height, frame_width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (self.in_width, self.in_height), self.mean, swapRB=False, crop=False)
        self.net.setInput(blob)
        detections = self.net.forward()

        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > self.conf_threshold:
                x_left_bottom = int(detections[0, 0, i, 3] * frame_width)
                y_left_bottom = int(detections[0, 0, i, 4] * frame_height)
                x_right_top = int(detections[0, 0, i, 5] * frame_width)
                y_right_top = int(detections[0, 0, i, 6] * frame_height)
                faces.append((x_left_bottom, y_left_bottom, x_right_top, y_right_top))

        return faces
