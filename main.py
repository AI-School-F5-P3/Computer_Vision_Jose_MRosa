from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import cv2
import face_recognition
import numpy as np
from pathlib import Path
import base64
from typing import List
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import threading
from fastapi.websockets import WebSocketState
from collections import deque
from PIL import Image
from vision_pipeline import VisionPipeline



app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vision_pipeline = VisionPipeline()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.frame_buffers = {}
        self._connection_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
            async with self._connection_lock:
                self.active_connections.append(websocket)
                self.frame_buffers[websocket] = deque(maxlen=2)
            print(f"Client connected. Total connections: {len(self.active_connections)}")
            return True
        except Exception as e:
            print(f"Error during connection: {e}")
            return False

    async def disconnect(self, websocket: WebSocket):
        async with self._connection_lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            if websocket in self.frame_buffers:
                del self.frame_buffers[websocket]
        try:
            await websocket.close()
        except Exception as e:
            print(f"Error during disconnect: {e}")
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def is_connected(self, websocket: WebSocket) -> bool:
        try:
            return (
                websocket in self.active_connections and 
                websocket.client_state != WebSocketState.DISCONNECTED and
                websocket.application_state != WebSocketState.DISCONNECTED
            )
        except Exception:
            return False

    async def add_frame(self, websocket: WebSocket, frame):
        if await self.is_connected(websocket):
            async with self._connection_lock:
                self.frame_buffers[websocket].append(frame)

    async def get_latest_frame(self, websocket: WebSocket):
        if websocket in self.frame_buffers and self.frame_buffers[websocket]:
            return self.frame_buffers[websocket][-1]
        return None

    async def send_json(self, websocket: WebSocket, data: dict):
        if await self.is_connected(websocket):
            try:
                await websocket.send_json(data)
                return True
            except Exception as e:
                print(f"Error sending JSON: {e}")
                await self.disconnect(websocket)
                return False
        return False

manager = ConnectionManager()

class FaceProcessor:
    def __init__(self):
        self.last_processed_time = 0
        self.processing_interval = 0.2  # Process every 200ms
        self.last_results = []
        self.processing = False
        self.frame_skip = 2  # Process every nth frame
        self.frame_count = 0
        self.processing_lock = threading.Lock()

    def should_process_frame(self):
        current_time = time.time()
        self.frame_count += 1
        
        if self.processing:
            return False
            
        if (current_time - self.last_processed_time) < self.processing_interval:
            return False
            
        if self.frame_count % self.frame_skip != 0:
            return False
            
        return True

    def process_frame(self, frame, known_face_encodings, known_face_names):
        if not self.should_process_frame():
            return self.last_results

        with self.processing_lock:
            if self.processing:
                return self.last_results
            self.processing = True

        try:
            # Resize frame for faster processing
            frame_height, frame_width = frame.shape[:2]
            scale = 1.0
            if frame_width > 640:
                scale = 640 / frame_width
                frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame, model="hog", number_of_times_to_upsample=1)
            
            if not face_locations:
                self.last_results = []
                return []

            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=1)
            
            results = []
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                if len(known_face_encodings) > 0:
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    
                    # Calculate confidence percentage (face_distance of 0 = 100% match, 1 = 0% match)
                    confidence = (1 - face_distances[best_match_index]) * 100

                    if face_distances[best_match_index] < 0.6:
                        name = known_face_names[best_match_index]
                        access_status = "AUTHORIZED"
                    else:
                        name = "Unknown"
                        access_status = "DENIED"
                        confidence = 0  # Set to 0 for unknown faces

                if scale != 1.0:
                    top = int(top / scale)
                    right = int(right / scale)
                    bottom = int(bottom / scale)
                    left = int(left / scale)

                results.append({
                    "location": (top, right, bottom, left),
                    "name": name,
                    "status": access_status,
                    "confidence": round(confidence, 1)  # Round to 1 decimal place
                })

            self.last_results = results
            self.last_processed_time = time.time()
            return results

        finally:
            self.processing = False

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

    
    

    async def process_frame(self, frame):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.face_processor.process_frame,
            frame,
            self.known_face_encodings,
            self.known_face_names
        )

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

face_system = FaceRecognitionSystem()


@app.get("/")  #RUTA RAIZ AÑADIDA
async def read_root():
    return {"message": "Bienvenido al sistema de detección facial de Factoría F5"}

@app.websocket("/ws/video")
async def video_websocket(websocket: WebSocket):
    if not await manager.connect(websocket):
        return
    
    try:
        while await manager.is_connected(websocket):
            try:
                # Set a timeout for receiving data
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
                
                await manager.add_frame(websocket, frame)
                
                try:
                    # Get current analysis type from app state
                    analysis_type = getattr(websocket.app.state, 'analysis_type', None)
                    
                    # Process face recognition
                    face_results = await asyncio.wait_for(
                        face_system.process_frame(frame),
                        timeout=5.0
                    )
                    
                    # Process vision pipeline with current analysis type
                    vision_results = await vision_pipeline.process_frame(frame, analysis_type) if analysis_type else {}
                    
                    # Combine results
                    response = {
                        "face_results": face_results,
                        "vision_results": vision_results
                    }
                    
                    if not await manager.send_json(websocket, response):
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
                if not await manager.is_connected(websocket):
                    break
                continue
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket)

@app.post("/users")
async def add_user(username: str, images: List[UploadFile] = File(...)):
    return await face_system.add_user(username, images)

@app.get("/users")
async def get_users():
    users = [dir.name for dir in face_system.dataset_path.iterdir() if dir.is_dir()]
    return {"users": users}

@app.post("/set-analysis")
async def set_analysis(request: Request, data: dict):
    analysis_type = data.get("type", "none")
    
    # Store the analysis type in app.state
    request.app.state.analysis_type = analysis_type
    print(f'Analysis type set to {analysis_type}')
    
    return {
        "status": "success", 
        "type": analysis_type,
        "message": f"Analysis type set to: {analysis_type}"
    }




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1)



