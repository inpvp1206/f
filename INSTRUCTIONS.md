# Noise Monitoring System Instructions

This system allows you to monitor noise events using a ReSpeaker Mic Array v3.0 and visualize them on a web dashboard hosted on Render.

## 1. Server Setup (Render)

1.  **Deployment:** Push this repository to GitHub and connect it to Render as a **Web Service**.
2.  **Build Command:** `pip install -r requirements.txt`
3.  **Start Command:** `streamlit run app.py`
4.  **Database:** The system uses SQLite (`noise_data.db`). Note that Render's free tier has a transient filesystem. For persistent data, you may want to connect a persistent disk or use an external database like Supabase (PostgreSQL).

## 2. Raspberry Pi Setup (Client)

1.  **Hardware:** Connect the ReSpeaker Mic Array v3.0 to your Raspberry Pi via USB.
2.  **Dependencies:**
    ```bash
    sudo apt-get install libasound2-dev libusb-1.0-0-dev
    pip install pyusb pyaudio requests numpy
    ```
3.  **Permissions:** Add a udev rule to access the USB device without sudo:
    ```bash
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="2886", ATTR{idProduct}=="0018", MODE="0666"' | sudo tee /etc/udev/rules.d/99-respeaker.rules
    sudo udevadm control --reload-rules && sudo udevadm trigger
    ```
4.  **Run the Client:**
    ```bash
    # Replace URL with your Render app URL
    python rpi_client.py --url https://your-app.onrender.com --threshold 1000
    ```

## 3. Usage
- The dashboard will be available at your Render URL.
- The RPi will send noise events (DOA and volume) whenever the sound level exceeds the threshold.
- The dashboard updates in real-time (requires manual refresh or button click).

## 4. Troubleshooting
- **No hardware?** Run the client in mock mode for testing: `python rpi_client.py --mock`
- **Port Conflicts:** The internal API runs on port 8000. Ensure it doesn't conflict with other services.
