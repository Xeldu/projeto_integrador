import os
import requests
import pandas as pd
from datetime import date

API_BASE = os.getenv("API_BASE_URL", "http://api:8000")
API_KEY  = os.getenv("API_KEY", "dev-secret-key")
HEADERS  = {"x-api-key": API_KEY}
N_CHANNELS = 7
DEVICE_ID  = os.getenv("DEVICE_ID", "simulator-01")


def is_api_alive() -> bool:
    try:
        return requests.get(f"{API_BASE}/health", timeout=3).status_code == 200
    except Exception:
        return False


def get_live_channels() -> dict[int, float]:
    """Returns latest reading value for each channel from MQTT subscriber data."""
    result = {}
    for ch in range(1, N_CHANNELS + 1):
        device_id = f"{DEVICE_ID}-ch{ch}"
        try:
            r = requests.get(f"{API_BASE}/readings",
                             params={"device_id": device_id, "limit": 1}, timeout=3)
            r.raise_for_status()
            data = r.json()
            if data:
                result[ch] = float(data[0]["temperature"])
        except Exception:
            pass
    return result


def get_live_history(n_points: int = 60) -> pd.DataFrame:
    """Returns last n_points readings for each channel as a DataFrame."""
    frames = []
    for ch in range(1, N_CHANNELS + 1):
        device_id = f"{DEVICE_ID}-ch{ch}"
        try:
            r = requests.get(f"{API_BASE}/readings",
                             params={"device_id": device_id, "limit": n_points}, timeout=3)
            r.raise_for_status()
            rows = r.json()
            if rows:
                df = pd.DataFrame(rows)
                df["channel"] = ch
                df["value"]   = df["temperature"].astype(float)
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                frames.append(df[["timestamp", "channel", "value"]])
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).sort_values("timestamp")


def get_recent(device_id=None, limit=200) -> pd.DataFrame:
    try:
        r = requests.get(f"{API_BASE}/readings",
                         params={"limit": limit,
                                 **({"device_id": device_id} if device_id else {})},
                         timeout=5)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        if not df.empty:
            df["timestamp"]   = pd.to_datetime(df["timestamp"], utc=True)
            df["temperature"] = df["temperature"].astype(float)
            df.sort_values("timestamp", inplace=True)
        return df
    except Exception:
        return pd.DataFrame()


def get_stats(device_id=None) -> dict:
    try:
        r = requests.get(f"{API_BASE}/readings/stats",
                         params={**({"device_id": device_id} if device_id else {})},
                         timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def get_csv(day: str, device_id=None) -> bytes | None:
    try:
        r = requests.get(f"{API_BASE}/export/csv",
                         params={"day": day,
                                 **({"device_id": device_id} if device_id else {})},
                         timeout=15)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


def get_machines() -> list[dict]:
    try:
        r = requests.get(f"{API_BASE}/machines", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def create_machine(data: dict) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}/machines", json=data, headers=HEADERS, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def update_machine(machine_id: int, data: dict) -> dict | None:
    try:
        r = requests.put(f"{API_BASE}/machines/{machine_id}", json=data,
                         headers=HEADERS, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def delete_machine(machine_id: int) -> bool:
    try:
        r = requests.delete(f"{API_BASE}/machines/{machine_id}",
                            headers=HEADERS, timeout=5)
        return r.status_code == 204
    except Exception:
        return False


def start_test(machine_id: int, type: str, reference_channel: int) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}/tests",
                          json={"machine_id": machine_id, "type": type,
                                "reference_channel": reference_channel},
                          headers=HEADERS, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def add_test_readings(test_id: int, readings: list[dict]) -> bool:
    try:
        r = requests.post(f"{API_BASE}/tests/{test_id}/readings",
                          json=readings, headers=HEADERS, timeout=5)
        return r.status_code == 201
    except Exception:
        return False


def finish_test(test_id: int) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}/tests/{test_id}/finish",
                          headers=HEADERS, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_test(test_id: int) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/tests/{test_id}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_tests(type=None, status=None, date_from=None, date_to=None) -> list[dict]:
    params = {}
    if type:      params["type"]      = type
    if status:    params["status"]    = status
    if date_from: params["date_from"] = str(date_from)
    if date_to:   params["date_to"]   = str(date_to)
    try:
        r = requests.get(f"{API_BASE}/tests", params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def get_tests_today(type=None) -> list[dict]:
    try:
        params = {"type": type} if type else {}
        r = requests.get(f"{API_BASE}/tests/today", params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []
