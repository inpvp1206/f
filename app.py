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
import os

# --- Database Setup ---
DB_PATH = "/tmp/noise_data.db"
DB_URL = f"sqlite:///{DB_PATH}"
Base = declarative_base()

class NoiseEvent(Base):
    __tablename__ = 'noise_events'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    doa = Column(Integer)
    volume = Column(Float)
    additional_info = Column(String, nullable=True)

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- API Logic (Embedded in Streamlit) ---
params = st.query_params
if "doa" in params and "vol" in params:
    try:
        db = SessionLocal()
        new_event = NoiseEvent(
            doa=int(params["doa"]),
            volume=float(params["vol"]),
            timestamp=datetime.now(),
            additional_info="GET_API"
        )
        db.add(new_event)
        db.commit()
        db.close()
        if params.get("api") == "true":
            st.write("OK")
            st.stop()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

# --- Streamlit Dashboard ---
st.set_page_config(page_title="Noise Monitoring Dashboard", layout="wide")

st.title("🔊 Real-time Noise Monitoring Dashboard")
st.markdown("ReSpeaker Mic Array v3.0 데이터를 활용한 소음 이벤트 시각화")

# Sidebar
st.sidebar.header("Filter & Settings")
time_range = st.sidebar.selectbox("Time Range", ["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "All Time"])

# Data Loading
def get_data(range_str):
    try:
        conn = sqlite3.connect(DB_PATH)
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
    except Exception as e:
        st.error(f"DB Read Error: {e}")
        return pd.DataFrame()

df = get_data(time_range)

# 디버깅용: DB 상태 확인
st.sidebar.info(f"DB 경로: {DB_PATH}, 이벤트 수: {len(df)}")


if df.empty:
    st.info("데이터가 없습니다. 라즈베리 파이에서 데이터를 전송하거나 샘플 데이터를 확인하세요.")
    if st.checkbox("샘플 데이터 보기"):
        df = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i*10) for i in range(20)],
            'doa': np.random.randint(0, 360, 20),
            'volume': np.random.uniform(200, 2000, 20)
        })

if not df.empty:
    # --- Metrics ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 소음 이벤트", f"{len(df)} 건")
    with col2:
        st.metric("평균 소음 수치", f"{df['volume'].mean():.1f} RMS")
    with col3:
        peak_idx = df['volume'].idxmax()
        st.metric("최대 소음 방향", f"{df.loc[peak_idx, 'doa']}°")

    # --- Charts ---
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("📍 소음 발생 방향 (DOA)")
        fig_polar = go.Figure()
        fig_polar.add_trace(go.Scatterpolar(
            r=df['volume'],
            theta=df['doa'],
            mode='markers',
            marker=dict(
                size=10,
                color=df['volume'],
                colorscale='Reds',
                showscale=True
            )
        ))
        fig_polar.update_layout(
            polar=dict(
                angularaxis=dict(direction="clockwise", period=360)
            ),
            height=400
        )
        st.plotly_chart(fig_polar, use_container_width=True)

    with c2:
        st.subheader("📈 시간별 소음 추이")
        fig_line = px.line(df, x='timestamp', y='volume', markers=True)
        fig_line.update_layout(height=400)
        st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("📋 최근 이벤트 로그 (최신 20건)")
    st.dataframe(df.sort_values(by='timestamp', ascending=False).head(20), use_container_width=True)

# Auto-refresh
if st.sidebar.button("데이터 새로고침"):
    st.rerun()

st.sidebar.divider()
st.sidebar.caption("Render 배포 시 'Start Command'를 확인하세요:")
st.sidebar.code(f"streamlit run app.py --server.port $PORT")
