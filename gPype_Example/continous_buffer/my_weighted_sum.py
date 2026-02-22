import gpype as gp
from typing import Dict
import numpy as np

PORT_IN = gp.Constants.Defaults.PORT_IN
PORT_OUT = gp.Constants.Defaults.PORT_OUT


class MyWeightedSum(gp.IONode):
    """Weighted sum node that computes a scalar output from input data.
    
    Performs element-wise multiplication of input data [N, N_ch] with weight matrix W [N, N_ch],
    sums all elements, and adds a scalar offset.
    
    Output = sum(X * W) + offset
    """
    
    def __init__(self, W: np.ndarray = None, offset: float = 0.0, **kwargs):
        """Initialize weighted sum with weight matrix and offset.
        
        Args:
            W: Weight matrix of shape [N, N_ch]. If None, will be initialized in setup.
            offset: Scalar offset to add after weighted sum.
            **kwargs: Additional arguments for parent IONode.
        """
        super().__init__(W=W, offset=offset, **kwargs)
        self._W = W
    
    def setup(self, data: dict[str, np.ndarray], port_context_in: dict[str, dict]) -> dict[str, dict]:
        """Setup weight matrix if not provided.
        
        Args:
            data: Input data arrays.
            port_context_in: Input port contexts.
            
        Returns:
            Output port contexts.
        """
        port_context_out = super().setup(data, port_context_in)
        
        sample_data = data[PORT_IN]
        
        # Initialize weight matrix if not provided
        if self._W is None:
            # Initialize with ones (uniform weighting)
            self._W = np.ones_like(sample_data)
            self.config['W'] = self._W
        else:
            self._W = self.config['W']
            
            # Verify shape compatibility
            if self._W.shape != sample_data.shape:
                raise ValueError(
                    f"Weight matrix shape {self._W.shape} does not match "
                    f"input data shape {sample_data.shape}"
                )
        
        return port_context_out
    
    def step(self, data: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Compute weighted sum of input data.
        
        Args:
            data: Input data dictionary with shape [N, N_ch] or [N,].
            
        Returns:
            Dictionary with scalar output value.
        """
        data_in = data[PORT_IN]
        offset = self.config['offset']
        
        # Element-wise multiplication and sum
        # X * W gives element-wise product, then sum all elements
        weighted_sum = np.sum(data_in * self._W)
        # print(f"Weighted Sum: {weighted_sum}, Offset: {offset}, Result: {weighted_sum + offset}")
        # Add offset
        result = weighted_sum + offset
        # Output as scalar (0D array) or 1D array with single element
        return {PORT_OUT: np.array([[result]])}
    