from flask import Flask, request, render_template_string
import sqlite3
import pandas as pd
from datetime import datetime
import os
import json

app = Flask(__name__)
DB_PATH = "/tmp/noise_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS noise_events 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     timestamp DATETIME, 
                     doa INTEGER, 
                     volume FLOAT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET'])
def index():
    doa = request.args.get('doa')
    vol = request.args.get('vol')
    
    if doa is not None and vol is not None:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO noise_events (timestamp, doa, volume) VALUES (?, ?, ?)",
                     (datetime.now(), int(doa), float(vol)))
        conn.commit()
        conn.close()
        return "OK", 200
        
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM noise_events ORDER BY timestamp DESC LIMIT 20", conn)
    conn.close()
    
    labels = df['timestamp'].dt.strftime('%H:%M:%S').tolist()[::-1]
    values = df['volume'].tolist()[::-1]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Noise Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h1>🔊 Real-time Noise Monitoring Dashboard</h1>
        <canvas id="myChart" width="400" height="100"></canvas>
        <table border="1">
            <tr><th>Time</th><th>DOA</th><th>Volume</th></tr>
            {"".join([f"<tr><td>{row['timestamp']}</td><td>{row['doa']}</td><td>{row['volume']:.2f}</td></tr>" for _, row in df.iterrows()])}
        </table>
        <script>
            const ctx = document.getElementById('myChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{ label: 'Volume', data: {json.dumps(values)}, borderColor: 'red' }}]
                }}
            }});
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
