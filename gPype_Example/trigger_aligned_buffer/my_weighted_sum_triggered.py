import gpype as gp
from typing import Dict
import numpy as np

PORT_IN = gp.Constants.Defaults.PORT_IN
PORT_OUT = gp.Constants.Defaults.PORT_OUT


class MyWeightedSum(gp.IONode):
    """Weighted sum node that computes a scalar output from input data.
    
    Performs element-wise multiplication of input data [N, N_ch+1] (buffer with trigger column appended)
    with weight matrix W [N, N_ch], sums all elements, and adds a scalar offset.
    
    Output = sum(X * W) + offset, preserving trigger column.
    """
    
    def __init__(self, W: np.ndarray = None, offset: float = 0.0, n_channels: int = 8, **kwargs):
        """Initialize weighted sum with weight matrix and offset.
        
        Args:
            W: Weight matrix of shape [N, N_ch].
            offset: Scalar offset to add after weighted sum.
            n_channels: Number of EEG channels.
            **kwargs: Additional arguments for parent IONode.
        """
        # Configure input port as sync (to accept from sync sources)
        input_ports = [gp.IPort.Configuration(timing=gp.Constants.Timing.SYNC)]
        input_ports = kwargs.pop(gp.Constants.Keys.INPUT_PORTS, input_ports)
        
        # Configure output port
        output_ports = [gp.OPort.Configuration()]
        output_ports = kwargs.pop(gp.Constants.Keys.OUTPUT_PORTS, output_ports)
        
        super().__init__(input_ports=input_ports, output_ports=output_ports, **kwargs)
        # Store weights and offset as instance variables (config is read-only)
        self._W = W
        self._offset = float(offset)
        self._n_channels = n_channels
    
    def setup(self, data: dict, port_context_in: dict) -> dict:
        """Setup output context with async timing."""
        out_ctx = {}
        first_ctx = next(iter(port_context_in.values()))
        out_ctx[PORT_OUT] = first_ctx
        out_ctx[PORT_OUT]["timing"] = gp.Constants.Timing.ASYNC
        
        sample_data = data[PORT_IN]
        if sample_data.ndim == 1:
            N = len(sample_data) // (self._n_channels + 1)
            sample_data = sample_data.reshape(N, self._n_channels + 1)
        data_eeg = sample_data[:, :-1]
        expected_samples = data_eeg.shape[0] // 7
        
        if self._W is None:
            self._W = np.ones((expected_samples, self._n_channels))
        
        return out_ctx
    
    def step(self, data: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Compute weighted sum of input data.
        
        Args:
            data: Input data dictionary with shape [N, N_ch+1] (buffer with trigger column appended).
            
        Returns:
            Dictionary with scalar output value [[result, trigger_col]], preserving trigger column.
        """
        data_in = data[PORT_IN]
        
        # Check if data is empty
        if not isinstance(data_in, np.ndarray) or data_in.size == 0:
            return {}  # Skip output if no data
        
        if data_in.ndim == 1:
            N = len(data_in) // (self._n_channels + 1)
            data_in = data_in.reshape(N, self._n_channels + 1)
        
        # Extract EEG (all but last column) and trigger (last column)
        trigger_col = data_in[-1, -1]  # Get trigger value from last sample, last column
        data_eeg = data_in[:, :-1]  # Remove trigger column
        
        # EEG data is expected to match the shape of W[0] if self._W is not None else data_eeg.shape[0] // 7
        if data_eeg.shape[0] > self._W.shape[0]:
            K = data_eeg.shape[0] // self._W.shape[0]
            data_eeg_dec = data_eeg[::K, :]
        else:
            data_eeg_dec = data_eeg
        
        # Check dimension match
        if data_eeg_dec.shape != self._W.shape:
            print(f"[MyWeightedSum] Shape mismatch: data {data_eeg_dec.shape} vs weights {self._W.shape}")
            return {}
        
        # Compute weighted sum: sum(X * W)
        weighted_sum = np.sum(data_eeg_dec * self._W)
        
        # Add offset
        result = weighted_sum + self._offset
        print(f"[MyWeightedSum] Computed result: {result} with trigger: {trigger_col}")
        # Output as 2D array with result and trigger
        return {PORT_OUT: np.array([[result, trigger_col]])}
    