"""Backward-compatible model exports."""

from gim_desktop.model import GimDocument, Layer, flatten_layers, load_gim, save_gim

__all__ = [
    "Layer",
    "GimDocument",
    "load_gim",
    "save_gim",
    "flatten_layers",
]
