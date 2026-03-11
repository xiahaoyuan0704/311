from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any
import zipfile


@dataclass
class FamProperty:
    key: str
    label: str
    value: str


@dataclass
class FamSection:
    name: str
    properties: list[FamProperty] = field(default_factory=list)


@dataclass
class FamDocument:
    sections: list[FamSection] = field(default_factory=list)

    @staticmethod
    def parse(text: str) -> "FamDocument":
        sections: list[FamSection] = []
        current = FamSection(name="默认")
        sections.append(current)

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]") and len(line) >= 2:
                current = FamSection(name=line[1:-1].strip() or "未命名")
                sections.append(current)
                continue

            parts = [part.strip() for part in line.split("=")]
            if len(parts) >= 3:
                key, label, value = parts[0], parts[1], "=".join(parts[2:])
            elif len(parts) == 2:
                key, label, value = parts[0], parts[0], parts[1]
            else:
                key = line
                label = line
                value = ""
            current.properties.append(FamProperty(key=key, label=label, value=value))

        # 移除空默认段
        if sections and sections[0].name == "默认" and not sections[0].properties:
            sections.pop(0)
        return FamDocument(sections=sections)

    def to_text(self) -> str:
        lines: list[str] = []
        for idx, section in enumerate(self.sections):
            if idx > 0:
                lines.append("")
            lines.append(f"[{section.name}]")
            for prop in section.properties:
                lines.append(f"{prop.key}={prop.label}={prop.value}")
        return "\n".join(lines) + "\n"


@dataclass
class GimPackage:
    source: str
    files: dict[str, bytes]

    def file_paths(self) -> list[str]:
        return sorted(self.files.keys())

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        return self.files[path].decode(encoding, errors="replace")

    def write_text(self, path: str, text: str, encoding: str = "utf-8") -> None:
        self.files[path] = text.encode(encoding)

    def fam_paths(self) -> list[str]:
        return [path for path in self.file_paths() if path.lower().endswith(".fam")]

    def save_as_gim_zip(self, output: str | Path) -> None:
        output = Path(output)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path, data in self.files.items():
                zf.writestr(path, data)


def load_gim_package(path: str | Path) -> GimPackage:
    path = Path(path)
    if path.is_dir():
        files: dict[str, bytes] = {}
        for item in path.rglob("*"):
            if item.is_file():
                rel = item.relative_to(path).as_posix()
                files[rel] = item.read_bytes()
        return GimPackage(source=str(path), files=files)

    if path.is_file():
        # 兼容旧版 JSON .gim
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and "layers" in payload:
                legacy_text = json.dumps(payload, ensure_ascii=False, indent=2)
                return GimPackage(source=str(path), files={"legacy_document.gim.json": legacy_text.encode("utf-8")})
        except Exception:
            pass

        with zipfile.ZipFile(path, "r") as zf:
            files = {name: zf.read(name) for name in zf.namelist() if not name.endswith("/")}
        return GimPackage(source=str(path), files=files)

    raise FileNotFoundError(path)


# ------- backward-compatible old API -------
@dataclass
class Layer:
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


@dataclass
class GimDocument:
    canvas_width: int = 1280
    canvas_height: int = 720
    background: str = "#1f1f1f"
    layers: list[Layer] = field(default_factory=list)


def load_gim(path: str | Path) -> GimDocument:
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    canvas = payload.get("canvas", {})
    return GimDocument(
        canvas_width=int(canvas.get("width", 1280)),
        canvas_height=int(canvas.get("height", 720)),
        background=str(canvas.get("background", "#1f1f1f")),
        layers=[],
    )


def save_gim(path: str | Path, document: GimDocument) -> None:
    path = Path(path)
    path.write_text(json.dumps({"canvas": {"width": document.canvas_width, "height": document.canvas_height, "background": document.background}, "layers": []}, ensure_ascii=False, indent=2), encoding="utf-8")


def flatten_layers(layers: list[Layer]) -> list[Layer]:
    return []
