import numpy as np
import gpype as gp

class TriggerAlignedBuffer(gp.IONode):
    """Buffer that resets on trigger and accumulates 0-500ms post-stimulus.
    
    Simple trigger-aligned buffer for LDA classification:
    - Detects trigger rising edge (0 → non-zero)
    - Accumulates EEG data for 0-500ms after trigger
    - Outputs buffer PLUS trigger ID that caused it (to align in CSV)
    """
    
    PORT_IN = gp.Constants.Defaults.PORT_IN
    PORT_OUT = gp.Constants.Defaults.PORT_OUT
    
    def __init__(self, buffer_size=125, n_channels=8, fs=250, K=1, **kwargs):
        """Initialize trigger-aligned buffer.
        
        Parameters:
        -----------
        buffer_size : int, samples to store (125 samples = 500ms at 250Hz)
        n_channels : int, number of EEG channels (8)
        fs : int, sampling frequency (Hz)
        K : int, downsampling factor across time (default=1, no downsampling)
        """
        # Configure input port as sync (to accept from sync sources)
        input_ports = [gp.IPort.Configuration(timing=gp.Constants.Timing.SYNC)]
        input_ports = kwargs.pop(gp.Constants.Keys.INPUT_PORTS, input_ports)
        
        # Configure output port
        output_ports = [gp.OPort.Configuration()]
        output_ports = kwargs.pop(gp.Constants.Keys.OUTPUT_PORTS, output_ports)
        
        super().__init__(input_ports=input_ports, output_ports=output_ports, **kwargs)
        self.buffer_size = buffer_size
        self.n_channels = n_channels
        self.fs = fs
        self.K = K  # Downsampling factor
        
        self.buffer = None
        self.sample_since_trigger = -1  # -1 = waiting, 0+ = accumulating
        self.last_trigger_value = 0
        self.current_trigger_id = 0  # Store trigger that started this buffer

    def setup(self, data: dict, port_context_in: dict) -> dict:
        """Ensure input port contexts include required metadata for gpype validation.

        The TriggerAlignedBuffer expects input frames containing `n_channels`
        EEG channels plus one trigger column. Newer gpype versions require
        `channel_count`, `frame_size`, `sampling_rate`, and `timing` to be
        present in input contexts; populate sensible defaults here.
        """

        out_ctx = {}
        first_ctx = next(iter(port_context_in.values()))
        out_ctx[self.PORT_OUT] = first_ctx
        out_ctx[self.PORT_OUT]["timing"] = gp.Constants.Timing.ASYNC
        return out_ctx
    
    def step(self, data: dict) -> dict:
        """Accumulate data after trigger - output full 0-500ms window WITH trigger ID."""
        try:
            if self.PORT_IN not in data:
                return {self.PORT_OUT: np.array([])}
            
            x = data[self.PORT_IN]
            if not isinstance(x, np.ndarray) or x.size == 0:
                return {self.PORT_OUT: np.array([])}
            
            # Ensure 2D
            if x.ndim == 1:
                x = x.reshape(1, -1)
            
            # Initialize buffer on first data
            if self.buffer is None:
                self.buffer = np.zeros((self.buffer_size, self.n_channels), dtype=np.float32)
            
            # Extract EEG (all but last column) and trigger (last column)
            eeg_data = x[:, :self.n_channels]
            trigger_data = x[:, self.n_channels]
            eeg_sample = eeg_data[-1:, :]
            trigger_value = float(trigger_data[-1])
            real_trigger_value = float(trigger_data[-1])

            # Detect trigger edge (0 → non-zero)
            if trigger_value != 0 and self.last_trigger_value == 0:
                self.sample_since_trigger = 0
                self.current_trigger_id = int(real_trigger_value)  # Store the trigger ID
                print(f"[TriggerAlignedBuffer] Trigger {self.current_trigger_id} received - starting 0-500ms window")

            self.last_trigger_value = trigger_value
            
            # Accumulate data after trigger
            if self.sample_since_trigger >= 0:
                if self.sample_since_trigger < self.buffer_size:
                    self.buffer[self.sample_since_trigger, :] = eeg_sample[0, :]
                    self.sample_since_trigger += 1
                    
                    # Buffer full - output and reset
                    if self.sample_since_trigger >= self.buffer_size:
                        # Apply downsampling across time dimension
                        output_eeg = self.buffer[::self.K, :].copy()
                        
                        # Keep original trigger ID in CSV 
                        trigger_col = np.full((output_eeg.shape[0], 1), self.current_trigger_id, dtype=np.float32)
                        output = np.hstack([output_eeg, trigger_col])

                        self.sample_since_trigger = -1  # Reset for next trigger
                        return {self.PORT_OUT: output}
            
            return {self.PORT_OUT: np.array([])}
        
        except Exception as e:
            print(f"[TriggerAlignedBuffer] Error: {e}")
            return {self.PORT_OUT: np.array([])}
