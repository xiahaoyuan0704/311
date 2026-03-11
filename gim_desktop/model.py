from __future__ import annotations

from dataclasses import dataclass, field
import bz2
import gzip
import json
import lzma
from pathlib import Path
import re
import string
import zlib
import zipfile


TEXT_EXTENSIONS = {".fam", ".cbm", ".dev", ".phm", ".txt", ".ini", ".cfg", ".json", ".mod", ".xml", ".gim"}
PROPERTY_EXTENSIONS = {".fam", ".cbm", ".dev", ".phm", ".ini", ".cfg", ".txt", ".gim"}
COMMON_ENCODINGS = ("utf-8", "utf-8-sig", "gb18030", "gbk", "utf-16-le", "utf-16-be")


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

            if line.startswith("[") and line.endswith("]") and len(line) >= 3:
                name = line[1:-1].strip() or "未命名"
                current = PropertySection(name=name)
                sections.append(current)
                continue

            item = _parse_property_line(line)
            if item is not None:
                current.properties.append(item)

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
        text, _enc, score = decode_bytes_auto_scored(self.files[path])
        return text if score >= 0.55 else ""

    def write_text(self, path: str, text: str, encoding: str = "utf-8") -> None:
        self.files[path] = text.encode(encoding)

    def save_as_gim_zip(self, output: str | Path) -> None:
        output = Path(output)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path, data in self.files.items():
                zf.writestr(path, data)


def _safe_text_ratio(text: str) -> float:
    if not text:
        return 0.0
    safe_chars = set(string.printable) | set("电压等级工程标识系统编码调度名称设备参数中文值（）【】、：；，。-_/[]")
    ok = 0
    for ch in text:
        if ch == "�":
            continue
        if ch in safe_chars or ch.isalnum() or "\u4e00" <= ch <= "\u9fff":
            ok += 1
    penalty = text.count("�") / max(1, len(text))
    return max(0.0, ok / len(text) - penalty)


def _decompress_candidates(data: bytes) -> list[bytes]:
    out = [data]
    for fn in (gzip.decompress, zlib.decompress, bz2.decompress, lzma.decompress):
        try:
            raw = fn(data)
            if raw and raw not in out:
                out.append(raw)
        except Exception:
            pass
    return out


def _utf16le_strings(data: bytes) -> list[str]:
    # 提取 UTF-16LE 可打印字符串片段
    s = data.decode("utf-16-le", errors="ignore")
    return [x.strip() for x in re.split(r"[\x00\r\n]+", s) if len(x.strip()) >= 4]


def decode_bytes_auto_scored(data: bytes) -> tuple[str, str, float]:
    best = ("", "unknown", 0.0)
    for raw in _decompress_candidates(data):
        for enc in COMMON_ENCODINGS:
            try:
                text = raw.decode(enc)
            except UnicodeDecodeError:
                continue
            score = _safe_text_ratio(text[:6000])
            if score > best[2]:
                best = (text, enc, score)

    if best[0]:
        return best

    fallback = data.decode("utf-8", errors="replace")
    return fallback, "utf-8-replace", _safe_text_ratio(fallback[:6000])


def decode_bytes_auto(data: bytes) -> tuple[str, str]:
    text, enc, _score = decode_bytes_auto_scored(data)
    return text, enc


def _looks_text(data: bytes) -> bool:
    if not data:
        return True
    sample = data[:4096]
    null_ratio = sample.count(b"\x00") / len(sample)
    if null_ratio > 0.2:
        return False
    _t, _enc, score = decode_bytes_auto_scored(sample)
    return score > 0.70


def _parse_property_line(line: str) -> TextProperty | None:
    if "=" not in line or len(line) > 280:
        return None
    parts = [part.strip() for part in line.split("=")]
    if len(parts) >= 3:
        key, label, value = parts[0], parts[1], "=".join(parts[2:])
    elif len(parts) == 2:
        key, label, value = parts[0], parts[0], parts[1]
    else:
        return None

    if not key or len(key) > 120:
        return None
    if not re.search(r"[A-Za-z0-9\u4e00-\u9fff]", key):
        return None

    noisy = key + label + value
    if noisy.count("�") > 1:
        return None
    if _safe_text_ratio(noisy) < 0.55:
        return None

    return TextProperty(key=key, label=label or key, value=value)


def _extract_property_lines(text: str) -> str:
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().replace("\x00", "").replace("\ufeff", "")
        if not line:
            continue
        if line.startswith("[") and line.endswith("]") and 2 < len(line) <= 80:
            kept.append(line)
            continue
        if _parse_property_line(line) is not None:
            kept.append(line)
    return "\n".join(kept)


def _parse_property_candidates(text: str) -> PropertyDocument | None:
    cleaned = _extract_property_lines(text)
    if not cleaned:
        return None
    doc = PropertyDocument.parse(cleaned)
    return doc if doc.property_count() >= 2 else None


def parse_property_from_bytes(path: str, data: bytes) -> PropertyDocument | None:
    ext = Path(path).suffix.lower()

    text, _enc, score = decode_bytes_auto_scored(data)
    if score >= 0.65:
        by_text = parse_property_document(path, text)
        if by_text is not None:
            return by_text

    extracted = _extract_property_lines(text)
    if extracted:
        doc = _parse_property_candidates(extracted)
        if doc is not None:
            return doc

    # 尝试 UTF-16LE 字符串扫描（很多二进制容器会这样嵌入属性）
    utf16_hits = _utf16le_strings(data)
    if utf16_hits:
        doc = _parse_property_candidates("\n".join(utf16_hits))
        if doc is not None:
            return doc

    if ext in PROPERTY_EXTENSIONS and score >= 0.55:
        doc = _parse_property_candidates(text)
        if doc is not None:
            return doc

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
        return _parse_property_candidates(text)
    if "=" in text and ("[" in text and "]"):
        return _parse_property_candidates(text)
    return None


def can_preview_as_text(path: str, data: bytes) -> bool:
    ext = Path(path).suffix.lower()
    return ext in TEXT_EXTENSIONS and _looks_text(data) or _looks_text(data)


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
