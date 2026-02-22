import numpy as np
from pyriemann.estimation import Covariances
from pyriemann.tangentspace import TangentSpace
from pyriemann.utils.base import invsqrtm, powm
from pyriemann.utils.mean import mean_covariance
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.base import BaseEstimator, TransformerMixin
from scipy.signal import butter, sosfiltfilt

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

class FilterBankRiemannian(BaseEstimator, TransformerMixin):
    def __init__(self, sfreq=256.0, verbose=False):
        self.sfreq = sfreq
        self.verbose = verbose
        self.bands = [
            (4, 12),   # Theta/Alpha
            (12, 30),  # Beta
            (30, 45),  # Low Gamma
            (45, 90)   # High Gamma
        ]
        self.pipes = [
            Pipeline([
                ('cov', Covariances(estimator='lwf')),
                ('ts', TangentSpace(metric='riemann'))
            ]) for _ in self.bands
        ]

    def _bandpass_filter(self, data, lowcut, highcut, order=4):
        sos = butter(order, [lowcut, highcut], btype='band', fs=self.sfreq, output='sos')
        return sosfiltfilt(sos, data, axis=-1)

    def fit(self, X, y=None):
        if self.verbose:
            print("    [FBR] Processing Bands: ", end="", flush=True)
            
        for i, (low, high) in enumerate(self.bands):
            if self.verbose:
                print(f"{i+1}..", end="", flush=True)
            X_band = self._bandpass_filter(X, low, high)
            self.pipes[i].fit(X_band, y)
            
        if self.verbose:
            print("Done.")
        return self

    def transform(self, X):
        features = []
        for i, (low, high) in enumerate(self.bands):
            X_band = self._bandpass_filter(X, low, high)
            features.append(self.pipes[i].transform(X_band))
        return np.concatenate(features, axis=1)

def get_riemannian_model(verbose=False):
    """
    Implements a FilterBank Riemannian (FBR) pipeline.
    Captures spectral-spatial signatures across multiple neural frequencies.
    """
    return Pipeline([
        ('fbr', FilterBankRiemannian(sfreq=256.0, verbose=verbose)),
        ('clf', LogisticRegression(C=0.01, penalty='l2', solver='lbfgs', class_weight='balanced', max_iter=1000))
    ])

