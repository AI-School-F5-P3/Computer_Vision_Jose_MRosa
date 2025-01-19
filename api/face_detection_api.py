from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import asyncio
import cv2
import numpy as np
import base64

from src.connection_manager import ConnectionManager
from src.face_recontition_system import FaceRecognitionSystem

class FaceDetectionAPI:
    def __init__(self):
        self.app = FastAPI(
            title="Detector de Caras",
            description="API para detectar a los Compañeros de Factoría F5",
            version="1.0.0"
        )
        self.manager = ConnectionManager()
        self.face_system = FaceRecognitionSystem()
        self.configure_routes()
        self.enable_cors()

    def enable_cors(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def configure_routes(self):
        self.app.websocket("/ws/video")(self.video_websocket)
        self.app.post("/add_user")(self.add_user)
        self.app.get("/users")(self.get_users)
        self.app.get("/")(self.read_root)  # Ruta raíz añadida
    
    async def read_root(self):
        return {"message": "Bienvenido al sistema de detección facial de Factoría F5"}

    async def video_websocket(self, websocket: WebSocket):
        if not await self.manager.connect(websocket):
            return

        try:
            while await self.manager.is_connected(websocket):
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=120.0)
                    try:
                        encoded_data = data.split(',')[1]
                        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    except Exception as e:
                        print(f"Error decoding frame: {e}")
                        continue

                    if frame is None:
                        continue

                    await self.manager.add_frame(websocket, frame)

                    try:
                        results = await asyncio.wait_for(
                            self.face_system.process_frame(frame),
                            timeout=5.0
                        )

                        if not await self.manager.send_json(websocket, {"results": results}):
                            break

                    except asyncio.TimeoutError:
                        print("Frame processing timeout")
                        continue
                    except Exception as e:
                        print(f"Error processing frame: {e}")
                        continue

                except asyncio.TimeoutError:
                    print("WebSocket receive timeout")
                    break
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    print(f"Error in websocket loop: {e}")
                    if not await self.manager.is_connected(websocket):
                        break
                    continue

        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            await self.manager.disconnect(websocket)

    async def add_user(self, username: str, images: List[UploadFile] = File(...)):
        return await self.face_system.add_user(username, images)

    async def get_users(self):
        users = [dir.name for dir in self.face_system.dataset_path.iterdir() if dir.is_dir()]
        return {"users": users}

# Para ser utilizado desde otro archivo:
# from src.face_detection_api import FaceDetectionAPI
# api_instance = FaceDetectionAPI()
# app = api_instance.app
