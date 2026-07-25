import cv2
import face_recognition
import numpy as np

print("Iniciando prueba de cámara...")
print("Presiona ESC para salir")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: No se pudo abrir la cámara")
    exit(1)

print(f"Resolución: {int(cap.get(3))}x{int(cap.get(4))}")
print("Cámara funcionando!")

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error al leer frame")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces_haar = face_cascade.detectMultiScale(gray, 1.1, 4)

    for (x, y, w, h) in faces_haar:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, "Rostro", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb)

    for (top, right, bottom, left) in face_locations:
        cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)
        cv2.putText(frame, "Face Rec", (left, bottom + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    head_roi = frame[0:int(frame.shape[0]*0.3), 0:frame.shape[1]]
    hsv = cv2.cvtColor(head_roi, cv2.COLOR_BGR2HSV)
    yellow_lower = np.array([20, 100, 100])
    yellow_upper = np.array([30, 255, 255])
    mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    yellow_pixels = np.sum(mask > 0)

    helmet_detected = yellow_pixels > 500
    color = (0, 255, 0) if helmet_detected else (0, 0, 255)
    text = f"CASCO: {'SI' if helmet_detected else 'NO'} ({yellow_pixels}px)"
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(frame, f"Rostros: {len(face_locations)}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.imshow("Webcam - IoT Security", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
print("Prueba finalizada")
