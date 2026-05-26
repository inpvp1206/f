import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import threading
import time

# --- Database Setup ---
DB_URL = "sqlite:///noise_data.db"
Base = declarative_base()

class NoiseEvent(Base):
    __tablename__ = 'noise_events'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    doa = Column(Integer)  # Direction of Arrival (0-359)
    volume = Column(Float) # Volume/Amplitude
    metadata = Column(String, nullable=True)

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- FastAPI App for Data Logging ---
api_app = FastAPI()

class NoiseLog(BaseModel):
    doa: int
    volume: float
    metadata: str = None

@api_app.post("/log")
async def log_noise(data: NoiseLog):
    db = SessionLocal()
    try:
        new_event = NoiseEvent(
            doa=data.doa,
            volume=data.volume,
            metadata=data.metadata,
            timestamp=datetime.now()
        )
        db.add(new_event)
        db.commit()
        return {"status": "success", "id": new_event.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@api_app.get("/health")
async def health():
    return {"status": "ok"}

def run_api():
    uvicorn.run(api_app, host="0.0.0.0", port=8000)

# Start FastAPI in a background thread
if 'api_thread' not in st.session_state:
    thread = threading.Thread(target=run_api, daemon=True)
    thread.start()
    st.session_state['api_thread'] = True

# --- Streamlit Dashboard ---
st.set_page_config(page_title="Noise Monitoring Dashboard", layout="wide")

st.title("🔊 Real-time Noise Monitoring Dashboard")
st.markdown("ReSpeaker Mic Array v3.0 데이터를 활용한 소음 이벤트 및 위치 시각화")

# Sidebar
st.sidebar.header("Filter & Settings")
time_range = st.sidebar.selectbox("Time Range", ["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "All Time"])

# Data Loading
def get_data(range_str):
    conn = sqlite3.connect("noise_data.db")
    query = "SELECT * FROM noise_events"
    
    if range_str == "Last 1 Hour":
        query += f" WHERE timestamp > '{ (datetime.now() - timedelta(hours=1)).isoformat() }'"
    elif range_str == "Last 6 Hours":
        query += f" WHERE timestamp > '{ (datetime.now() - timedelta(hours=6)).isoformat() }'"
    elif range_str == "Last 24 Hours":
        query += f" WHERE timestamp > '{ (datetime.now() - timedelta(hours=24)).isoformat() }'"
        
    df = pd.read_sql_query(query, conn)
    conn.close()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

df = get_data(time_range)

if df.empty:
    st.warning("No data found for the selected range. Send some data to /log endpoint!")
    # Show dummy data if empty for preview (optional)
    if st.checkbox("Show sample data"):
        df = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(10)],
            'doa': np.random.randint(0, 360, 10),
            'volume': np.random.uniform(20, 80, 10)
        })
else:
    # --- Metrics ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Events", len(df))
    with col2:
        st.metric("Avg Volume", f"{df['volume'].mean():.2f} dB")
    with col3:
        peak_doa = df.loc[df['volume'].idxmax(), 'doa'] if not df.empty else 0
        st.metric("Peak Noise Dir", f"{peak_doa}°")

    # --- Charts ---
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("📍 Direction of Noise (DOA)")
        # Polar plot for DOA
        fig_polar = go.Figure()
        fig_polar.add_trace(go.Scatterpolar(
            r=df['volume'],
            theta=df['doa'],
            mode='markers',
            marker=dict(
                size=10,
                color=df['volume'],
                colorscale='Viridis',
                showscale=True
            ),
            name='Noise Events'
        ))
        fig_polar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, df['volume'].max() + 10]),
                angularaxis=dict(direction="clockwise", period=360)
            )
        )
        st.plotly_chart(fig_polar, use_container_width=True)

    with c2:
        st.subheader("📈 Noise Level Over Time")
        fig_line = px.line(df, x='timestamp', y='volume', title="Volume Trend")
        st.plotly_chart(fig_line, use_container_width=True)

    # --- History Table ---
    st.subheader("📋 Recent Events")
    st.dataframe(df.sort_values(by='timestamp', ascending=False).head(20), use_container_width=True)

# Auto-refresh
if st.sidebar.button("Refresh Data"):
    st.rerun()

# API Info
st.sidebar.divider()
st.sidebar.info(f"""
**API Endpoint:** `POST /log`  
**Internal Port:** 8000  
**Schema:** `{{ "doa": int, "volume": float, "metadata": str }}`
""")
