from flask import Flask, request, jsonify, render_template_string
import sqlite3
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
DB_PATH = "/tmp/noise_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS noise_events 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     timestamp DATETIME, 
                     doa INTEGER, 
                     volume FLOAT)''')
    conn.close()

init_db()

@app.route('/', methods=['GET'])
def index():
    # 데이터 수신 엔드포인트
    doa = request.args.get('doa')
    vol = request.args.get('vol')
    
    if doa is not None and vol is not None:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO noise_events (timestamp, doa, volume) VALUES (?, ?, ?)",
                     (datetime.now(), int(doa), float(vol)))
        conn.commit()
        conn.close()
        return "OK", 200
        
    # 대시보드 뷰
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM noise_events ORDER BY timestamp DESC LIMIT 20", conn)
    conn.close()
    
    html = f"""
    <h1>🔊 Noise Dashboard</h1>
    <table border="1">
        <tr><th>Time</th><th>DOA</th><th>Volume</th></tr>
        {"".join([f"<tr><td>{row['timestamp']}</td><td>{row['doa']}</td><td>{row['volume']:.2f}</td></tr>" for _, row in df.iterrows()])}
    </table>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
