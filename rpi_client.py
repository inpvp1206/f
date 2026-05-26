import usb.core
import usb.util
import time
import requests
import pyaudio
import numpy as np
import argparse

# --- ReSpeaker v3.0 USB Config ---
VID = 0x2886
PID = 0x0018

# Parameter ID for DOA is 21 for v2.0/v3.0 (XVF3800/XVF3000)
DOA_PARAM_ID = 21

class ReSpeakerClient:
    def __init__(self, server_url, threshold=500, interval=0.5, mock=False):
        self.server_url = server_url
        self.threshold = threshold
        self.interval = interval
        self.mock = mock
        self.dev = None
        
        if not mock:
            self.dev = usb.core.find(idVendor=VID, idProduct=PID)
            if not self.dev:
                print("Warning: ReSpeaker Mic Array v3.0 not found. Switching to Mock mode.")
                self.mock = True
            else:
                # Basic USB initialization (may need udev rules on Linux)
                try:
                    self.dev.reset()
                except Exception as e:
                    print(f"USB Reset failed: {e}")

        # PyAudio setup
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1, # Processed audio
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )

    def get_doa(self):
        if self.mock:
            return np.random.randint(0, 360)
        
        try:
            # Control transfer to read DOA parameter
            # Logic based on Seeed Studio's tuning.py
            data = self.dev.ctrl_transfer(
                usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
                0, DOA_PARAM_ID, 0, 8)
            return data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
        except Exception as e:
            print(f"Error reading DOA: {e}")
            return None

    def get_volume(self):
        data = self.stream.read(1024, exception_on_overflow=False)
        samples = np.frombuffer(data, dtype=np.int16)
        return np.sqrt(np.mean(samples**2)) # RMS Volume

    def send_data(self, doa, volume):
        payload = {
            "doa": int(doa),
            "volume": float(volume),
            "metadata": "RPI_CLIENT_V1"
        }
        try:
            response = requests.post(f"{self.server_url}/log", json=payload, timeout=5)
            print(f"Sent: DOA={doa}, Vol={volume:.2f} | Status: {response.status_code}")
        except Exception as e:
            print(f"Failed to send data: {e}")

    def run(self):
        print(f"Starting Noise Monitor (Server: {self.server_url})...")
        print(f"Threshold: {self.threshold}, Interval: {self.interval}s")
        try:
            while True:
                volume = self.get_volume()
                if volume > self.threshold:
                    doa = self.get_doa()
                    if doa is not None:
                        self.send_data(doa, volume)
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.pa.terminate()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReSpeaker v3.0 Noise Client")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL (e.g. https://your-app.onrender.com)")
    parser.add_argument("--threshold", type=float, default=500, help="Volume threshold for events")
    parser.add_argument("--interval", type=float, default=0.5, help="Polling interval in seconds")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no hardware)")
    
    args = parser.parse_args()
    
    client = ReSpeakerClient(args.url, args.threshold, args.interval, args.mock)
    client.run()
