import asyncio
import random
import httpx
import os

API_KEY = os.getenv("API_KEY", "dev-secret-key")
DEVICE_ID = "simulator-01"
INTERVAL = 5  # seconds between readings


async def simulate_readings():
    """Sends a random temperature reading to the API every INTERVAL seconds.
    This runs inside the API container itself, replacing the physical ESP32."""
    await asyncio.sleep(3)  # let the server finish starting up
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        while True:
            temperature = round(random.uniform(20.0, 35.0), 2)
            try:
                await client.post(
                    "/reading",
                    json={"device_id": DEVICE_ID, "temperature": temperature},
                    headers={"x-api-key": API_KEY},
                    timeout=5,
                )
            except Exception as e:
                print(f"[simulator] error: {e}")
            await asyncio.sleep(INTERVAL)
