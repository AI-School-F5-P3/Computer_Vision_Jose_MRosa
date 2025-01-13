# main.py
import cv2
from models.detector import FaceDetector
from models.recognizer import FaceRecognizer
from utils.capture import WebcamCapture
import os

# Crear la carpeta si no existe
data_path = "dataset/"
if not os.path.exists(data_path):
    os.makedirs(data_path)
    print(f"Carpeta '{data_path}' creada con éxito.")
else:
    print(f"La carpeta '{data_path}' ya existe.")

# Eliminar modelo anterior si existe
if os.path.exists("trained_model.yml"):
    os.remove("trained_model.yml")
    print("Modelo anterior eliminado. Entrenando un nuevo modelo...")

face_detector = FaceDetector()
face_recognizer = FaceRecognizer()
face_recognizer.train_model(data_path)
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
            if confidence < 90:  # Umbral de confianza aumentado
                label = f"{name} ({confidence:.2f})"
                color = (0, 255, 0)  # Verde para confianza alta
            else:
                label = "Unknown"
                color = (0, 0, 255)  # Rojo para baja confianza
        except:
            label = "Unknown"
            color = (0, 0, 255)  # Rojo para no reconocido

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    cv2.imshow("Face Recognition", frame)
    if cv2.waitKey(1) == 27:
        break

webcam.release()
cv2.destroyAllWindows()
