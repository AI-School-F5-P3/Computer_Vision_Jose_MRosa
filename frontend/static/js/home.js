// Global variables with improved configuration
let isStreaming = false;
let ws = null;
let stream = null;
const capturedImages = [];
let lastFrameTime = 0;
const FRAME_INTERVAL = 200; // Increased to 200ms for better stability
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
let lastReceivedResults = [];
let lastVisionState = null;
let animationFrameId = null;
let reconnectTimeout = null;

// DOM Elements
const video = document.getElementById('video');
const overlay = document.getElementById('overlay');
const toggleBtn = document.getElementById('toggleCamera');

const addUserDialog = document.getElementById('addUserDialog');
const usernameInput = document.getElementById('username');
const captureBtn = document.getElementById('captureBtn');
const saveUserBtn = document.getElementById('saveUserBtn');
const cancelBtn = document.getElementById('cancelBtn');
const userList = document.getElementById('userList');
const capturedImagesContainer = document.getElementById('capturedImages');

// Set initial canvas size
overlay.width = 770;
overlay.height = 480;

// Improved WebSocket connection with better error handling
function setupWebSocket() {
    if (ws) {
        ws.close();
    }

    ws = new WebSocket('ws://localhost:8000/ws/video');
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttempts = 0; // Reset reconnect attempts on successful connection
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
        }
    };
    
    ws.onmessage = handleWsMessage;
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reconnectAttempts++;
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        if (isStreaming && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            // Exponential backoff for reconnection
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
            reconnectTimeout = setTimeout(setupWebSocket, delay);
        } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            alert('Connection lost. Please refresh the page to reconnect.');
            stopStream();
        }
    };
}

// Camera Controls
toggleBtn.onclick = async () => {
    if (isStreaming) {
        stopStream();
    } else {
        await startStream();
    }
};

async function startStream() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 770 },
                height: { ideal: 480 },
                facingMode: 'user',
                frameRate: { ideal: 15 }
            }
        });
        
        video.srcObject = stream;
        
        await new Promise((resolve) => {
            video.onloadedmetadata = () => resolve();
        });
        
        await video.play();
        
        const videoTrack = stream.getVideoTracks()[0];
        const settings = videoTrack.getSettings();
        
        overlay.width = settings.width || 770;
        overlay.height = settings.height || 480;
        
        isStreaming = true;
        toggleBtn.textContent = 'Stop Camera';
        toggleBtn.classList.add('camera-active'); 
        video.parentNode.classList.add('video-active');
        captureBtn.disabled = false;
        
        setupWebSocket();
        animationFrameId = requestAnimationFrame(sendFrame);
        
    } catch (error) {
        console.error('Error accessing camera:', error);
        alert('Error accessing camera. Please ensure camera permissions are granted.');
    }
}

function stopStream() {
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }
    
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }
    
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
    
    if (ws) {
        ws.close();
    }
    
    isStreaming = false;
    toggleBtn.textContent = 'Start Camera';
    toggleBtn.classList.remove('camera-active');
    video.parentNode.classList.remove('video-active'); 
    captureBtn.disabled = true;
    lastVisionState = null;
    
    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    lastReceivedResults = [];
}

function sendFrame() {
    if (!isStreaming || !ws || ws.readyState !== WebSocket.OPEN) {
        animationFrameId = requestAnimationFrame(sendFrame);
        return;
    }

    const currentTime = performance.now();
    if (currentTime - lastFrameTime < FRAME_INTERVAL) {
        animationFrameId = requestAnimationFrame(sendFrame);
        return;
    }

    try {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d', { alpha: false });
        
        if (!video.videoWidth || !video.videoHeight) {
            animationFrameId = requestAnimationFrame(sendFrame);
            return;
        }
        
        ctx.drawImage(video, 0, 0);
        const base64Frame = canvas.toDataURL('image/jpeg', 0.6);
        
        if (ws.bufferedAmount === 0) {
            ws.send(base64Frame);
            lastFrameTime = currentTime;
        }
    } catch (error) {
        console.error('Error sending frame:', error);
    }

    animationFrameId = requestAnimationFrame(sendFrame);
}

function handleWsMessage(event) {
    try {
        const data = JSON.parse(event.data);
        
        // Update vision state based on received results
        if (data.vision_results) {
            lastVisionState = data.vision_results;
        } else {
            lastVisionState = null;
        }
        
        if (data.face_results) {
            const results = {
                face_results: data.face_results,
                vision_results: lastVisionState
            };
            lastReceivedResults = results;
            drawResults(results);
        }
    } catch (error) {
        console.error('Error processing WebSocket message:', error);
    }
}

function drawResults(results) {
    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = overlay.width;
    offscreenCanvas.height = overlay.height;
    const offscreenCtx = offscreenCanvas.getContext('2d', { alpha: true });
    
    offscreenCtx.clearRect(0, 0, overlay.width, overlay.height);
    
    const { face_results = [], vision_results = {} } = results;
    
    if (!face_results.length) {
        const ctx = overlay.getContext('2d');
        ctx.clearRect(0, 0, overlay.width, overlay.height);
        return;
    }

    const scaleX = overlay.width / video.videoWidth;
    const scaleY = overlay.height / video.videoHeight;

    face_results.forEach((result, index) => {
        if (!result.location || result.location.length !== 4) return;

        const [top, right, bottom, left] = result.location;
        const color = result.status === 'AUTHORIZED' ? '#22c55e' : '#ef4444';

        const scaledLeft = left * scaleX;
        const scaledTop = top * scaleY;
        const scaledWidth = (right - left) * scaleX;
        const scaledHeight = (bottom - top) * scaleY;

        // Draw face box
        offscreenCtx.strokeStyle = color;
        offscreenCtx.lineWidth = 2;
        offscreenCtx.strokeRect(scaledLeft, scaledTop, scaledWidth, scaledHeight);

        // Draw name and confidence label
        offscreenCtx.font = 'bold 14px Arial';
        const nameText = `${result.name} (${result.confidence?.toFixed(1) || 0}%)`;
        const nameMetrics = offscreenCtx.measureText(nameText);
        const namePadding = 10;

        // Background for name
        offscreenCtx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        offscreenCtx.fillRect(
            scaledLeft,
            Math.max(0, scaledTop - 20 - namePadding),
            nameMetrics.width + (namePadding * 2),
            30
        );

        // Draw name text
        offscreenCtx.fillStyle = 'white';
        offscreenCtx.fillText(
            nameText,
            scaledLeft + namePadding,
            Math.max(16, scaledTop - namePadding)
        );

        // Generate vision analysis text based on available results
        let visionText = '';
        if (vision_results) {
            if (vision_results.emotion) {
                visionText = `Emotion: ${vision_results.emotion.emotion} (${(vision_results.emotion.confidence * 100).toFixed(1)}%)`;
            } else if (vision_results.mask) {
                const maskStatus = vision_results.mask.wearing_mask ? 'Wearing Mask' : 'No Mask';
                visionText = `Mask: ${maskStatus} (${(vision_results.mask.confidence * 100).toFixed(1)}%)`;
            } else if (vision_results.people) {
                visionText = `People Count: ${vision_results.people.count}`;
            }
        }

        if (visionText) {
            const statusMetrics = offscreenCtx.measureText(visionText);
            const statusHeight = 30;
            const statusPadding = 10;

            // Background for vision analysis
            offscreenCtx.fillStyle = 'rgba(0, 0, 0, 0.8)';
            offscreenCtx.fillRect(
                scaledLeft,
                scaledTop + scaledHeight + namePadding,
                statusMetrics.width + (statusPadding * 2),
                statusHeight
            );

            // Draw vision analysis text
            offscreenCtx.fillStyle = 'white';
            offscreenCtx.fillText(
                visionText,
                scaledLeft + statusPadding,
                scaledTop + scaledHeight + statusHeight
            );
        }

        // Draw authorization status
        const authStatusText = result.status;
        const authStatusMetrics = offscreenCtx.measureText(authStatusText);
        const authStatusPadding = 10;

        offscreenCtx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        offscreenCtx.fillRect(
            scaledLeft,
            scaledTop + scaledHeight + (visionText ? 32 : 0) + namePadding,
            authStatusMetrics.width + (authStatusPadding * 2) ,
            30
        );

        offscreenCtx.fillStyle = color;
        offscreenCtx.fillText(
            authStatusText,
            scaledLeft + authStatusPadding,
            scaledTop + scaledHeight + (visionText ? 32 : 0) + 30
        );
    });

    const ctx = overlay.getContext('2d', { alpha: true });
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    ctx.drawImage(offscreenCanvas, 0, 0);
}

// User Management
async function fetchUsers() {
    try {
        const response = await fetch('http://localhost:8000/users');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        displayUsers(data.users);
    } catch (error) {
        console.error('Error fetching users:', error);
        alert('Error loading users. Please try again later.');
    }
}

function displayUsers(users) {
    userList.innerHTML = users.map(user => 
        `<div class="user-item">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
        </svg>
        ${user}
        </div>`
    ).join('');
}

// Image Capture
captureBtn.onclick = () => {
    if (!isStreaming) return;
    
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d', { alpha: false });
    
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(video, 0, 0);
    
    canvas.toBlob((blob) => {
        if (blob) {
            capturedImages.push(blob);
            updateCapturedImages();
            if (capturedImages.length >= 5) {
                captureBtn.disabled = true;
            }
            saveUserBtn.disabled = capturedImages.length === 0 || !usernameInput.value;
        } else {
            console.error('Failed to capture image');
            alert('Failed to capture image. Please try again.');
        }
    }, 'image/jpeg', 0.9);
};

function updateCapturedImages() {
    capturedImagesContainer.innerHTML = ''; // Limpia el contenedor

    capturedImages.forEach((blob, index) => {
        // Crea un div para contener cada imagen
        const imageDiv = document.createElement('div');
        imageDiv.className = 'captured-image';

        // Crea un elemento <img> para mostrar la imagen capturada
        const imgElement = document.createElement('img');
        imgElement.alt = `Image ${index + 1}`;
        // imgElement.style.width = '100px'; // Ajusta el tamaño según tus necesidades
        // imgElement.style.height = 'auto';

        // Convierte el blob en una URL de objeto para mostrar la imagen
        const blobURL = URL.createObjectURL(blob);
        imgElement.src = blobURL;

        // Añade la imagen al div
        imageDiv.appendChild(imgElement);

        // Añade el div al contenedor
        capturedImagesContainer.appendChild(imageDiv);
    });
}




// cancelBtn.onclick = () => {
//     if (confirm('Are you sure you want to cancel? All captured images will be discarded.')) {
//         addUserDialog.style.display = 'none';
//         resetForm();
//     }
// };



async function uploadUserImages(username, imageFiles) {

    // Ocultar formulario y Mostrar loading...
    const dialog = document.getElementById('addUserDialog');
    const loadingOverlay = document.createElement('div');
    loadingOverlay.id = 'loadingOverlay';
    loadingOverlay.className = 'loading-overlay fixed inset-0 bg-gray-950 bg-opacity-50 flex items-center justify-center z-50 transition-opacity duration-500 opacity-100';
    loadingOverlay.innerHTML = `
        <div class="loading-spinner"></div>
        <p class="text-white-700 my-8">Añadiendo usuario...</p>
    `;
    dialog.appendChild(loadingOverlay);

    const formData = new FormData();
    
    imageFiles.forEach((file, index) => {
        formData.append('images', file, `image_${index + 1}.jpg`);
    });

    try {
        const response = await fetch(`http://127.0.0.1:8000/users?username=${encodeURIComponent(username)}`, {
            method: 'POST',
            headers: {
                'accept': 'application/json',
            },
            body: formData
        });

        if (!response.ok) {
            const errorDetail = await response.json();
            console.error('Error en la solicitud:', errorDetail);
            alert(`Error: ${errorDetail.detail || 'Ocurrió un problema al subir las imágenes.'}`);
            return;
        }

        const data = await response.json();
        console.log('Respuesta del servidor:', data);

        // Mostrar un mensaje de que el usuario ha sido añadido correctamente con botón para Cerrar popup
        dialog.innerHTML = `
            <div class="dialog rounded-lg shadow-lg p-6 w-full max-w-md text-center">
                <h2 class="text-green-600 font-bold text-xl">¡Usuario añadido exitosamente!</h2>
                <p class="text-white-700 my-6">El usuario <strong>${username}</strong> ha sido registrado.</p>
                <button id="closeSuccessBtn" class="btn btn-primary mt-4">Cerrar</button>
            </div>
        `;

        document.getElementById('closeSuccessBtn').onclick = () => {
            dialog.style.display = 'none';
            dialog.innerHTML = ''; // Limpia el contenido del diálogo
            fetchUsers()
        };

    } catch (error) {
        console.error('Error en la solicitud:', error);
        alert('Ocurrió un error al intentar subir las imágenes.');
    } finally {
        // TODO: Remover el overlay de loading una vez que finalice la operación
        if (document.getElementById('loadingOverlay')) {
            document.getElementById('loadingOverlay').remove();
        }
    }
}

// Save User
saveUserBtn.onclick = async () => {
    if (capturedImages.length === 0 || !usernameInput.value) {
        alert('Please capture at least one image and enter a username');
        return;
    }

    const formData = new FormData();
    formData.append('username', usernameInput.value.trim());
    capturedImages.forEach((image, index) => {
        formData.append('images', image, `image_${index}.jpg`);
    });

    // Verificar el contenido de FormData
    for (let [key, value] of formData.entries()) {
        console.log(`${key}:`, value);
    }


    try {

        const username = usernameInput.value.trim(); // Obtener el nombre de usuario
        const files = Array.from(capturedImages); // Convertir imágenes capturadas en un array
        await uploadUserImages(username, files);
       
        
    } catch (error) {
        console.error('Error adding user:', error);
        alert('Error adding user. Please check your connection and try again.');
    }
};

// Form validation
usernameInput.oninput = () => {
    const username = usernameInput.value.trim();
    saveUserBtn.disabled = capturedImages.length === 0 || !username;
    
    if (username.length > 0 && username.length < 3) {
        usernameInput.setCustomValidity('Username must be at least 3 characters long');
    } else {
        usernameInput.setCustomValidity('');
    }
};

// Analysis Type Controls
const analysisSelect = document.getElementById('analysisType');

analysisSelect.onchange = async () => {
    const selectedOption = analysisSelect.value;
    
    try {
        const response = await fetch('http://localhost:8000/set-analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ type: selectedOption })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Analysis type updated:', data);
    } catch (error) {
        console.error('Error updating analysis type:', error);
        alert('Error updating analysis type. Please try again.');
    }
};

// Cleanup
window.addEventListener('beforeunload', () => {
    stopStream();
});

// Initial setup
document.addEventListener('DOMContentLoaded', fetchUsers);

