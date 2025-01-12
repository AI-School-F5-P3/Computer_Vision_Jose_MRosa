# main.py
import cv2
from models.detector import FaceDetector
from models.recognizer import FaceRecognizer
from utils.capture import WebcamCapture

face_detector = FaceDetector()
face_recognizer = FaceRecognizer()
face_recognizer.train_model("data/")
webcam = WebcamCapture()

while True:
    frame = webcam.get_frame()
    if frame is None:
        break

    faces = face_detector.detect_faces(frame)

    for (x1, y1, x2, y2) in faces:
        face_img = frame[y1:y2, x1:x2]
        gray_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        try:
            name, confidence = face_recognizer.predict(gray_face)
            label = f"{name} ({confidence:.2f})"
        except:
            label = "Unknown"

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    cv2.imshow("Face Recognition", frame)
    if cv2.waitKey(1) == 27:
        break

webcam.release()
cv2.destroyAllWindows()