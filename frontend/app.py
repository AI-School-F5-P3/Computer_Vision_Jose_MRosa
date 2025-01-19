from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.face_detection_api import FaceDetectionAPI

# Crear la aplicación FastAPI con la clase FaceDetectionAPI
api_instance = FaceDetectionAPI()
app = api_instance.app

# Configurar CORS para permitir solicitudes desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar carpeta estática para servir CSS e imágenes
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# ✅ Ejecución con Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
