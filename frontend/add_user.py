from reactpy import component, html, use_state

@component
def AddUser(show, on_add):
    name, set_name = use_state("")
    images_taken, set_images_taken = use_state(0)

    # Función para añadir usuario solo si se han tomado 5 imágenes
    def handle_add():
        if images_taken == 5:
            on_add(name)
            set_name("")
            set_images_taken(0)

    # Función para simular la toma de imágenes
    def take_image():
        if images_taken < 5:
            set_images_taken(images_taken + 1)

    # Si el modal no está activo, no renderizar nada
    if not show:
        return None

    # Interfaz del componente con clases de Tailwind aplicadas directamente
    return html.div(
        {"class": "mt-4 bg-gray-100 p-4 rounded-lg"},
        html.h3({"class": "text-lg font-semibold mb-2"}, "Añadir Nuevo Usuario"),
        
        # Input para ingresar el nombre con clases Tailwind
        html.input(
            {
                "type": "text",
                "placeholder": "Nombre del usuario",
                "value": name,
                "on_change": lambda e: set_name(e["target"]["value"]),
                "class": "border rounded py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline mb-2 w-full",
            }
        ),
        
        # Simulación de la cámara y contador de imágenes
        html.div(
            {"class": "bg-gray-200 h-48 rounded-lg flex items-center justify-center mb-2"},
            f"Cámara (Imágenes tomadas: {images_taken}/5)"
        ),
        
        # Botones con Tailwind directamente
        html.button(
            {
                "on_click": take_image,
                "disabled": images_taken == 5,
                "class": "bg-blue-500 text-white font-bold py-2 px-4 rounded hover:bg-blue-700 mr-2 disabled:bg-gray-400"
            },
            "Tomar Imagen"
        ),
        html.button(
            {
                "on_click": handle_add,
                "disabled": images_taken < 5 or not name,
                "class": "bg-green-500 text-white font-bold py-2 px-4 rounded hover:bg-green-700 disabled:bg-gray-400"
            },
            "Guardar Usuario"
        ),
    )
