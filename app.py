from flask import Flask, render_template, Response, jsonify
import mysql.connector
import threading, paho.mqtt.client as mqtt, json

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(host="localhost", user="root", password="", database="motion_face_detector_db")

@app.route("/")
def index():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, capture_time, event_type FROM detection ORDER BY capture_time DESC")
    data = cursor.fetchall()
    cursor.close(); db.close()
    return render_template("index.html", detection=data)

@app.route("/image/<int:image_id>")
def image(image_id):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT image FROM detection WHERE id=%s", (image_id,))
    row = cursor.fetchone()
    cursor.close(); db.close()
    if row and row[0]:
        return Response(row[0], mimetype="image/jpeg")
    return "Image not found", 404

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM detection WHERE id=%s", (id,))
    db.commit(); cursor.close(); db.close()
    return jsonify({"status":"success"})

# MQTT listener
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print(f"[ALERT] {data['event']} at {data['timestamp']}")
    except:
        print("[ALERT] Pesan:", msg.payload.decode())

def mqtt_listener():
    c = mqtt.Client()
    c.on_message = on_message
    c.connect("localhost", 1883, 60)
    c.subscribe("surveillance/events")
    c.loop_forever()

threading.Thread(target=mqtt_listener, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True)