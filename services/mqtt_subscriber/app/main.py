import json
import os
import random
import time
import threading
import requests
import paho.mqtt.client as mqtt

# ── Config ────────────────────────────────────────────────
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "sensors/temperature")

API_BASE    = os.getenv("API_BASE_URL", "http://api:8000")
API_KEY     = os.getenv("API_KEY", "dev-secret-key")

SIMULATE    = os.getenv("SIMULATE", "true").lower() == "true"
DEVICE_ID   = os.getenv("DEVICE_ID", "simulator-01")
INTERVAL    = int(os.getenv("SIMULATE_INTERVAL", "5"))


# ── Simulator thread ──────────────────────────────────────
def run_simulator(client: mqtt.Client):
    """Publishes random temperature to the broker every INTERVAL seconds.
    Runs in a background thread. Replace with real ESP32 when ready."""
    print("[simulator] starting — publishing every %ds" % INTERVAL)
    time.sleep(3)  # wait for broker connection to settle
    while True:
        payload = json.dumps({
            "device_id":   DEVICE_ID,
            "temperature": round(random.uniform(20.0, 35.0), 2),
        })
        client.publish(MQTT_TOPIC, payload)
        print(f"[simulator] published: {payload}")
        time.sleep(INTERVAL)


# ── MQTT callbacks ────────────────────────────────────────
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[subscriber] connected to broker {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"[subscriber] subscribed to {MQTT_TOPIC}")

        if SIMULATE:
            t = threading.Thread(target=run_simulator, args=(client,), daemon=True)
            t.start()
    else:
        print(f"[subscriber] connection failed — rc={rc}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        device_id   = data.get("device_id", DEVICE_ID)
        temperature = float(data["temperature"])
    except Exception as e:
        print(f"[subscriber] bad payload: {e}")
        return

    try:
        resp = requests.post(
            f"{API_BASE}/reading",
            json={"device_id": device_id, "temperature": temperature},
            headers={"x-api-key": API_KEY},
            timeout=5,
        )
        print(f"[subscriber] saved → {temperature}°C  HTTP {resp.status_code}")
    except Exception as e:
        print(f"[subscriber] api error: {e}")


# ── Main ──────────────────────────────────────────────────
def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[subscriber] connecting to {MQTT_BROKER}:{MQTT_PORT} ...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
