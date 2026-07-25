import cv2
import face_recognition
import numpy as np
import os

class SecurityService:
    def __init__(self):
        self.known_faces = {}
        self.helmet_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.camera = None

    def init_camera(self, camera_id=0):
        self.camera = cv2.VideoCapture(camera_id)
        return self.camera.isOpened()

    def register_face(self, name, image_path):
        image = face_recognition.load_image_file(image_path)
        encoding = face_recognition.face_encodings(image)
        if encoding:
            self.known_faces[name] = encoding[0]
            return True
        return False

    def recognize_face(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb)
        face_encodings = face_recognition.face_encodings(rgb, face_locations)

        for encoding in face_encodings:
            matches = face_recognition.compare_faces(
                list(self.known_faces.values()), encoding, tolerance=0.6
            )
            if True in matches:
                idx = matches.index(True)
                return list(self.known_faces.keys())[idx]
        return None

    def detect_helmet(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.helmet_cascade.detectMultiScale(gray, 1.1, 4)

        for (x, y, w, h) in faces:
            head_region = frame[y:y+h, x:x+w]
            avg_color = np.mean(head_region, axis=(0, 1))

            yellow_lower = np.array([20, 100, 100])
            yellow_upper = np.array([30, 255, 255])
            hsv = cv2.cvtColor(head_region, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
            yellow_pixels = np.sum(mask > 0)

            if yellow_pixels > 500:
                return True
            return False

        return None

    def release_camera(self):
        if self.camera:
            self.camera.release()