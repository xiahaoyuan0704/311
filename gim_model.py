from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any


@dataclass
class Layer:
    """A hierarchical layer node parsed from a .gim document."""

    id: str
    name: str
    type: str = "group"
    visible: bool = True
    opacity: float = 1.0
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0
    fill: str = "#808080"
    text: str = ""
    font_size: int = 14
    children: list["Layer"] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Layer":
        children_data = data.get("children", []) or []
        children = [Layer.from_dict(item) for item in children_data]
        return Layer(
            id=str(data.get("id", "")),
            name=str(data.get("name", "Unnamed Layer")),
            type=str(data.get("type", "group")),
            visible=bool(data.get("visible", True)),
            opacity=float(data.get("opacity", 1.0)),
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            width=float(data.get("width", 0.0)),
            height=float(data.get("height", 0.0)),
            rotation=float(data.get("rotation", 0.0)),
            fill=str(data.get("fill", "#808080")),
            text=str(data.get("text", "")),
            font_size=int(data.get("font_size", 14)),
            children=children,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "visible": self.visible,
            "opacity": self.opacity,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "fill": self.fill,
            "text": self.text,
            "font_size": self.font_size,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class GimDocument:
    canvas_width: int = 1280
    canvas_height: int = 720
    background: str = "#1f1f1f"
    layers: list[Layer] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "GimDocument":
        canvas = data.get("canvas", {})
        layer_data = data.get("layers", []) or []
        layers = [Layer.from_dict(item) for item in layer_data]
        return GimDocument(
            canvas_width=int(canvas.get("width", 1280)),
            canvas_height=int(canvas.get("height", 720)),
            background=str(canvas.get("background", "#1f1f1f")),
            layers=layers,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "canvas": {
                "width": self.canvas_width,
                "height": self.canvas_height,
                "background": self.background,
            },
            "layers": [layer.to_dict() for layer in self.layers],
        }


def load_gim(path: str | Path) -> GimDocument:
    """Load a .gim file in JSON format."""

    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("Invalid .gim file: root must be an object")
    return GimDocument.from_dict(payload)


def save_gim(path: str | Path, document: GimDocument) -> None:
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(document.to_dict(), f, ensure_ascii=False, indent=2)


def flatten_layers(layers: list[Layer]) -> list[Layer]:
    out: list[Layer] = []

    def walk(items: list[Layer]) -> None:
        for layer in items:
            out.append(layer)
            if layer.children:
                walk(layer.children)

    walk(layers)
    return out
