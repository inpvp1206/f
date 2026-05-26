import usb.core
import usb.util
import time
import requests
import pyaudio
import numpy as np
import argparse
import struct
import os
import sys
import tuning  # 공식 라이브러리 사용

# --- ReSpeaker v3.0 USB Config ---
VID = 0x2886
PID = 0x0018

class ReSpeakerClient:
    def __init__(self, server_url, threshold=500, interval=0.5, channels=6, mock=False):
        self.server_url = server_url
        self.threshold = threshold
        self.interval = interval
        self.channels = channels
        self.mock = mock
        self.dev = None
        self.mic_tuning = None
        
        if not mock:
            self.dev = usb.core.find(idVendor=VID, idProduct=PID)
            if not self.dev:
                print("Warning: ReSpeaker Mic Array v3.0 not found. Switching to Mock mode.")
                self.mock = True
            else:
                try:
                    self.mic_tuning = tuning.Tuning(self.dev)
                except Exception as e:
                    print(f"Failed to initialize tuning: {e}")
                    self.mock = True

        # PyAudio setup (with ALSA error suppression)
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(sys.stderr.fileno())
        os.dup2(devnull, sys.stderr.fileno())
        try:
            self.pa = pyaudio.PyAudio()
        finally:
            os.dup2(old_stderr, sys.stderr.fileno())
            os.close(devnull)
            
        input_device_index = self._find_respeaker_index()
        
        try:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=16000,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=1024
            )
        except Exception as e:
            print(f"Error opening audio stream: {e}")
            self.mock = True
            self.stream = None

    def _find_respeaker_index(self):
        """Find the PyAudio index for ReSpeaker device."""
        device_count = self.pa.get_device_count()
        found_index = None
        for i in range(device_count):
            try:
                dev_info = self.pa.get_device_info_by_index(i)
                name = dev_info.get('name', '')
                if any(kw in name for kw in ['ReSpeaker', 'XVF', 'Array', 'seeed']):
                    found_index = i
                    break
            except:
                continue
        return found_index

    def get_doa(self):
        if self.mock or not self.mic_tuning:
            return np.random.randint(0, 360)
        
        try:
            return self.mic_tuning.direction
        except Exception as e:
            print(f"Error reading DOA via tuning: {e}")
            return None


    def get_volume(self):
        if self.mock or self.stream is None:
            return np.random.uniform(0, 1000) # Mock volume
            
        try:
            data = self.stream.read(1024, exception_on_overflow=False)
            all_channels = np.frombuffer(data, dtype=np.int16).astype(np.float64)
            
            # If multi-channel, extract channel 0 (Processed Audio)
            if self.channels > 1:
                # all_channels is [c0, c1, ..., cN, c0, c1, ...]
                processed_audio = all_channels[0::self.channels]
                return np.sqrt(np.mean(processed_audio**2))
            
            return np.sqrt(np.mean(all_channels**2)) # RMS Volume
        except Exception as e:
            print(f"Error reading audio: {e}")
            return 0

    def send_data(self, doa, volume):
        # Using GET parameters for compatibility with single-port Streamlit deployment
        params = {
            "doa": int(doa),
            "vol": float(volume),
            "api": "true"
        }
        try:
            response = requests.get(self.server_url, params=params, timeout=5)
            print(f"Sent: DOA={doa}, Vol={volume:.2f} | Status: {response.status_code}")
        except Exception as e:
            print(f"Failed to send data: {e}")

    def run(self):
        print(f"Starting Noise Monitor (Server: {self.server_url})...")
        print(f"Threshold: {self.threshold}, Interval: {self.interval}s")
        if self.mock:
            print("RUNNING IN MOCK MODE")
            
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
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.pa.terminate()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReSpeaker v3.0 Noise Client")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL (e.g. https://your-app.onrender.com)")
    parser.add_argument("--threshold", type=float, default=500, help="Volume threshold for events")
    parser.add_argument("--interval", type=float, default=0.5, help="Polling interval in seconds")
    parser.add_argument("--channels", type=int, default=6, help="Number of input channels (1 or 6)")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no hardware)")
    
    args = parser.parse_args()
    
    client = ReSpeakerClient(args.url, args.threshold, args.interval, args.channels, args.mock)
    client.run()
