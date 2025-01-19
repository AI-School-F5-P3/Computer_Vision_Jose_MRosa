from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.vision_pipeline import VisionPipeline
from src.connection_manager import ConnectionManager
from src.face_recontition_system import FaceRecognitionSystem
from api.api_routes import api_router

app = FastAPI(
    title="Detector de Caras",
    description="API para detectar a los Compañeros de Factoría F5",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize shared resources
app.state.vision_pipeline = VisionPipeline()
app.state.manager = ConnectionManager()
app.state.face_system = FaceRecognitionSystem()

# Include all API routes
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1)
