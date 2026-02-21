import torch
import torch.nn as nn

class Conv2dWithConstraint(nn.Conv2d):
    """
    Standard Conv2d but applies MaxNorm constraint to weights if needed, 
    often used in EEGNet. Here we just implement the standard forward, 
    but you can add weight constraints in the training loop.
    """
    def __init__(self, *args, max_norm=1.0, **kwargs):
        self.max_norm = max_norm
        super(Conv2dWithConstraint, self).__init__(*args, **kwargs)

class EEGNet(nn.Module):
    """
    EEGNet: A Compact Convolutional Neural Network for EEG-based Brain-Computer Interfaces.
    This implementation mimics the standard EEGNet-8,2 architecture using PyTorch.
    It heavily relies on Depthwise and Separable convolutions to minimize parameters and thus drastically reduce overfitting on noisy EEG data.
    """
    def __init__(self, num_classes=4, in_channels=128, F1=8, D=2, F2=16, kernel_length=64, dropout_rate=0.5):
        super(EEGNet, self).__init__()
        
        # We need to treat the 1D signal as a 2D image of shape (1, channels, time_steps)
        # So input should eventually be reshaped from (B, C, T) -> (B, 1, C, T) before feeding to Block 1
        
        # ----------------------------------------------------------------------
        # Block 1: Temporal Convolution
        # ----------------------------------------------------------------------
        # Learns frequency filters over time. The kernel size is (1, kernel_length).
        self.block1_conv1 = nn.Conv2d(1, F1, (1, kernel_length), padding=(0, kernel_length // 2), bias=False)
        self.block1_bn1 = nn.BatchNorm2d(F1)
        
        # Depthwise Convolution
        # Learns spatial filters (how different channels interact). Groups=F1 means we learn D spatial filters for each F1 temporal filter.
        self.block1_conv2 = nn.Conv2d(F1, F1 * D, (in_channels, 1), groups=F1, bias=False)
        self.block1_bn2 = nn.BatchNorm2d(F1 * D)
        self.block1_elu = nn.ELU()
        self.block1_pool = nn.AvgPool2d((1, 4))
        self.block1_dropout = nn.Dropout(dropout_rate)
        
        # ----------------------------------------------------------------------
        # Block 2: Separable Convolution
        # ----------------------------------------------------------------------
        # Depthwise across the time axis
        self.block2_conv1 = nn.Conv2d(F1 * D, F1 * D, (1, 16), groups=F1 * D, padding=(0, 16 // 2), bias=False)
        # Pointwise across the filter axis
        self.block2_conv2 = nn.Conv2d(F1 * D, F2, (1, 1), bias=False)
        self.block2_bn1 = nn.BatchNorm2d(F2)
        self.block2_elu = nn.ELU()
        self.block2_pool = nn.AvgPool2d((1, 8))
        self.block2_dropout = nn.Dropout(dropout_rate)
        
        # ----------------------------------------------------------------------
        # Classification Block
        # ----------------------------------------------------------------------
        # Dynamically determine the flattening size by passing a dummy tensor
        self.flatten = nn.Flatten()
        
        # A 2.5s signal at 256Hz = 640 time steps
        # Pooling block 1 reduces time by factor of 4 => 160
        # Pooling block 2 reduces time by factor of 8 => 20
        # Total output size = F2 * 20 = 16 * 20 = 320. We use AdaptiveAvgPool to guarantee this.
        self.adaptive_pool = nn.AdaptiveAvgPool2d((1, 20))
        
        self.dense = nn.Linear(F2 * 20, num_classes)
        
    def forward(self, x):
        # x arrives as shape: (batch_size, channels, time_steps)
        # We need it as (batch_size, 1, channels, time_steps) for 2D convolutions over Channels and Time separately
        x = x.unsqueeze(1)
        
        # Block 1
        x = self.block1_conv1(x)
        x = self.block1_bn1(x)
        x = self.block1_conv2(x)
        x = self.block1_bn2(x)
        x = self.block1_elu(x)
        x = self.block1_pool(x)
        x = self.block1_dropout(x)
        
        # Block 2
        x = self.block2_conv1(x)
        x = self.block2_conv2(x)
        x = self.block2_bn1(x)
        x = self.block2_elu(x)
        x = self.block2_pool(x)
        x = self.block2_dropout(x)
        
        # Classification
        # Use Adaptive Pool to fix the temporal length just in case the input crop time differs slightly
        x = self.adaptive_pool(x)
        x = self.flatten(x)
        out = self.dense(x)
        
        return out
