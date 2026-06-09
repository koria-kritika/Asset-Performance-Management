from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import numpy as np
import sqlite3
import json
import os
from datetime import datetime
import shap
import requests as http_requests

app = FastAPI(title="Predictive Maintenance API")

MODEL_PATH = "models/rf_model.joblib"
SCALER_PATH = "models/scaler.joblib"
META_PATH   = "models/model_meta.json"

model     = joblib.load(MODEL_PATH)
scaler    = joblib.load(SCALER_PATH)
explainer = shap.TreeExplainer(model)

with open(META_PATH) as f:
    meta = json.load(f)

THRESHOLD     = meta["threshold"]
DB_PATH       = "maintenance.db"
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

# ── Database ──────────────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT,
            machine_id   TEXT,
            air_temp     REAL,
            process_temp REAL,
            rot_speed    REAL,
            torque       REAL,
            tool_wear    REAL,
            temp_diff    REAL,
            failure_prob REAL,
            status       TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

# ── Pydantic model ────────────────────────────────────────────────────────────
class SensorReading(BaseModel):
    machine_id:   str   = "MACHINE_01"
    air_temp:     float
    process_temp: float
    rot_speed:    float
    torque:       float
    tool_wear:    float

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_status(prob: float) -> str:
    if prob >= 0.80:
        return "CRITICAL"
    elif prob >= 0.50:
        return "WARNING"
    else:
        return "NORMAL"

# def get_status(prob: float) -> str:
#     if prob >= 0.50:
#         return "CRITICAL"
#     elif prob >= 0.30:
#         return "WARNING"
#     else:
#         return "NORMAL"

def send_slack_alert(reading: SensorReading, prob: float):
    if not SLACK_WEBHOOK:
        print("Slack webhook not set — skipping alert")
        return
    try:
        message = {
            "text": (
                f":rotating_light: *CRITICAL ALERT*\n"
                f"*Machine:* {reading.machine_id}\n"
                f"*Failure Probability:* {prob:.0%}\n"
                f"*Air Temp:* {reading.air_temp:.1f} K\n"
                f"*Torque:* {reading.torque:.1f} Nm\n"
                f"*Tool Wear:* {reading.tool_wear:.0f} min\n"
                f"*Time:* {datetime.utcnow().isoformat()}\n"
                f">Immediate inspection required."
            )
        }
        http_requests.post(SLACK_WEBHOOK, json=message, timeout=5)
        print(f"[ALERT] Slack message sent for {reading.machine_id}")
    except Exception as e:
        print(f"[ALERT] Slack failed: {e}")

# ── Routes ────────────────────────────────────────────────────────────────────
@app.post("/ingest")
def ingest_sensor(reading: SensorReading):
    temp_diff = reading.process_temp - reading.air_temp

    X = np.array([[
        reading.air_temp,
        reading.process_temp,
        reading.rot_speed,
        reading.torque,
        reading.tool_wear,
        temp_diff
    ]])

    X_scaled = scaler.transform(X)
    prob     = float(model.predict_proba(X_scaled)[0][1])
    status   = get_status(prob)

    if status == "CRITICAL":
        send_slack_alert(reading, prob)




    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO predictions
        (timestamp, machine_id, air_temp, process_temp, rot_speed,
         torque, tool_wear, temp_diff, failure_prob, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        reading.machine_id,
        reading.air_temp,
        reading.process_temp,
        reading.rot_speed,
        reading.torque,
        reading.tool_wear,
        temp_diff,
        round(prob, 4),
        status
    ))
    con.commit()
    con.close()

    return {
        "machine_id":   reading.machine_id,
        "failure_prob": round(prob, 4),
        "status":       status,
        "timestamp":    datetime.utcnow().isoformat()
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/logs")
def get_logs():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT * FROM predictions ORDER BY id DESC LIMIT 50"
    ).fetchall()
    con.close()

    cols = ["id", "timestamp", "machine_id", "air_temp", "process_temp",
            "rot_speed", "torque", "tool_wear", "temp_diff",
            "failure_prob", "status"]

    return [dict(zip(cols, row)) for row in rows]

@app.post("/explain")
def explain(reading: SensorReading):
    temp_diff = reading.process_temp - reading.air_temp

    X = np.array([[
        reading.air_temp,
        reading.process_temp,
        reading.rot_speed,
        reading.torque,
        reading.tool_wear,
        temp_diff
    ]])

    X_scaled  = scaler.transform(X)
    shap_vals = explainer.shap_values(X_scaled)

    if isinstance(shap_vals, list):
        failure_shap = shap_vals[1][0]
    else:
        failure_shap = shap_vals[0, :, 1]

    feature_names = [
        "Air Temp", "Process Temp",
        "Rot Speed", "Torque",
        "Tool Wear", "Temp Diff"
    ]

    explanation = {
        name: round(float(val), 4)
        for name, val in zip(feature_names, failure_shap)
    }

    return {
        "machine_id":     reading.machine_id,
        "shap_values":    explanation,
        "interpretation": "Positive = failure ki taraf, Negative = safe side"
    }

print("Database ready")
print("Model loaded successfully")
print(f"Threshold: {THRESHOLD}")