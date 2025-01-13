import cv2
import os
import argparse
from pathlib import Path
import face_recognition
import time
import sys

class DatasetManager:
    def __init__(self, dataset_path="dataset"):
        self.dataset_path = Path(dataset_path)
        self.dataset_path.mkdir(exist_ok=True)

    def create_user_directory(self, username):
        user_path = self.dataset_path / username
        if user_path.exists():
            raise ValueError(f"User {username} already exists in dataset")
        user_path.mkdir(parents=True)
        return user_path

    def capture_user_images(self, username, num_images=5):
        user_path = self.create_user_directory(username)
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            raise RuntimeError("Could not access webcam")

        images_captured = 0
        last_capture_time = time.time()
        capture_delay = 2  # Seconds between captures
        
        print(f"\nStarting capture for user {username}")
        print("Position yourself in front of the camera with different poses")
        print(f"Will capture {num_images} images with {capture_delay} seconds delay")
        print("Press 'q' to quit or 'c' to capture manually")

        while images_captured < num_images:
            ret, frame = cap.read()
            if not ret:
                break

            # Mirror the frame for better user experience
            frame_flip = cv2.flip(frame, 1)
            
            # Draw capture counter
            cv2.putText(frame_flip, f"Captures: {images_captured}/{num_images}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Detect faces
            face_locations = face_recognition.face_locations(frame)
            
            # Draw rectangles around detected faces
            for top, right, bottom, left in face_locations:
                cv2.rectangle(frame_flip, (left, top), (right, bottom), (0, 255, 0), 2)

            cv2.imshow('Capture', frame_flip)
            
            key = cv2.waitKey(1) & 0xFF
            current_time = time.time()
            
            # Auto capture if face detected and enough time has passed
            if (current_time - last_capture_time >= capture_delay and 
                len(face_locations) == 1):
                image_path = user_path / f"{username}_{images_captured+1}.jpg"
                cv2.imwrite(str(image_path), frame)
                print(f"Captured image {images_captured+1}/{num_images}")
                images_captured += 1
                last_capture_time = current_time
            
            # Manual capture with 'c' key
            elif key == ord('c'):
                if len(face_locations) == 1:
                    image_path = user_path / f"{username}_{images_captured+1}.jpg"
                    cv2.imwrite(str(image_path), frame)
                    print(f"Captured image {images_captured+1}/{num_images}")
                    images_captured += 1
                    last_capture_time = current_time
                else:
                    print("No face or multiple faces detected. Please adjust position.")
            
            # Quit with 'q' key
            elif key == ord('q'):
                print("\nCapture cancelled by user")
                break

        cap.release()
        cv2.destroyAllWindows()
        
        if images_captured == 0:
            # Clean up empty directory
            user_path.rmdir()
            return False
            
        return True

def main():
    parser = argparse.ArgumentParser(description='Capture user images for facial recognition dataset')
    parser.add_argument('username', type=str, help='Name of the user to add')
    parser.add_argument('--num-images', type=int, default=5, 
                        help='Number of images to capture (default: 5)')
    parser.add_argument('--dataset-path', type=str, default='dataset',
                        help='Path to dataset directory (default: dataset)')
    
    args = parser.parse_args()
    
    try:
        dataset_manager = DatasetManager(args.dataset_path)
        success = dataset_manager.capture_user_images(args.username, args.num_images)
        
        if success:
            print(f"\nSuccessfully added user {args.username} to dataset")
            print(f"Images saved in {dataset_manager.dataset_path / args.username}")
        else:
            print("\nFailed to capture any images. Please try again.")
            sys.exit(1)
            
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()