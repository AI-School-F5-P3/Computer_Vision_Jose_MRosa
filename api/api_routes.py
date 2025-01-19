from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Request, HTTPException
import asyncio
import cv2
import numpy as np
import base64
from typing import List

api_router = APIRouter()

from src.face_recontition_system import FaceRecognitionSystem

@api_router.get("/")
async def read_root():
    return {"message": "Bienvenido al sistema de detección facial de Factoría F5"}

@api_router.websocket("/ws/video")
async def video_websocket(websocket: WebSocket):
    manager = websocket.app.state.manager
    face_system = websocket.app.state.face_system
    vision_pipeline = websocket.app.state.vision_pipeline

    if not await manager.connect(websocket):
        return

    try:
        while await manager.is_connected(websocket):
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=120.0)
                encoded_data = data.split(',')[1]
                frame = cv2.imdecode(np.frombuffer(base64.b64decode(encoded_data), np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                await manager.add_frame(websocket, frame)

                analysis_type = getattr(websocket.app.state, 'analysis_type', None)
                face_results = await asyncio.wait_for(face_system.process_frame(frame), timeout=5.0)
                vision_results = await vision_pipeline.process_frame(frame, analysis_type) if analysis_type else {}

                response = {"face_results": face_results, "vision_results": vision_results}
                if not await manager.send_json(websocket, response):
                    break
            except asyncio.TimeoutError:
                print("WebSocket timeout")
            except Exception as e:
                print(f"Error in WebSocket loop: {e}")
    finally:
        await manager.disconnect(websocket)

@api_router.post("/users")
async def add_user(request: Request, username: str, images: List[UploadFile] = File(...)):
    print(f"Username received: {username}")
    print(f"Number of images received: {len(images)}")
    for image in images:
        print(f"Image: {image.filename}, Content-Type: {image.content_type}")
    face_system = FaceRecognitionSystem()
    # Validaciones
    if not username or len(username) < 3:
        raise HTTPException(status_code=422, detail="Username must be at least 3 characters long")
    if not images:
        raise HTTPException(status_code=422, detail="At least one image is required")
    for image in images:
        if image.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=422, detail="Only JPEG and PNG images are allowed")
    
    # Lógica de procesamiento
    face_system = request.app.state.face_system
    return await face_system.add_user(username, images)

@api_router.get("/users")
async def get_users(request: Request):
    face_system = request.app.state.face_system
    users = [dir.name for dir in face_system.dataset_path.iterdir() if dir.is_dir()]
    return {"users": users}


@api_router.post("/set-analysis")
async def set_analysis(request: Request, data: dict):
    analysis_type = data.get("type", "none")
    request.app.state.analysis_type = analysis_type
    print(f'Analysis type set to {analysis_type}')
    return {
        "status": "success",
        "type": analysis_type,
        "message": f"Analysis type set to: {analysis_type}"
    }
