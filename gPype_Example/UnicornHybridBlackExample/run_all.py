#python run_all.py

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent

HTTP_PORT = 8000
BRIDGE_URL = "http://127.0.0.1:8765/health"
STIM_URL = f"http://127.0.0.1:{HTTP_PORT}/stimuli.html"

def main():
    # 1) Start a local web server to serve stimuli.html
    #    (avoids file:// restrictions and makes fetch() behave)
    http_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(HTTP_PORT)],
        cwd=str(HERE),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 2) Start the UDP bridge
    bridge_proc = subprocess.Popen(
        [sys.executable, "udp_bridge.py"],
        cwd=str(HERE),
        stdout=None,   # keep visible so you can see "[udp_bridge] ..." logs
        stderr=None,
    )

    # Give the servers a moment to bind to ports
    time.sleep(0.5)

    # 3) Open the stimulus page in the default browser
    webbrowser.open(STIM_URL)

    # 4) Run the EEG backend in the foreground (blocks until you close the gpype window)
    try:
        subprocess.run([sys.executable, "example_devices_hybrid_black.py"], cwd=str(HERE), check=False)
    finally:
        # Cleanup: stop bridge + http server
        for proc in (bridge_proc, http_proc):
            try:
                proc.terminate()
            except Exception:
                pass

        # Optional: give them a second, then force kill if needed
        time.sleep(0.5)
        for proc in (bridge_proc, http_proc):
            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass

if __name__ == "__main__":
    main()