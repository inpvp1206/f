# Noise Monitoring System Instructions

This system allows you to monitor noise events using a ReSpeaker Mic Array v3.0 and visualize them on a web dashboard hosted on Render.

## 1. Server Setup (Render)

1.  **Deployment:** Push this repository to GitHub and connect it to Render as a **Web Service**.
2.  **Build Command:** `pip install -r requirements.txt`
3.  **Start Command:** `streamlit run app.py --server.port $PORT`
4.  **Database:** The system uses SQLite (`noise_data.db`). Note that Render's free tier has a transient filesystem. For persistent data, use Render's Persistent Disk feature.

## 2. Raspberry Pi Setup (Client)

1.  **Run the Client:**
    ```bash
    # Replace URL with your Render app URL
    python rpi_client.py --url https://your-app.onrender.com --threshold 1000
    ```

## 3. Usage
- The dashboard will be available at your Render URL.
- The RPi sends noise data via URL query parameters (GET request).
- The dashboard automatically detects these parameters, saves them to the DB, and displays the updated charts.

## 4. Troubleshooting
- **No hardware?** Run the client in mock mode for testing: `python rpi_client.py --mock`
- **Render Error?** Ensure the Start Command is exactly `streamlit run app.py --server.port $PORT`.
