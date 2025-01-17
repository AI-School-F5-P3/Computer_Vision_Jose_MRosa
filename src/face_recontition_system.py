from fastapi import UploadFile, File, HTTPException
import cv2
import face_recognition
import numpy as np
from pathlib import Path
from typing import List
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

import os
from datetime import datetime

from src.face_processor import FaceProcessor

# DEFINE EL DIRECTORIO BASE PARA LOS LOGS
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

class FaceRecognitionSystem:
    def __init__(self, dataset_path="dataset"):
        self.dataset_path = Path(dataset_path)
        self.dataset_path.mkdir(exist_ok=True)
        self.known_face_encodings = []
        self.known_face_names = []
        self.face_processor = FaceProcessor()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.encoding_lock = threading.Lock()
        self.detected_users = set()  # TRACK USERS WHOSE IMAGES ARE ALREADY LOGGED
        self.load_known_faces()

    def load_known_faces(self):
        print("Loading known faces...")
        with self.encoding_lock:
            temp_encodings = []
            temp_names = []

            for person_dir in self.dataset_path.iterdir():
                if person_dir.is_dir():
                    name = person_dir.name
                    for image_path in person_dir.glob("*.jpg"):
                        try:
                            face_image = face_recognition.load_image_file(str(image_path))
                            face_encoding = face_recognition.face_encodings(face_image)[0]
                            temp_encodings.append(face_encoding)
                            temp_names.append(name)
                            print(f"Loaded face for: {name}")
                        except Exception as e:
                            print(f"Error processing {image_path}: {e}")

            self.known_face_encodings = temp_encodings
            self.known_face_names = temp_names

        print(f"Loaded {len(self.known_face_names)} face(s)")

    # NUEVO MÉTODO: GUARDA LA IMAGEN RECONOCIDA JUNTO CON LA HORA Y EL DÍA EN EL SISTEMA DE LOGS
    def save_recognition_log(self, frame, name, location):
        """Guarda la imagen reconocida junto con la hora y el día en el sistema de logs."""
        try:
            # OBTENER TIMESTAMP ACTUAL
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # CREAR CARPETA PARA EL USUARIO
            user_log_dir = os.path.join(LOG_DIR, name)
            full_log_dir = os.path.join(user_log_dir, "full")
            face_log_dir = os.path.join(user_log_dir, "face")

            os.makedirs(full_log_dir, exist_ok=True)
            os.makedirs(face_log_dir, exist_ok=True)

            # EXTRAER LA REGIÓN DE LA CARA
            top, right, bottom, left = location
            face_image = frame[top:bottom, left:right]

            # GUARDAR LA IMAGEN COMPLETA Y LA REGIÓN DE LA CARA
            image_path = os.path.join(full_log_dir, f"{timestamp}_full.jpg")
            face_image_path = os.path.join(face_log_dir, f"{timestamp}_face.jpg")

            cv2.imwrite(image_path, frame)
            cv2.imwrite(face_image_path, face_image)

            print(f"Logged recognition for {name} at {timestamp}")
        except Exception as e:
            print(f"Error saving log for {name}: {e}")

    async def process_frame(self, frame):
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            self.executor,
            self.face_processor.process_frame,
            frame,
            self.known_face_encodings,
            self.known_face_names
        )

        # NUEVA LÓGICA: SOLO GUARDAR IMÁGENES LA PRIMERA VEZ QUE SE DETECTA A UN USUARIO AUTORIZADO
        for result in results:
            if result['status'] == "AUTHORIZED" and result['name'] not in self.detected_users:
                self.save_recognition_log(frame, result['name'], result['location'])
                self.detected_users.add(result['name'])
        return results

    async def add_user(self, username: str, images: List[UploadFile]):
        user_path = self.dataset_path / username
        if user_path.exists():
            raise HTTPException(status_code=400, detail="User already exists")
        
        temp_path = self.dataset_path / f"temp_{username}"
        temp_path.mkdir(parents=True)
        
        try:
            for idx, image in enumerate(images):
                content = await image.read()
                nparr = np.frombuffer(content, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is None:
                    raise HTTPException(status_code=400, detail=f"Could not decode image {idx+1}")
                
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_img)
                
                if len(face_locations) != 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Image {idx+1} contains {len(face_locations)} faces. Each image must contain exactly one face."
                    )
                
                image_path = temp_path / f"{username}_{idx+1}.jpg"
                cv2.imwrite(str(image_path), img)
            
            temp_path.rename(user_path)
            self.load_known_faces()
            return {"message": f"Successfully added user {username}"}
            
        except Exception as e:
            if temp_path.exists():
                import shutil
                shutil.rmtree(temp_path)
            raise e
