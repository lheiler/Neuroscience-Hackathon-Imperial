import gpype as gp
from my_buffer_downsampler import MyBufferDownsampler
from my_weighted_sum import MyWeightedSum
import numpy as np
from scipy.io import loadmat

FS = 250    # sampling frequency
N_ch = 8    # Number of channels
K = 7       # downsampling factor (FS//(f_hi*2)) to avoid aliasing
N_BUFFER = FS  # Number of samples to buffer (1 second at 250Hz)
MDL_PATH = r"C:\g\Presentations\2026_ICL_Hackathon\gPype_Example\lda_model.mat"

if __name__ == '__main__':

    # main app
    app = gp.MainApp(caption="Example LDA")

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

    buffer_downsampler = MyBufferDownsampler(N=N_BUFFER, K=K)
    mdl = loadmat(MDL_PATH)

    W = mdl['W'][::K, :]
    offset = mdl['offset']
    weighted_node = MyWeightedSum(W=W, offset=offset)

    # router for BP
    router = gp.Router(input_channels=[gp.Router.ALL,
                                           [0]])
    

    scope = gp.TimeSeriesScope(amplitude_limit=100,
                               time_window=10)


    # file sink raw
    sink = gp.CsvWriter(file_name=f"Continuous_LDA.csv")
    

    p.connect(amp, f_bs50)
    p.connect(f_bs50, f_bs60)
    p.connect(f_bs60, f_bp)
    p.connect(f_bp, buffer_downsampler)
    p.connect(buffer_downsampler, weighted_node)    
    p.connect(f_bp, router["in1"])
    p.connect(weighted_node, router["in2"])

    p.connect(router, scope)
    p.connect(router, sink)

    # Add widget to main app
    app.add_widget(scope)

    # start pipeline and main app
    p.start()
    app.run()
    p.stop()
