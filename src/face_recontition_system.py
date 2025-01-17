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
            os.makedirs(user_log_dir, exist_ok=True)

            # EXTRAER LA REGIÓN DE LA CARA
            top, right, bottom, left = location
            face_image = frame[top:bottom, left:right]

            # GUARDAR LA IMAGEN COMPLETA Y LA REGIÓN DE LA CARA
            image_path = os.path.join(user_log_dir, f"{timestamp}_full.jpg")
            face_image_path = os.path.join(user_log_dir, f"{timestamp}_face.jpg")

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
    
        # NUEVA LÓGICA: GUARDA LAS IMÁGENES DE LAS CARAS RECONOCIDAS
        for result in results:
            if result['status'] == "AUTHORIZED":
                self.save_recognition_log(frame, result['name'], result['location'])
        
        return results