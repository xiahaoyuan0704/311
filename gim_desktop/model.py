from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import zipfile


TEXT_EXTENSIONS = {".fam", ".cbm", ".dev", ".phm", ".txt", ".ini", ".cfg", ".json", ".mod", ".xml", ".gim"}
PROPERTY_EXTENSIONS = {".fam", ".cbm", ".dev", ".phm", ".ini", ".cfg", ".txt", ".gim"}


@dataclass
class TextProperty:
    key: str
    label: str
    value: str


@dataclass
class PropertySection:
    name: str
    properties: list[TextProperty] = field(default_factory=list)


@dataclass
class PropertyDocument:
    sections: list[PropertySection] = field(default_factory=list)

    @staticmethod
    def parse(text: str) -> "PropertyDocument":
        sections: list[PropertySection] = []
        current = PropertySection(name="默认")
        sections.append(current)

        for raw in text.splitlines():
            line = raw.strip().replace("\ufeff", "")
            if not line or line.startswith("#") or line.startswith(";"):
                continue

            if line.startswith("[") and line.endswith("]") and len(line) >= 2:
                current = PropertySection(name=line[1:-1].strip() or "未命名")
                sections.append(current)
                continue

            parts = [part.strip() for part in line.split("=")]
            if len(parts) >= 3:
                key, label, value = parts[0], parts[1], "=".join(parts[2:])
            elif len(parts) == 2:
                key, label, value = parts[0], parts[0], parts[1]
            else:
                key, label, value = line, line, ""
            current.properties.append(TextProperty(key=key, label=label, value=value))

        if sections and sections[0].name == "默认" and not sections[0].properties:
            sections.pop(0)
        return PropertyDocument(sections=sections)

    def to_text(self) -> str:
        lines: list[str] = []
        for idx, section in enumerate(self.sections):
            if idx > 0:
                lines.append("")
            lines.append(f"[{section.name}]")
            for prop in section.properties:
                lines.append(f"{prop.key}={prop.label}={prop.value}")
        return "\n".join(lines) + "\n"

    def property_count(self) -> int:
        return sum(len(sec.properties) for sec in self.sections)

    def to_flat_dict(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for section in self.sections:
            for prop in section.properties:
                out[prop.key] = prop.value
        return out


@dataclass
class GimPackage:
    source: str
    files: dict[str, bytes]

    def file_paths(self) -> list[str]:
        return sorted(self.files.keys())

    def read_bytes(self, path: str) -> bytes:
        return self.files[path]

    def read_text_auto(self, path: str) -> str:
        return decode_bytes_auto(self.files[path])

    def write_text(self, path: str, text: str, encoding: str = "utf-8") -> None:
        self.files[path] = text.encode(encoding)

    def save_as_gim_zip(self, output: str | Path) -> None:
        output = Path(output)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path, data in self.files.items():
                zf.writestr(path, data)


def decode_bytes_auto(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk", "utf-16", "latin1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _looks_text(data: bytes) -> bool:
    if not data:
        return True
    sample = data[:4096]
    null_ratio = sample.count(b"\x00") / len(sample)
    if null_ratio > 0.2:
        return False
    text_like = sum(32 <= b < 127 or b in (9, 10, 13) for b in sample)
    return text_like / len(sample) > 0.45


def _extract_printable_lines(data: bytes) -> str:
    text = decode_bytes_auto(data)
    lines = []
    for line in text.splitlines():
        clean = line.strip().replace("\x00", "")
        if not clean:
            continue
        if any(ch.isalnum() for ch in clean) and ("=" in clean or ("[" in clean and "]" in clean)):
            lines.append(clean)
    return "\n".join(lines)


def _parse_property_candidates(text: str) -> PropertyDocument | None:
    doc = PropertyDocument.parse(text)
    if doc.property_count() >= 2:
        return doc
    return None


def parse_property_from_bytes(path: str, data: bytes) -> PropertyDocument | None:
    text = decode_bytes_auto(data)
    by_text = parse_property_document(path, text)
    if by_text is not None and by_text.property_count() > 0:
        return by_text

    guessed = _extract_printable_lines(data)
    if guessed:
        return _parse_property_candidates(guessed)
    return None


def load_gim_package(path: str | Path) -> GimPackage:
    path = Path(path)
    if path.is_dir():
        files: dict[str, bytes] = {}
        for item in path.rglob("*"):
            if item.is_file():
                files[item.relative_to(path).as_posix()] = item.read_bytes()
        return GimPackage(source=str(path), files=files)

    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and "layers" in payload:
                legacy = json.dumps(payload, ensure_ascii=False, indent=2)
                return GimPackage(source=str(path), files={"legacy_document.gim.json": legacy.encode("utf-8")})
        except Exception:
            pass

        try:
            with zipfile.ZipFile(path, "r") as zf:
                files = {name: zf.read(name) for name in zf.namelist() if not name.endswith("/")}
            return GimPackage(source=str(path), files=files)
        except zipfile.BadZipFile:
            return GimPackage(source=str(path), files={path.name: path.read_bytes()})

    raise FileNotFoundError(f"路径不存在或不可读取: {path}")


def parse_property_document(path: str, text: str) -> PropertyDocument | None:
    ext = Path(path).suffix.lower()
    if ext in PROPERTY_EXTENSIONS:
        return PropertyDocument.parse(text)
    if "=" in text and ("[" in text and "]" in text):
        return PropertyDocument.parse(text)
    return None


def can_preview_as_text(path: str, data: bytes) -> bool:
    ext = Path(path).suffix.lower()
    return ext in TEXT_EXTENSIONS or _looks_text(data)


def parse_obj_vertices_edges(text: str) -> tuple[list[tuple[float, float, float]], list[tuple[int, int]]]:
    vertices: list[tuple[float, float, float]] = []
    edges: set[tuple[int, int]] = set()

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("v "):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except ValueError:
                    continue
        elif line.startswith("f "):
            parts = line.split()[1:]
            indices: list[int] = []
            for p in parts:
                token = p.split("/")[0]
                try:
                    idx = int(token)
                except ValueError:
                    continue
                if idx > 0:
                    indices.append(idx - 1)
            for i in range(len(indices)):
                a = indices[i]
                b = indices[(i + 1) % len(indices)]
                if a != b:
                    edges.add(tuple(sorted((a, b))))

    return vertices, sorted(edges)


FamProperty = TextProperty
FamSection = PropertySection
FamDocument = PropertyDocument


@dataclass
class Layer:
    id: str
    name: str


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
    payload = {
        "canvas": {
            "width": document.canvas_width,
            "height": document.canvas_height,
            "background": document.background,
        },
        "layers": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def flatten_layers(layers: list[Layer]) -> list[Layer]:
    return []
