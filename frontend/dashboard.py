import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import time
import requests

matplotlib.use("Agg")


RENDER_URL = "https://asset-performance-management.onrender.com" 
LOCAL_URL = "http://127.0.0.1:8000"

try:
    requests.get(LOCAL_URL, timeout=1)
    API_BASE = LOCAL_URL
except requests.exceptions.RequestException:
    API_BASE = RENDER_URL

st.set_page_config(
    page_title="Asset Performance Management",
    page_icon="⚙",
    layout="wide"
)


if "study_row" not in st.session_state:
    st.session_state.study_row = None


@st.cache_data(ttl=3)
def fetch_logs():
    try:
        r = requests.get(f"{API_BASE}/logs", timeout=3)
        df = pd.DataFrame(r.json())
        if not df.empty:
            df["failure_prob"] = pd.to_numeric(df["failure_prob"], errors="coerce")
            df["air_temp"]     = pd.to_numeric(df["air_temp"],     errors="coerce")
            df["torque"]       = pd.to_numeric(df["torque"],       errors="coerce")
            df["tool_wear"]    = pd.to_numeric(df["tool_wear"],    errors="coerce")
            df["timestamp"]    = pd.to_datetime(df["timestamp"])
        return df
    except:
        return pd.DataFrame()

def fetch_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=2)
        return r.json()
    except:
        return {"status": "offline"}


st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght=300;400;500;700&display=swap');

    /* Font Family & Uniform Light Brown Background */
    html, body, [class*="st-"], .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Roboto', sans-serif !important;
        background-color: #FAF6ED !important;
    }

    /* Professional Headers */
    h1 {
        font-weight: 700 !important;
        color: #030303 !important;
        letter-spacing: -0.5px;
    }
    
    h2, h3 {
        font-weight: 500 !important;
        color: #030303 !important;
    }

    /* Responsive Metrics */
    [data-testid="stMetricValue"] {
        font-size: calc(20px + 0.8vw) !important;
        font-weight: 500 !important;
        color: #065fd4 !important;
    }

    /* Clean Tabs */
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        font-weight: 500;
        font-size: 16px;
        color: #606060;
    }
    .stTabs [aria-selected="true"] {
        color: #065fd4 !important;
        border-bottom-color: #065fd4 !important;
    }

    /* Custom Responsive Rows for Audit Log */
    .log-row-container {
        display: flex;
        flex-wrap: wrap;
        padding: 12px;
        margin-bottom: 6px;
        border-radius: 6px;
        align-items: center;
    }
    .log-critical { background-color: #FFEBEE; border-left: 5px solid #EF5350; color: #B71C1C; }
    .log-warning  { background-color: #FFFDE7; border-left: 5px solid #FFEE58; color: #F57F17; }
    .log-normal   { background-color: #E8F5E9; border-left: 5px solid #66BB6A; color: #1B5E20; }

    /* Custom Banner for Status Alerts */
    .status-banner {
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 25px;
        font-weight: 500;
        font-size: 20px;
    }
    .critical-banner { background-color: #FFEBEE; color: #B71C1C; border: 1px solid #EF5350; }
    .warning-banner { background-color: #FFFDE7; color: #F57F17; border: 1px solid #FFEE58; }
    .normal-banner { background-color: #E8F5E9; color: #1B5E20; border: 1px solid #66BB6A; }

    /* Pill-shaped UI Buttons */
    .stButton>button {
        border-radius: 20px !important;
        font-weight: 500 !important;
        background-color: #e0dbcd !important;
        border: none !important;
        color: #030303 !important;
        transition: background 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #d1cbbd !important;
        color: #030303 !important;
    }

    @media (max-width: 768px) {
        [data-testid="stMetricValue"] {
            font-size: 18px !important;
        }
        .status-banner {
            font-size: 16px;
        }
    }
    </style>
    """, unsafe_allow_html=True)


st.title("Asset Performance Dashboard")
st.caption("Live Operations & Asset Health")

health = fetch_health()
if health.get("status") != "ok":
    st.error("API server offline — run: uvicorn backend.main:app --reload")
    st.stop()

df = fetch_logs()
if df.empty:
    st.info("Waiting for data — run: python simulator/sensor_stream.py")
    st.stop()

latest    = df.iloc[0]
status    = latest["status"]
df_sorted = df.sort_values("timestamp")


if status == "CRITICAL":
    st.markdown(f"""
    <div class="status-banner critical-banner">
         CRITICAL ALERT — Machine {latest['machine_id']}<br>
        <span style="font-size: 16px; font-weight: normal;">
        Failure Probability: {float(latest['failure_prob']):.0%} — Immediate Inspection Required!
        </span>
    </div>
    <script>
        var audio = new Audio("https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3");
        audio.play();
    </script>
    """, unsafe_allow_html=True)

elif status == "WARNING":
    st.markdown(f"""
    <div class="status-banner warning-banner">
        WARNING — Machine {latest['machine_id']} | Probability: {float(latest['failure_prob']):.0%}
    </div>
    """, unsafe_allow_html=True)

else:
    st.markdown(f"""
    <div class="status-banner normal-banner">
        NORMAL — All machines operating safely
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Live Monitor", "Diagnostic Insights"])

with tab1:
    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Latest Probability", f"{float(latest['failure_prob']):.1%}")
    col2.metric("Air Temp",           f"{float(latest['air_temp']):.1f} K")
    col3.metric("Torque",             f"{float(latest['torque']):.1f} Nm")
    col4.metric("Tool Wear",          f"{float(latest['tool_wear']):.0f} min")

    st.subheader("Failure Probability Over Time")
    st.line_chart(df_sorted.set_index("timestamp")["failure_prob"])

    st.divider()

    col5, col6 = st.columns(2)
    with col5:
        st.subheader("Air Temperature (K)")
        st.line_chart(df_sorted.set_index("timestamp")["air_temp"])
    with col6:
        st.subheader("Torque (Nm)")
        st.line_chart(df_sorted.set_index("timestamp")["torque"])

    st.divider()

   
    study_panel_container = st.container()

    
    st.subheader("Audit Log")

    h1, h2, h3, h4, h5, h6 = st.columns([1, 2.5, 2, 1, 1, 1])
    h1.markdown("**ID**")
    h2.markdown("**Timestamp**")
    h3.markdown("**Machine**")
    h4.markdown("**Prob**")
    h5.markdown("**Status**")
    h6.markdown("**Action**")

    st.divider()

    for i, row in df.iterrows():
        row_status = row["status"]
        log_class = {
            "CRITICAL": "log-row-container log-critical",
            "WARNING": "log-row-container log-warning",
            "NORMAL": "log-row-container log-normal"
        }.get(row_status, "log-row-container")

        rid = int(row["id"])
        prob = float(row["failure_prob"])
        time_str = str(row["timestamp"])[:19]

        with st.container():
            col_id, col_t, col_m, col_p, col_s, col_btn = st.columns([1, 2.5, 2, 1, 1, 1])
            
            if rid == int(latest["id"]):
                col_id.markdown(f'<div class="{log_class}"><b>#{rid} *</b></div>', unsafe_allow_html=True)
            else:
                col_id.markdown(f'<div class="{log_class}">#{rid}</div>', unsafe_allow_html=True)
                
            col_t.markdown(f'<div class="{log_class}">{time_str}</div>', unsafe_allow_html=True)
            col_m.markdown(f'<div class="{log_class}">{row["machine_id"]}</div>', unsafe_allow_html=True)
            col_p.markdown(f'<div class="{log_class}"><b>{prob:.0%}</b></div>', unsafe_allow_html=True)
            col_s.markdown(f'<div class="{log_class}">{row_status}</div>', unsafe_allow_html=True)
            
            with col_btn:
                if st.button("Analyse", key=f"study_{rid}", use_container_width=True):
                    st.session_state.study_row = row.to_dict()
                    st.rerun()

    
    if st.session_state.study_row is not None:
        with study_panel_container:
            r = st.session_state.study_row
            st.write("---")
            st.subheader(f"Diagnostic Window — {r['machine_id']} (Row #{int(r['id'])})")

            payload = {
                "machine_id":   str(r["machine_id"]),
                "air_temp":     float(r["air_temp"]),
                "process_temp": float(r["process_temp"]),
                "rot_speed":    float(r["rot_speed"]),
                "torque":       float(r["torque"]),
                "tool_wear":    float(r["tool_wear"]),
            }

            try:
                with st.spinner("Calculating values..."):
                    res = requests.post(f"{API_BASE}/explain", json=payload, timeout=15)
                    shap_data = res.json()["shap_values"]

                features = list(shap_data.keys())
                values   = list(shap_data.values())
                colors   = ["#e74c3c" if v > 0 else "#2ecc71" for v in values]

                fig, ax = plt.subplots(figsize=(9, 4))
                fig.patch.set_facecolor("#FAF6ED")
                ax.set_facecolor("#FAF6ED")
                ax.barh(features, values, color=colors, height=0.5)

                for bar, val in zip(ax.patches, values):
                    ax.text(val + (0.002 if val >= 0 else -0.002), bar.get_y() + bar.get_height() / 2, f"{val:+.4f}", va="center", ha="left" if val >= 0 else "right", fontsize=9, color="#030303")

                ax.axvline(0, color="#030303", linewidth=1.0, alpha=0.6)
                st.pyplot(fig)
                plt.close()

                with st.expander("Raw SHAP values Breakdown", expanded=True):
                    shap_df = pd.DataFrame({"Feature": features, "SHAP Value": values}).sort_values("SHAP Value", ascending=False)
                    st.dataframe(shap_df, use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Error loading diagnostics: {e}")
                
            st.write("---")

    st.divider()
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False),
        file_name="maintenance_logs.csv",
        mime="text/csv"
    )


with tab2:
    st.subheader("Risk Factor Identification")
    st.caption("Attribution analysis of real-time telemetry driving the risk index.")

    st.divider()
    st.markdown(f"**Latest sensor reading — Row ID: #{int(latest['id'])}**")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Machine",      latest["machine_id"])
    c2.metric("Air Temp",     f"{float(latest['air_temp']):.1f} K")
    c3.metric("Torque",       f"{float(latest['torque']):.1f} Nm")
    c4.metric("Tool Wear",    f"{float(latest['tool_wear']):.0f} min")
    c5.metric("Failure Risk", f"{float(latest['failure_prob']):.1%}")

    st.divider()

    if st.button("Evaluate Driver Metrics", use_container_width=True):
        payload = {
            "machine_id":   str(latest["machine_id"]),
            "air_temp":     float(latest["air_temp"]),
            "process_temp": float(latest["process_temp"]),
            "rot_speed":    float(latest["rot_speed"]),
            "torque":       float(latest["torque"]),
            "tool_wear":    float(latest["tool_wear"]),
        }

        with st.spinner("Calculating SHAP values..."):
            try:
                res = requests.post(f"{API_BASE}/explain", json=payload, timeout=15)
                result    = res.json()
                shap_data = result["shap_values"]

                features = list(shap_data.keys())
                values   = list(shap_data.values())
                colors   = ["#e74c3c" if v > 0 else "#2ecc71" for v in values]

                fig, ax = plt.subplots(figsize=(9, 4))
                fig.patch.set_facecolor("#FAF6ED")
                ax.set_facecolor("#FAF6ED")

                bars = ax.barh(features, values, color=colors, height=0.5)

                for bar, val in zip(bars, values):
                    ax.text(val + (0.002 if val >= 0 else -0.002), bar.get_y() + bar.get_height() / 2, f"{val:+.4f}", va="center", ha="left" if val >= 0 else "right", fontsize=9, color="#030303")

                ax.axvline(0, color="#030303", linewidth=1.0, alpha=0.6)
                st.pyplot(fig)
                plt.close()

                st.markdown("### Raw Breakdown Table")
                shap_df_tab2 = pd.DataFrame({
                    "Sensor Feature": features, 
                    "SHAP Value (Impact)": values
                }).sort_values("SHAP Value (Impact)", ascending=False)
                
                st.dataframe(shap_df_tab2, use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Error: {e}")


st.divider()
st.caption("Auto-refreshing every 3 seconds...")
time.sleep(3)
st.rerun()