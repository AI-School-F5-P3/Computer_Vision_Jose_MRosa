import cv2
import face_recognition
import numpy as np
import time
import threading

class FaceProcessor:
    def __init__(self):
        self.last_processed_time = 0
        self.processing_interval = 0.2  # Process every 200ms
        self.last_results = []
        self.processing = False
        self.frame_skip = 2  # Process every nth frame
        self.frame_count = 0
        self.processing_lock = threading.Lock()

    def should_process_frame(self):
        current_time = time.time()
        self.frame_count += 1
        
        if self.processing:
            return False
            
        if (current_time - self.last_processed_time) < self.processing_interval:
            return False
            
        if self.frame_count % self.frame_skip != 0:
            return False
            
        return True

    def process_frame(self, frame, known_face_encodings, known_face_names):
        if not self.should_process_frame():
            return self.last_results

        with self.processing_lock:
            if self.processing:
                return self.last_results
            self.processing = True

        try:
            # Resize frame for faster processing
            frame_height, frame_width = frame.shape[:2]
            scale = 1.0
            if frame_width > 640:
                scale = 640 / frame_width
                frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame, model="hog", number_of_times_to_upsample=1)
            
            if not face_locations:
                self.last_results = []
                return []

            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=1)
            
            results = []
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                if len(known_face_encodings) > 0:
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    
                    if face_distances[best_match_index] < 0.6:
                        name = known_face_names[best_match_index]
                        access_status = "AUTHORIZED"
                    else:
                        name = "Unknown"
                        access_status = "DENIED"
                else:
                    name = "Unknown"
                    access_status = "DENIED"

                if scale != 1.0:
                    top = int(top / scale)
                    right = int(right / scale)
                    bottom = int(bottom / scale)
                    left = int(left / scale)

                results.append({
                    "location": (top, right, bottom, left),
                    "name": name,
                    "status": access_status
                })

            self.last_results = results
            self.last_processed_time = time.time()
            return results

        finally:
            self.processing = False

