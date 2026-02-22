import gpype as gp
from typing import Dict
import numpy as np

PORT_IN = gp.Constants.Defaults.PORT_IN
PORT_OUT = gp.Constants.Defaults.PORT_OUT


class MyBufferDownsampler(gp.IONode):
    """Buffer node with downsampling capability.
    
    Maintains a sliding window buffer of the last N samples and outputs
    a downsampled version by taking every Kth sample starting from index 0.
    The buffer is output every step, so the sampling rate remains unchanged.
    """
    
    def __init__(self, N: int = 100, K: int = 1, **kwargs):
        """Initialize buffer with desired length and downsampling factor.
        
        Args:
            N: Buffer length (number of samples to store).
            K: Downsampling factor (takes every Kth sample). K=1 means no downsampling.
            **kwargs: Additional arguments for parent IONode.
        """
        super().__init__(N=N, K=K, **kwargs)
        self._buffer = None
        self._is_filled = False
    
    def setup(self, data: dict[str, np.ndarray], port_context_in: dict[str, dict]) -> dict[str, dict]:
        """Setup buffer and output context.
        
        Args:
            data: Input data arrays.
            port_context_in: Input port contexts.
            
        Returns:
            Output port contexts with same sampling rate as input.
        """
        port_context_out = super().setup(data, port_context_in)
        
        # Initialize buffer based on input data shape
        sample_data = data[PORT_IN]
        N = self.config['N']
        
        # Buffer shape: (N, num_channels)
        if sample_data.ndim == 1:
            buffer_shape = (N,)
        else:
            buffer_shape = (N, sample_data.shape[1])
        
        self._buffer = np.zeros(buffer_shape, dtype=sample_data.dtype)
        self._is_filled = False
        
        # Sampling rate remains the same as input
        # (we output every step, just with fewer samples in the buffer)
        sr_key = gp.Constants.Keys.SAMPLING_RATE
        if sr_key in port_context_in[PORT_IN]:
            sampling_rate_in = port_context_in[PORT_IN][sr_key]
            port_context_out[PORT_OUT][sr_key] = sampling_rate_in
        
        return port_context_out
    
    def step(self, data: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Process one step: update buffer and output downsampled version.
        
        Args:
            data: Input data dictionary.
            
        Returns:
            Dictionary with downsampled buffer (takes every Kth sample starting from index 0).
        """
        data_in = data[PORT_IN]
        N = self.config['N']
        K = self.config['K']
        
        # Number of new samples
        num_new_samples = data_in.shape[0]
        
        if num_new_samples >= N:
            # If we have more samples than buffer size, just take the last N
            self._buffer = data_in[-N:]
            self._is_filled = True
        else:
            # Shift buffer and append new data
            self._buffer = np.roll(self._buffer, -num_new_samples, axis=0)
            self._buffer[-num_new_samples:] = data_in
            
            if not self._is_filled:
                self._is_filled = True
        
        # Downsample: take every Kth sample starting from index 0
        # Example: buffer length 10, K=4 -> indices [0, 4, 8]
        downsampled = self._buffer[::K]
        # print(f"Buffer Size: {self._buffer.shape}, Downsampled Size: {downsampled.shape}, Average Value: {np.mean(downsampled)}")
        return {PORT_OUT: downsampled.copy()}