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
let animationFrameId = null;
let reconnectTimeout = null;

// DOM Elements
const video = document.getElementById('video');
const overlay = document.getElementById('overlay');
const toggleBtn = document.getElementById('toggleCamera');
const addUserBtn = document.getElementById('addUserBtn');
const addUserDialog = document.getElementById('addUserDialog');
const usernameInput = document.getElementById('username');
const captureBtn = document.getElementById('captureBtn');
const saveUserBtn = document.getElementById('saveUserBtn');
const cancelBtn = document.getElementById('cancelBtn');
const userList = document.getElementById('userList');
const capturedImagesContainer = document.getElementById('capturedImages');

// Set initial canvas size
overlay.width = 640;
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
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user',
                frameRate: { ideal: 15 } // Limit frame rate for better performance
            }
        });
        
        video.srcObject = stream;
        
        // Wait for video to be ready
        await new Promise((resolve) => {
            video.onloadedmetadata = () => resolve();
        });
        
        await video.play();
        
        // Set canvas size to match video
        const videoTrack = stream.getVideoTracks()[0];
        const settings = videoTrack.getSettings();
        
        overlay.width = settings.width || 640;
        overlay.height = settings.height || 480;
        
        isStreaming = true;
        toggleBtn.textContent = 'Stop Camera';
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
    captureBtn.disabled = true;
    
    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    lastReceivedResults = [];
}

// Improved frame sending with rate limiting and error handling
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
        
        // Optimize drawing
        ctx.drawImage(video, 0, 0);
        const base64Frame = canvas.toDataURL('image/jpeg', 0.6); // Reduced quality for better performance
        
        if (ws.bufferedAmount === 0) { // Only send if previous frame was processed
            ws.send(base64Frame);
            lastFrameTime = currentTime;
        }
    } catch (error) {
        console.error('Error sending frame:', error);
    }

    animationFrameId = requestAnimationFrame(sendFrame);
}

// Improved message handling with smoothing
function handleWsMessage(event) {
    try {
        const data = JSON.parse(event.data);
        if (data.results) {
            // Smooth transition between results
            lastReceivedResults = data.results;
            drawResults(data.results);
        }
    } catch (error) {
        console.error('Error processing WebSocket message:', error);
    }
}

// Improved drawing function with double buffering
function drawResults(results) {
    // Create an off-screen canvas for double buffering
    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = overlay.width;
    offscreenCanvas.height = overlay.height;
    const offscreenCtx = offscreenCanvas.getContext('2d', { alpha: true });
    
    // Clear the off-screen canvas
    offscreenCtx.clearRect(0, 0, overlay.width, overlay.height);
    
    if (!results || results.length === 0) {
        // Copy the off-screen canvas to the visible canvas
        const ctx = overlay.getContext('2d');
        ctx.clearRect(0, 0, overlay.width, overlay.height);
        return;
    }

    const scaleX = overlay.width / video.videoWidth;
    const scaleY = overlay.height / video.videoHeight;

    results.forEach(result => {
        if (!result.location || result.location.length !== 4) {
            return;
        }

        const [top, right, bottom, left] = result.location;
        const color = result.status === 'AUTHORIZED' ? '#22c55e' : '#ef4444';

        const scaledLeft = left * scaleX;
        const scaledTop = top * scaleY;
        const scaledWidth = (right - left) * scaleX;
        const scaledHeight = (bottom - top) * scaleY;

        // Draw to off-screen canvas
        offscreenCtx.strokeStyle = color;
        offscreenCtx.lineWidth = 2;
        offscreenCtx.strokeRect(scaledLeft, scaledTop, scaledWidth, scaledHeight);

        // Draw labels with improved visibility
        offscreenCtx.font = 'bold 16px Arial';
        
        // Name label with improved background
        const nameText = result.name;
        const nameWidth = offscreenCtx.measureText(nameText).width;
        const nameHeight = 24;
        const namePadding = 8;
        
        offscreenCtx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        offscreenCtx.fillRect(
            scaledLeft,
            Math.max(0, scaledTop - nameHeight - namePadding),
            nameWidth + (namePadding * 2),
            nameHeight
        );
        
        offscreenCtx.fillStyle = color;
        offscreenCtx.fillText(
            nameText,
            scaledLeft + namePadding,
            Math.max(nameHeight - 4, scaledTop - namePadding)
        );

        // Status label with improved visibility
        const statusText = result.status;
        const statusWidth = offscreenCtx.measureText(statusText).width;
        const statusHeight = 24;
        const statusPadding = 8;
        
        offscreenCtx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        offscreenCtx.fillRect(
            scaledLeft,
            scaledTop + scaledHeight + namePadding,
            statusWidth + (statusPadding * 2),
            statusHeight
        );
        
        offscreenCtx.fillStyle = color;
        offscreenCtx.fillText(
            statusText,
            scaledLeft + statusPadding,
            scaledTop + scaledHeight + statusHeight
        );
    });

    // Copy the off-screen canvas to the visible canvas with transparency
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
        `<div class="user-item">${user}</div>`
    ).join('');
}

// Image Capture with improved quality
captureBtn.onclick = () => {
    if (!isStreaming) return;
    
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d', { alpha: false });
    
    // Ensure smooth image capture
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
    capturedImagesContainer.innerHTML = capturedImages.map((_, index) => 
        `<div class="captured-image">Image ${index + 1}</div>`
    ).join('');
}

// Dialog Controls with improved validation
addUserBtn.onclick = () => {
    if (!isStreaming) {
        alert('Please start the camera first');
        return;
    }
    addUserDialog.style.display = 'flex';
};

cancelBtn.onclick = () => {
    if (confirm('Are you sure you want to cancel? All captured images will be discarded.')) {
        addUserDialog.style.display = 'none';
        resetForm();
    }
};

function resetForm() {
    usernameInput.value = '';
    capturedImages.length = 0;
    updateCapturedImages();
    saveUserBtn.disabled = true;
    captureBtn.disabled = !isStreaming;
}

// Save User with improved error handling
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

    try {
        const response = await fetch('http://localhost:8000/users', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (response.ok) {
            alert('User added successfully!');
            addUserDialog.style.display = 'none';
            resetForm();
            await fetchUsers();
        } else {
            alert(`Error adding user: ${data.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error adding user:', error);
        alert('Error adding user. Please check your connection and try again.');
    }
};

// Form validation with improved feedback
usernameInput.oninput = () => {
    const username = usernameInput.value.trim();
    saveUserBtn.disabled = capturedImages.length === 0 || !username;
    
    if (username.length > 0 && username.length < 3) {
        usernameInput.setCustomValidity('Username must be at least 3 characters long');
    } else {
        usernameInput.setCustomValidity('');
    }
};

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopStream();
});

// Initial setup
document.addEventListener('DOMContentLoaded', fetchUsers);