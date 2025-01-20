// Referencias al popup y botones
const popup = document.getElementById('addUserDialog');
const closeButton = document.getElementById('cancelBtn');
const openButton = document.getElementById('openButton');

// Mostrar el popup
const showPopup = () => {
    popup.classList.remove('opacity-0', 'pointer-events-none');
    popup.classList.add('opacity-100');
}

// Ocultar el popup
const hidePopup = () => {
    popup.classList.remove('opacity-100');
    popup.classList.add('opacity-0', 'pointer-events-none');
    resetForm();
}

// Asignar eventos
closeButton.addEventListener('click', hidePopup);

openButton.onclick = () => {
  if (isStreaming) {
    showPopup() 
  }
  else{
     alert('Please start the camera first');
      return;
  }

};

cancelBtn.onclick = () => {
  if (confirm('¿Seguro de que deseas cancelar? Se descartarán todas las imágenes capturadas.')) {
    hidePopup()
  }
};

const resetForm = () => {
  usernameInput.value = '';
  capturedImages.length = 0;
  updateCapturedImages();
  saveUserBtn.disabled = true;
  captureBtn.disabled = !isStreaming;
}



