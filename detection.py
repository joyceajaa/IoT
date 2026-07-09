import cv2, imutils, time, mysql.connector, os, numpy as np, paho.mqtt.client as mqtt, json
from plyer import notification
import pygame

#Setup database
db = mysql.connector.connect(host="localhost", user="root", password="", database="motion_face_detector_db")
cursor = db.cursor()

#Setup MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "surveillance/events"
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

#load wajah yang dikenali
known_faces, labels = [], []
label_to_name = {}
base_path = "known_faces"
if os.path.exists(base_path):
    label_id = 0
    for person in os.listdir(base_path):
        person_folder = os.path.join(base_path, person)
        if not os.path.isdir(person_folder): continue
        for img_file in os.listdir(person_folder):
            if img_file.lower().endswith((".jpg", ".png")):
                img = cv2.imread(os.path.join(person_folder, img_file), cv2.IMREAD_GRAYSCALE)
                img = cv2.resize(img, (200, 200))
                known_faces.append(img)
                labels.append(label_id)
        label_to_name[label_id] = person
        label_id += 1

recognizer = None
if len(known_faces) > 0:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(known_faces, np.array(labels))
    print(f"[INFO] {len(label_to_name)} wajah dikenal dimuat.")
else:
    print("[WARN] Tidak ada wajah dikenal ditemukan di folder known_faces.")

#alert dan database
def play_alert():
    try:
        pygame.mixer.init()
        pygame.mixer.music.load("alert.mp3")
        pygame.mixer.music.play()
    except:
        print("[WARN] Gagal memutar suara alert.")

def insert_image_to_db(event_type, frame):
    _, buffer = cv2.imencode(".jpg", frame)
    binary_data = buffer.tobytes()
    cursor.execute("INSERT INTO detection (capture_time, event_type, image) VALUES (NOW(), %s, %s)", (event_type, binary_data))
    db.commit()
    payload = json.dumps({"event": event_type, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
    client.publish(MQTT_TOPIC, payload)
    print(f"[INFO] {event_type} dikirim ke MQTT & disimpan ke DB.")

#Setup kamera
camera = cv2.VideoCapture(0)
if not camera.isOpened():
    raise Exception("Kamera tidak bisa dibuka.")
print("[INFO] Kamera aktif. Tekan 'Q' untuk keluar.")

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
first_frame, motion_counter, last_capture_time, last_alert_time = None, 0, 0, 0
capture_interval, alert_interval = 3, 10

while True:
    ret, frame = camera.read()
    if not ret:
        continue

    frame = imutils.resize(frame, width=700)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_blur = cv2.GaussianBlur(gray, (31, 31), 0)
    gray_blur = cv2.equalizeHist(gray_blur)

    if first_frame is None:
        first_frame = gray_blur
        continue

    # Deteksi gerak
    frame_delta = cv2.absdiff(first_frame, gray_blur)
    thresh = cv2.threshold(frame_delta, 30, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    first_frame = cv2.addWeighted(first_frame, 0.9, gray_blur, 0.1, 0)
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    motion_boxes = [(x, y, w, h) for c in contours if cv2.contourArea(c) >= 2500 for (x, y, w, h) in [cv2.boundingRect(c)]]

    motion_detected, face_detected, unknown_detected, recognized_name = False, False, False, None
    if motion_boxes:
        motion_counter += 1
        if motion_counter >= 3:
            motion_detected = True
            x_min, y_min = min(x for x, y, w, h in motion_boxes), min(y for x, y, w, h in motion_boxes)
            x_max, y_max = max(x + w for x, y, w, h in motion_boxes), max(y + h for x, y, w, h in motion_boxes)
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.putText(frame, "Gerakan Terdeteksi", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    else:
        motion_counter = 0

    # Deteksi wajah
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
    for (x, y, w, h) in faces:
        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (200, 200))
        if recognizer is not None:
            label, confidence = recognizer.predict(face)
            if confidence < 70:
                recognized_name = label_to_name[label]
                face_detected = True
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
                cv2.putText(frame, recognized_name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            else:
                unknown_detected = True
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0,0,255), 2)
                cv2.putText(frame, "Wajah Asing", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
        else:
            unknown_detected = True

    event_type = "motion" if motion_detected else None
    if recognized_name:
        event_type = f"face ({recognized_name})"
    elif unknown_detected:
        event_type = "unknown face"

    current_time = time.time()
    if event_type and (current_time - last_capture_time >= capture_interval):
        insert_image_to_db(event_type, frame)
        last_capture_time = current_time

    if unknown_detected and (current_time - last_alert_time >= alert_interval):
        notification.notify(title="Wajah Asing Terdeteksi!", message="Ada seseorang yang tidak dikenal!", timeout=3)
        play_alert()
        last_alert_time = current_time

    cv2.imshow("Deteksi Wajah & Gerakan", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
cursor.close()
db.close()
client.loop_stop()