from reactpy import component, html

@component
def UserList(users, on_add_click):
    return html.div(
        {"class": "bg-white p-4 rounded-lg shadow"},
        
        # Título del listado
        html.h2({"class": "text-xl font-bold mb-4"}, "Usuarios Registrados"),
        
        # Lista de usuarios
        html.ul(
            {"class": "space-y-2"},
            [html.li({"key": user["id"]}, user["name"]) for user in users],
        ),
        
        # Botón con estilos Tailwind directamente aplicados
        html.button(
            {
                "on_click": on_add_click,
                "class": "mt-4 bg-green-500 text-white font-bold py-2 px-4 rounded hover:bg-green-700"
            },
            "Añadir Nuevo Usuario"
        ),
    )
