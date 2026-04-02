import os
import requests
import pandas as pd
from datetime import date

API_BASE = os.getenv("API_BASE_URL", "http://api:8000")


def get_recent(device_id: str | None = None, limit: int = 200) -> pd.DataFrame:
    params = {"limit": limit}
    if device_id:
        params["device_id"] = device_id
    try:
        r = requests.get(f"{API_BASE}/readings", params=params, timeout=5)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df["temperature"] = df["temperature"].astype(float)
            df.sort_values("timestamp", inplace=True)
        return df
    except Exception:
        return pd.DataFrame()


def get_stats(device_id: str | None = None) -> dict:
    params = {}
    if device_id:
        params["device_id"] = device_id
    try:
        r = requests.get(f"{API_BASE}/readings/stats", params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def get_csv(day: str, device_id: str | None = None) -> bytes | None:
    params = {"day": day}
    if device_id:
        params["device_id"] = device_id
    try:
        r = requests.get(f"{API_BASE}/export/csv", params=params, timeout=15)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


def reset_readings() -> bool:
    api_key = os.getenv("API_KEY", "dev-secret-key")
    try:
        r = requests.delete(f"{API_BASE}/readings", headers={"x-api-key": api_key}, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def is_api_alive() -> bool:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
