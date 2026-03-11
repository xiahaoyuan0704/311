"""Backward-compatible model exports."""

from gim_desktop.model import (
    FamDocument,
    FamProperty,
    FamSection,
    GimDocument,
    GimPackage,
    Layer,
    flatten_layers,
    load_gim,
    load_gim_package,
    save_gim,
)

__all__ = [
    "Layer",
    "GimDocument",
    "load_gim",
    "save_gim",
    "flatten_layers",
    "FamProperty",
    "FamSection",
    "FamDocument",
    "GimPackage",
    "load_gim_package",
]
