import pandas as pd
import requests
import time
import random

API_URL = "http://127.0.0.1:8000/ingest"
DATA_PATH = "data/ai4i2020.csv"
INTERVAL = 2

def add_noise(value):
    return value * (1 + random.uniform(-0.01, 0.01))

def stream():
    df = pd.read_csv(DATA_PATH)
    print(f"Dataset loaded — {len(df)} rows")
    print(f"Sending data every {INTERVAL} seconds...\n")

    for i, row in df.iterrows():
        payload = {
            "machine_id": "MACHINE_01",
            "air_temp":     add_noise(row["Air temperature [K]"]),
            "process_temp": add_noise(row["Process temperature [K]"]),
            "rot_speed":    add_noise(row["Rotational speed [rpm]"]),
            "torque":       add_noise(row["Torque [Nm]"]),
            "tool_wear":    add_noise(row["Tool wear [min]"])
        }

        try:
            response = requests.post(API_URL, json=payload, timeout=5)
            data = response.json()

            print(
                f"Row {i+1:05d} | "
                f"Status: {data['status']:8s} | "
                f"Prob: {data['failure_prob']:.3f} | "
                f"Temp: {payload['air_temp']:.1f}K | "
                f"Torque: {payload['torque']:.1f}Nm"
            )

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(INTERVAL)

stream()