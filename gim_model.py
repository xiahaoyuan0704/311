"""Backward-compatible model exports."""

from gim_desktop.model import (
    FamDocument,
    FamProperty,
    FamSection,
    GimDocument,
    GimPackage,
    Layer,
    PropertyDocument,
    PropertySection,
    TextProperty,
    can_preview_as_text,
    flatten_layers,
    load_gim,
    load_gim_package,
    parse_obj_vertices_edges,
    parse_property_document,
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
    "TextProperty",
    "PropertySection",
    "PropertyDocument",
    "parse_property_document",
    "can_preview_as_text",
    "parse_obj_vertices_edges",
]
