import cv2
import os

name = input("Masukkan nama orang yang ingin didaftarkan: ").strip()
if not name:
    print("Nama tidak boleh kosong.")
    exit()

folder = os.path.join("known_faces", name)
os.makedirs(folder, exist_ok=True)

camera = cv2.VideoCapture(0)
if not camera.isOpened():
    print("Tidak bisa membuka kamera.")
    exit()

print("[INFO] Mulai ambil gambar. Tekan 'q' untuk berhenti.")
count = 0

while True:
    ret, frame = camera.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (200, 200))
        count += 1
        file_path = os.path.join(folder, f"face_{count}.jpg")
        cv2.imwrite(file_path, face)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(frame, f"{count}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

    cv2.imshow("Pendaftaran Wajah", frame)
    if cv2.waitKey(1) & 0xFF == ord('q') or count >= 40:
        break

print(f"[INFO] {count} foto wajah '{name}' disimpan di {folder}")
camera.release()
cv2.destroyAllWindows()