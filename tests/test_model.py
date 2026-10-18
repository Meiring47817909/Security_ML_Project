import torch

from intrusion.model import MLP


def test_forward_shape():
    m = MLP().eval()
    assert m(torch.randn(5, 17)).shape == (5,)


def test_architecture():
    kinds = [type(l).__name__ for l in MLP().net]
    assert kinds == ["Linear", "BatchNorm1d", "ReLU", "Dropout", "Linear", "BatchNorm1d", "ReLU", "Dropout", "Linear"]
    assert MLP().net[0].in_features == 17 and MLP().net[-1].out_features == 1
