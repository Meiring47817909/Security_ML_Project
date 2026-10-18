"""MLP model for intrusion detection."""
import torch
import torch.nn as nn
from torch import Tensor


class MLP(nn.Module):
    """Multi-layer perceptron for binary intrusion detection."""

    def __init__(self, in_features: int = 17):
        """Initialize the MLP with the specified input features.

        Args:
            in_features: Number of input features (default 17).
        """
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(self, x: Tensor) -> Tensor:
        """Forward pass through the network.

        Args:
            x: Input tensor of shape [B, 17] where B is batch size.

        Returns:
            Logits of shape [B] (squeezed from [B, 1]).
        """
        out = self.net(x)
        return out.squeeze(-1)
