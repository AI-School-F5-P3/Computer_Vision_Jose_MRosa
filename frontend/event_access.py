from reactpy import component, html, use_state

@component
def EventAccess():
    camera_active, set_camera_active = use_state(False)

    # Alternar el estado de la cámara
    def toggle_camera():
        set_camera_active(lambda prev: not prev)

    return html.div(
        {"class": "flex-1"},
        
        # Imagen de ejemplo con estilos Tailwind
        html.img(
            {
                "src": "/placeholder.svg?height=300&width=400",
                "alt": "Imagen descriptiva del evento",
                "class": "w-full h-auto mb-4 rounded-lg"
            }
        ),
        
        # Botón con estilos Tailwind directamente
        html.button(
            {
                "on_click": toggle_camera,
                "class": "bg-blue-500 text-white font-bold py-2 px-4 rounded hover:bg-blue-700"
            },
            "Iniciar cámara" if not camera_active else "Detener cámara"
        ),
        
        # Mostrar la cámara solo si está activa
        html.div(
            {"class": "mt-4 bg-gray-200 h-48 rounded-lg flex items-center justify-center"},
            f"Cámara {'activa' if camera_active else 'inactiva'}"
        ) if camera_active else None,
    )
