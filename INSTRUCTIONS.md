# Noise Monitoring System Instructions

This system allows you to monitor noise events using a ReSpeaker Mic Array v3.0 and visualize them on a web dashboard hosted on Render.

## 1. Server Setup (Render)

1.  **Deployment:** Push this repository to GitHub and connect it to Render as a **Web Service**.
2.  **Build Command:** `pip install -r requirements.txt`
3.  **Start Command:** `streamlit run app.py --server.port $PORT`
4.  **Database:** The system uses SQLite (`noise_data.db`). Note that Render's free tier has a transient filesystem. For persistent data, use Render's Persistent Disk feature.

## 2. Raspberry Pi Setup (Client)

1.  **System Dependencies:**
    ```bash
    sudo apt-get update
    sudo apt-get install -y libasound2-dev portaudio19-dev python3-pyaudio libusb-1.0-0-dev
    ```
2.  **Permissions (USB Access):**
    By default, USB devices require root privileges. You can run with `sudo` or add a udev rule:
    ```bash
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="2886", ATTR{idProduct}=="0018", MODE="0666"' | sudo tee /etc/udev/rules.d/99-respeaker.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    ```
3.  **Run the Client:**
    ```bash
    pip install -r requirements.txt
    # Replace URL with your Render app URL
    python rpi_client.py --url https://your-app.onrender.com --threshold 1000
    ```

## 3. Usage
- The dashboard will be available at your Render URL.
- The RPi sends noise data via URL query parameters (GET request).
- The dashboard automatically detects these parameters, saves them to the DB, and displays the updated charts.

## 4. Troubleshooting
- **No hardware?** Run the client in mock mode for testing: `python rpi_client.py --mock`
- **Permission Denied?** Ensure you added the udev rule or run with `sudo`.
- **PyAudio Error?** Ensure `libasound2-dev` and `portaudio19-dev` are installed.
- **Render Error?** Ensure the Start Command is exactly `streamlit run app.py --server.port $PORT`.
