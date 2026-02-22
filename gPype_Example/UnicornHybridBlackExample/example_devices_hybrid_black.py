"""
Unicorn Hybrid Black Device Example - Real-time EEG Acquisition and Processing
... (your header unchanged)
"""
import os
from datetime import datetime

import gpype as gp

# Sampling rate (hardware-dependent, fixed at 250 Hz for Unicorn Hybrid Black)
fs = 250


if __name__ == "__main__":

    app = gp.MainApp()
    p = gp.Pipeline()

    # === HARDWARE DATA SOURCE ===
    source = gp.HybridBlack(serial="UN-2019.05.49")

    splitter = gp.Router(input_channels=gp.Router.ALL)

    # === SIGNAL CONDITIONING STAGE ===
    bandpass = gp.Bandpass(f_lo=1, f_hi=30)

    # === POWER LINE INTERFERENCE REMOVAL ===
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)
    notch60 = gp.Bandstop(f_lo=58, f_hi=62)

    # === TRIGGERS (UDP from frontend/bridge) ===
    # Receives UDP trigger values: 1 = START (dot onset), 2 = END (just before next onset)
    trig_ip = "127.0.0.1"
    trig_port = 1000
    trig_receiver = gp.UDPReceiver(ip=trig_ip, port=trig_port)

    # Markers: put triggers on an extra channel index after EEG channels.
    # EEG is 8 channels (0..7), so use channel=8 for trigger channel.
    mk = gp.TimeSeriesScope.Markers
    markers = [
        mk(color="#00aa00", label="START (dot)", channel=8, value=1),
        mk(color="#ff0000", label="END (pre-next)", channel=8, value=2),
    ]

    # === REAL-TIME VISUALIZATION ===
    scope = gp.TimeSeriesScope(amplitude_limit=50, time_window=10, markers=markers)

    # === CSV LOGGING ===
    print('hello')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(script_dir, "recordings")

    os.makedirs(out_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, f"unicorn_hybrid_black_{timestamp}.csv")
    writer = gp.CsvWriter(file_name=csv_path)

    # === PIPELINE CONNECTIONS ===
    p.connect(source, splitter)
    p.connect(splitter, bandpass)
    p.connect(bandpass, notch50)
    p.connect(notch50, notch60)

    # --- Merge EEG + trigger stream for scope ---
    # Combines (filtered EEG) + (trigger values) so the scope can draw markers.
    merge_for_scope = gp.Router(input_channels=[gp.Router.ALL, gp.Router.ALL])
    p.connect(notch60, merge_for_scope["in1"])
    p.connect(trig_receiver, merge_for_scope["in2"])
    p.connect(merge_for_scope, scope)

    # --- Merge EEG + trigger stream for CSV ---
    # This makes your CSV contain both EEG channels and the trigger channel.
    merge_for_save = gp.Router(input_channels=[gp.Router.ALL, gp.Router.ALL])
    p.connect(notch60, merge_for_save["in1"])
    p.connect(trig_receiver, merge_for_save["in2"])
    p.connect(merge_for_save, writer)

    # GUI
    app.add_widget(scope)

    # Run (ensure clean shutdown so CSV closes properly)
    try:
        p.start()
        print("Running. Waiting for UDP triggers from frontend/bridge. Close the window to stop.")
        app.run()
    finally:
        p.stop()

    print(f"Saved CSV to: {csv_path}")
