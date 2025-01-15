# models/recognizer.py
import cv2
import os
import numpy as np

class FaceRecognizer:
    def __init__(self):
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()

    def train_model(self, data_path):
        images, labels = [], []
        label_map = {}
        current_label = 0

        for subdir in os.listdir(data_path):
            subject_path = os.path.join(data_path, subdir)
            if not os.path.isdir(subject_path):
                continue
            label_map[current_label] = subdir

            for filename in os.listdir(subject_path):
                img_path = os.path.join(subject_path, filename)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                images.append(img)
                labels.append(current_label)
            current_label += 1

        self.recognizer.train(images, np.array(labels))
        self.label_map = label_map

    def predict(self, face_img):
        label, confidence = self.recognizer.predict(face_img)
        return self.label_map[label], confidence