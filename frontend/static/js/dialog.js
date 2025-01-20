



// Referencias al popup y botón
const popup = document.getElementById('popup');
const closeButton = document.getElementById('closeButton');

// Mostrar el popup
function showPopup() {
  popup.classList.remove('opacity-0', 'pointer-events-none');
  popup.classList.add('opacity-100');
}

// Ocultar el popup
function hidePopup() {
  popup.classList.remove('opacity-100');
  popup.classList.add('opacity-0', 'pointer-events-none');
}

// Asignar eventos
closeButton.addEventListener('click', hidePopup);

// Prueba: Muestra el popup después de 1 segundo
setTimeout(showPopup, 1000);

document.getElementById('openButton').addEventListener('click', showPopup);
