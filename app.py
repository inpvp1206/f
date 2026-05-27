from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Cross-platform SQLite DB Path setup (using local dir by default)
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "noise_data.db")
DB_PATH = os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)

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

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

@app.route('/', methods=['GET'])
def index():
    doa = request.args.get('doa')
    vol = request.args.get('vol')
    
    # Check if this is a GET request sending data from the RPi client
    if doa is not None and vol is not None:
        conn = sqlite3.connect(DB_PATH)
        # Use standard string representation of datetime
        conn.execute("INSERT INTO noise_events (timestamp, doa, volume) VALUES (?, ?, ?)",
                     (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), int(doa), float(vol)))
        conn.commit()
        conn.close()
        return "OK", 200
        
    # Serve index.html dashboard
    try:
        # Load local index.html dynamically to support edits without restarting Flask
        index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "index.html not found in project directory. Please create it.", 404

@app.route('/api/data', methods=['GET'])
def get_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query last 50 noise events for rendering in charts and tables
    cursor.execute("SELECT * FROM noise_events ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    
    events = []
    for r in rows:
        events.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "doa": r["doa"],
            "volume": r["volume"]
        })
        
    # Fetch aggregates
    cursor.execute("SELECT COUNT(*) as count, AVG(volume) as avg_vol, MAX(volume) as max_vol FROM noise_events")
    stats_row = cursor.fetchone()
    total_count = stats_row["count"] or 0
    avg_volume = stats_row["avg_vol"] or 0.0
    max_volume = stats_row["max_vol"] or 0.0
    
    # Find most active Direction of Arrival (DOA of the maximum volume event)
    cursor.execute("SELECT doa FROM noise_events ORDER BY volume DESC LIMIT 1")
    peak_doa_row = cursor.fetchone()
    peak_doa = peak_doa_row["doa"] if peak_doa_row else 0
    
    # Calculate alerts today (volume >= 3000)
    today_str = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) as alert_count FROM noise_events WHERE timestamp LIKE ? AND volume >= 3000", (f"{today_str}%",))
    alerts_today = cursor.fetchone()["alert_count"] or 0
    
    conn.close()
    
    # Reverse events to chronological order for streaming chart
    events_chrono = events[::-1]
    
    return jsonify({
        "events": events_chrono,
        "stats": {
            "total_count": total_count,
            "avg_volume": round(avg_volume, 2),
            "max_volume": round(max_volume, 2),
            "peak_doa": peak_doa,
            "alerts_today": alerts_today
        }
    })

@app.route('/api/historical', methods=['GET'])
def get_historical_data():
    period = request.args.get('period', '24h')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM noise_events"
    params = []
    
    if period != 'all':
        now = datetime.now()
        if period == '1h':
            start_time = now - timedelta(hours=1)
        elif period == '6h':
            start_time = now - timedelta(hours=6)
        elif period == '24h':
            start_time = now - timedelta(hours=24)
        else:
            start_time = now - timedelta(hours=24)  # default
            
        query += " WHERE timestamp >= ?"
        params.append(start_time.strftime('%Y-%m-%d %H:%M:%S'))
        
    query += " ORDER BY timestamp DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    events = []
    for r in rows:
        events.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "doa": r["doa"],
            "volume": r["volume"]
        })
        
    return jsonify({
        "events": events,
        "period": period,
        "count": len(events)
    })

@app.route('/api/clear', methods=['POST', 'OPTIONS'])
def clear_data():
    if request.method == 'OPTIONS':
        return '', 200
        
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM noise_events")
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "All noise event history cleared."}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)
