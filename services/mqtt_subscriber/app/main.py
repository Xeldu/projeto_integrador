import json
import os
import random
import time
import threading
import requests
import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "sensors/temperature")

API_BASE    = os.getenv("API_BASE_URL", "http://api:8000")
API_KEY     = os.getenv("API_KEY", "dev-secret-key")

SIMULATE    = os.getenv("SIMULATE", "true").lower() == "true"
DEVICE_ID   = os.getenv("DEVICE_ID", "simulator-01")
INTERVAL    = int(os.getenv("SIMULATE_INTERVAL", "10"))
N_CHANNELS  = 7

# Persistent base temperatures per channel so they drift realistically
_base = {i + 1: round(random.uniform(22.0, 26.0), 2) for i in range(N_CHANNELS)}


def run_simulator(client: mqtt.Client):
    """Publishes all 7 channel readings every INTERVAL seconds.
    Payload: {"device_id": "...", "channels": {"1": 25.3, "2": 26.1, ...}}
    """
    print(f"[simulator] starting — publishing every {INTERVAL}s")
    time.sleep(3)
    step = 0
    while True:
        step += 1
        channels = {}
        for ch in range(1, N_CHANNELS + 1):
            # Simulate gradual heating that levels off
            _base[ch] = round(_base[ch] + random.uniform(-0.1, 0.8) * max(0, 1 - step / 60), 2)
            channels[str(ch)] = _base[ch]

        payload = json.dumps({"device_id": DEVICE_ID, "channels": channels})
        client.publish(MQTT_TOPIC, payload)
        print(f"[simulator] published step {step}: {channels}")
        time.sleep(INTERVAL)


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[subscriber] connected to {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"[subscriber] subscribed to {MQTT_TOPIC}")
        if SIMULATE:
            threading.Thread(target=run_simulator, args=(client,), daemon=True).start()
    else:
        print(f"[subscriber] connection failed rc={rc}")


def on_message(client, userdata, msg):
    """Receives multi-channel payload and stores the latest values
    in the live readings endpoint (one record per channel)."""
    try:
        data     = json.loads(msg.payload.decode())
        channels = data.get("channels", {})
        device_id = data.get("device_id", DEVICE_ID)
    except Exception as e:
        print(f"[subscriber] bad payload: {e}")
        return

    for ch_str, value in channels.items():
        try:
            resp = requests.post(
                f"{API_BASE}/reading",
                json={"device_id": f"{device_id}-ch{ch_str}", "temperature": float(value)},
                headers={"x-api-key": API_KEY},
                timeout=5,
            )
            if resp.status_code not in (200, 201):
                print(f"[subscriber] ch{ch_str} HTTP {resp.status_code}")
        except Exception as e:
            print(f"[subscriber] api error ch{ch_str}: {e}")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    print(f"[subscriber] connecting to {MQTT_BROKER}:{MQTT_PORT} ...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
