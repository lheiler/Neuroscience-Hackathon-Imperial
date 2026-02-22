import gpype as gp
from triggered_buffer import TriggerAlignedBuffer
from my_weighted_sum_triggered import MyWeightedSum
import numpy as np
from scipy.io import loadmat

FS = 250    # sampling frequency
N_ch = 8    # Number of channels
K = 7       # downsampling factor (FS//(f_hi*2)) to avoid aliasing
KEY_t = ord('T')    # Trigger Key to wait for
MDL_PATH = r"C:\g\Presentations\2026_ICL_Hackathon\gPype_Example\lda_model.mat"

if __name__ == '__main__':
    print(f"Press any key to trigger the buffer and see LDA output in CSV and Console.")
    print(f"The Trigger Scope will wait for the '{chr(KEY_t)}' key to be pressed to trigger the buffer capture.")
    
    # main app
    app = gp.MainApp(caption="Example LDA Triggered")
    
    # pipeline
    p = gp.Pipeline()

    # amplifier
    amp = gp.Generator(channel_count=N_ch,
                          signal_frequency=10,
                          signal_shape=gp.Generator.SHAPE_SINUSOID,
                          signal_amplitude=25,
                          noise_amplitude=0,
                          sampling_rate=FS)
    
    # bandpass
    f_lo = 1    # Hz
    f_hi = 15   # Hz
    f_bp = gp.Bandpass(f_lo=f_lo,
                       f_hi=f_hi,
                       order=4)
    
    # bandstop
    f_lo = 48   # Hz
    f_hi = 52   # Hz
    f_bs50 = gp.Bandstop(f_lo=f_lo,
                       f_hi=f_hi,
                       order=4)
    
    # bandstop
    f_lo = 58   # Hz
    f_hi = 62   # Hz
    f_bs60 = gp.Bandstop(f_lo=f_lo,
                       f_hi=f_hi,
                       order=4)

    keyboard=gp.Keyboard()

    buffer_downsampler = TriggerAlignedBuffer(buffer_size=int(FS), n_channels=N_ch, fs=FS, K=K)
    mdl = loadmat(MDL_PATH)

    W = mdl['W'][::K, :]    # N_time x N_ch
    offset = mdl['offset']
    d_scalar = offset if np.isscalar(offset) else (offset.flatten()[0] if hasattr(offset, 'flatten') else float(offset))

    weighted_node = MyWeightedSum(W=W, offset=d_scalar)

    router = gp.Router(input_channels=[gp.Router.ALL,[0]])
    router_eeg_trigger = gp.Router(input_channels=[gp.Router.ALL,[0]])

    scope = gp.TimeSeriesScope(amplitude_limit=100, time_window=10)

    trigger = gp.Trigger(time_pre = 0.1, time_post=0.7, target=[KEY_t])
    trigger_scope = gp.TriggerScope(amplitude_limit = 50, hidden_channels=[1,2,3,4,5,6,7])

    # file sink raw
    sink = gp.CsvWriter(file_name=f"Triggered_LDA.csv")

    p.connect(amp, f_bs50)
    p.connect(f_bs50, f_bs60)
    p.connect(f_bs60, f_bp)
    p.connect(f_bp,router_eeg_trigger["in1"])
    p.connect(keyboard,router_eeg_trigger["in2"])

    p.connect(router_eeg_trigger, buffer_downsampler)
    p.connect(buffer_downsampler, weighted_node)    
    p.connect(f_bp, router["in1"])
    p.connect(keyboard, router["in2"])

    p.connect(router, scope)
    p.connect(weighted_node, sink)

    # Connect the trigger analysis pipeline
    p.connect(amp, trigger[gp.Constants.Defaults.PORT_IN])
    p.connect(keyboard, trigger[trigger.PORT_TRIGGER])
    p.connect(trigger, trigger_scope)

    # Add widget to main app
    app.add_widget(scope)
    app.add_widget(trigger_scope)

    # start pipeline and main app
    p.start()
    app.run()
    p.stop()
