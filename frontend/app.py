from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from reactpy import component, html, use_state
from reactpy.backend.fastapi import configure
from fastapi.staticfiles import StaticFiles

from api.face_detection_api import FaceDetectionAPI

# ✅ Importación de componentes personalizados
from frontend.event_access import EventAccess
from frontend.user_list import UserList
from frontend.add_user import AddUser

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

# ✅ Definición del componente principal con los componentes personalizados
@component
def Main():
    # Estado para almacenar usuarios y control del modal
    users, set_users = use_state([
        {"id": 1, "name": "Usuario 1"},
        {"id": 2, "name": "Usuario 2"},
        {"id": 3, "name": "Usuario 3"},
    ])
    show_add_user, set_show_add_user = use_state(False)

    # Alternar visibilidad del formulario para agregar un nuevo usuario
    def toggle_add_user():
        set_show_add_user(lambda prev: not prev)

    # Añadir un nuevo usuario
    def add_user(name):
        new_user = {"id": len(users) + 1, "name": name}
        set_users(lambda prev: prev + [new_user])
        set_show_add_user(False)

    # ✅ Integrando los componentes personalizados
    return html._(
        html.link({
            "href": "https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css",
            "rel": "stylesheet"
        }),
        html.link({"rel": "stylesheet", "href": "/static/css/main.css"}),  # CSS local opcional
        html.div(
            {"class": "container mx-auto p-4"},
            html.div(
                {"class": "flex flex-col md:flex-row gap-8"},
                
                # ✅ Usando componentes importados
                EventAccess(),
                html.div(
                    {"class": "flex-1"},
                    UserList(users=users, on_add_click=toggle_add_user),
                    AddUser(show=show_add_user, on_add=add_user) if show_add_user else None,
                ),
            ),
        )
    )

# ✅ Integración de FastAPI con ReactPy usando `configure`
configure(app, Main)

# ✅ Ejecución con Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
