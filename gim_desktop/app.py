from __future__ import annotations

import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gim_desktop.model import (
    GimPackage,
    PropertyDocument,
    can_preview_as_text,
    find_related_mod_path,
    load_gim_package,
    parse_obj_mesh,
    parse_obj_vertices_edges,
    parse_numeric_triplets,
    parse_points_from_binary,
    parse_property_document,
    parse_property_from_bytes,
)


class GimDesktopApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GIM 桌面解析与渲染工具")
        self.root.geometry("1380x860")

        self.package: GimPackage | None = None
        self.current_doc: PropertyDocument | None = None
        self.current_path: str | None = None

        self.status_var = tk.StringVar(value="请选择 .gim 文件或解压目录")
        self.render_mode_var = tk.StringVar(value="自动")
        self.key_var = tk.StringVar()
        self.label_var = tk.StringVar()
        self.value_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=8, pady=8)

        ttk.Button(toolbar, text="打开 .gim", command=self.open_gim_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="打开目录", command=self.open_gim_directory).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="保存当前属性文件", command=self.save_current_text).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="导出 .gim(zip)", command=self.export_gim_zip).pack(side=tk.LEFT, padx=4)
        ttk.Label(toolbar, text="渲染模式").pack(side=tk.LEFT, padx=(12, 2))
        mode_box = ttk.Combobox(
            toolbar,
            textvariable=self.render_mode_var,
            values=["自动", "3D线框", "3D点云"],
            width=12,
            state="readonly",
        )
        mode_box.pack(side=tk.LEFT, padx=4)
        mode_box.bind("<<ComboboxSelected>>", self.on_render_mode_changed)
        ttk.Label(toolbar, textvariable=self.status_var).pack(side=tk.RIGHT, padx=8)

        main = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        left = ttk.Labelframe(main, text="文件树")
        main.add(left, weight=3)
        self.tree = ttk.Treeview(left, show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_file)

        right = ttk.Notebook(main)
        main.add(right, weight=7)

        attr_tab = ttk.Frame(right)
        right.add(attr_tab, text="属性编辑")
        raw_tab = ttk.Frame(right)
        right.add(raw_tab, text="原始文本")
        render_tab = ttk.Frame(right)
        right.add(render_tab, text="模型渲染")

        self.prop_table = ttk.Treeview(attr_tab, columns=("key", "label", "value"), show="headings")
        self.prop_table.heading("key", text="属性键")
        self.prop_table.heading("label", text="显示名")
        self.prop_table.heading("value", text="属性值")
        self.prop_table.column("key", width=220)
        self.prop_table.column("label", width=260)
        self.prop_table.column("value", width=420)
        self.prop_table.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.prop_table.bind("<<TreeviewSelect>>", self.on_select_property)

        edit = ttk.Frame(attr_tab)
        edit.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(edit, text="键").grid(row=0, column=0, padx=4)
        ttk.Entry(edit, textvariable=self.key_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Label(edit, text="显示名").grid(row=0, column=2, padx=4)
        ttk.Entry(edit, textvariable=self.label_var).grid(row=0, column=3, sticky="ew", padx=4)
        ttk.Label(edit, text="值").grid(row=0, column=4, padx=4)
        ttk.Entry(edit, textvariable=self.value_var).grid(row=0, column=5, sticky="ew", padx=4)
        ttk.Button(edit, text="应用到选中行", command=self.apply_property_edit).grid(row=0, column=6, padx=4)
        edit.columnconfigure(1, weight=1)
        edit.columnconfigure(3, weight=1)
        edit.columnconfigure(5, weight=2)

        self.raw_text = tk.Text(raw_tab, wrap="none")
        self.raw_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.render_canvas = tk.Canvas(render_tab, bg="#10151c")
        self.render_canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def open_gim_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("GIM 文件", "*.gim"), ("所有文件", "*.*")])
        if path:
            self.load_source(path)

    def open_gim_directory(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.load_source(path)

    def load_source(self, path: str) -> None:
        try:
            self.package = load_gim_package(path)
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))
            return
        self.status_var.set(f"已加载: {path}")
        self.rebuild_tree()
        self.clear_detail()

    def rebuild_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        if not self.package:
            return
        existing: set[str] = set()
        focused_roots = {"CBM", "DEV", "MOD", "PHM"}
        allowed_ext = {".fam", ".cbm", ".dev", ".mod", ".phm"}

        file_paths = self.package.file_paths()
        if any(path.split("/", 1)[0].upper() in focused_roots for path in file_paths):
            file_paths = [
                path for path in file_paths
                if path.split("/", 1)[0].upper() in focused_roots
                and Path(path).suffix.lower() in allowed_ext
            ]

        for fp in file_paths:
            parent = ""
            current = ""
            for part in fp.split("/"):
                current = f"{current}/{part}" if current else part
                if current not in existing:
                    self.tree.insert(parent, tk.END, iid=current, text=part)
                    existing.add(current)
                parent = current

    def clear_detail(self) -> None:
        self.current_doc = None
        self.current_path = None
        self.prop_table.delete(*self.prop_table.get_children())
        self.raw_text.delete("1.0", tk.END)
        self.render_canvas.delete("all")

    def on_render_mode_changed(self, _event: tk.Event) -> None:
        if not self.package or not self.current_path:
            return
        data = self.package.read_bytes(self.current_path)
        text = self.package.read_text_auto(self.current_path) if can_preview_as_text(self.current_path, data) else ""
        self.render_for_selection(self.current_path, text, data)

    def on_select_file(self, _event: tk.Event) -> None:
        if not self.package:
            return
        selected = self.tree.selection()
        if not selected:
            return
        path = selected[0]
        if path not in self.package.files:
            return

        self.current_path = path
        data = self.package.read_bytes(path)
        self.prop_table.delete(*self.prop_table.get_children())

        if can_preview_as_text(path, data):
            text = self.package.read_text_auto(path)
            self.raw_text.delete("1.0", tk.END)
            self.raw_text.insert(tk.END, text)
            doc = parse_property_document(path, text)
            self.current_doc = doc
            if doc is not None:
                self.show_document(doc)
                self.status_var.set(f"已解析属性文件: {path}")
            else:
                self.current_doc = None
                self.status_var.set(f"已预览文本: {path}")
            self.render_for_selection(path, text, data)
        else:
            doc = parse_property_from_bytes(path, data)
            if doc is not None:
                self.current_doc = doc
                parsed_text = doc.to_text()
                self.raw_text.delete("1.0", tk.END)
                self.raw_text.insert(tk.END, parsed_text)
                self.show_document(doc)
                self.render_for_selection(path, parsed_text, data)
                self.status_var.set(f"已从二进制中提取属性: {path}")
            else:
                self.current_doc = None
                self.raw_text.delete("1.0", tk.END)
                self.raw_text.insert(tk.END, f"二进制文件，大小: {len(data)} 字节")
                self.render_for_selection(path, "", data)
                self.status_var.set(f"已加载二进制文件: {path}")

    def render_for_selection(self, path: str, text: str, data: bytes) -> None:
        ext = Path(path).suffix.lower()
        if ext == ".mod":
            self.render_mod(path, text, data)
            return

        if self.package is not None:
            related_mod = find_related_mod_path(path, self.package.file_paths())
            if related_mod is not None:
                mod_data = self.package.read_bytes(related_mod)
                mod_text = self.package.read_text_auto(related_mod) if can_preview_as_text(related_mod, mod_data) else ""
                self.render_mod(related_mod, mod_text, mod_data)
                self.status_var.set(f"已解析属性文件: {path}，并关联渲染模型: {related_mod}")
                return

        if text:
            self.render_from_path(path, text)
        else:
            self.render_from_binary(path, data)

    def show_document(self, doc: PropertyDocument) -> None:
        self.prop_table.delete(*self.prop_table.get_children())
        for sec in doc.sections:
            sec_id = self.prop_table.insert("", tk.END, values=(f"[{sec.name}]", "", ""))
            for i, item in enumerate(sec.properties):
                rid = f"{sec_id}:{i}"
                self.prop_table.insert("", tk.END, iid=rid, values=(item.key, item.label, item.value))

    def on_select_property(self, _event: tk.Event) -> None:
        row_ids = self.prop_table.selection()
        if not row_ids:
            return
        vals = self.prop_table.item(row_ids[0], "values")
        if not vals or vals[0].startswith("["):
            return
        self.key_var.set(vals[0])
        self.label_var.set(vals[1])
        self.value_var.set(vals[2])

    def apply_property_edit(self) -> None:
        if not self.package or not self.current_path or not self.current_doc:
            messagebox.showwarning("提示", "当前文件不是可编辑属性文件")
            return

        row_ids = self.prop_table.selection()
        if not row_ids:
            messagebox.showwarning("提示", "请先选中一个属性行")
            return

        row_id = row_ids[0]
        if ":" not in row_id:
            messagebox.showwarning("提示", "请选中具体属性，而不是分组标题")
            return

        sec_part, idx_part = row_id.split(":", 1)
        sec_name = self.prop_table.item(sec_part, "values")[0].strip("[]")
        idx = int(idx_part)
        sec = next((s for s in self.current_doc.sections if s.name == sec_name), None)
        if sec is None or idx >= len(sec.properties):
            return

        prop = sec.properties[idx]
        prop.key = self.key_var.get().strip() or prop.key
        prop.label = self.label_var.get().strip() or prop.label
        prop.value = self.value_var.get().strip()

        self.show_document(self.current_doc)
        new_text = self.current_doc.to_text()
        self.package.write_text(self.current_path, new_text)
        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert(tk.END, new_text)
        self.render_for_selection(self.current_path, new_text, self.package.read_bytes(self.current_path))
        self.status_var.set(f"已修改并写回: {self.current_path}")

    def save_current_text(self) -> None:
        if not self.package or not self.current_path:
            messagebox.showwarning("提示", "请先选择文件")
            return
        out = filedialog.asksaveasfilename(initialfile=Path(self.current_path).name)
        if not out:
            return
        Path(out).write_bytes(self.package.read_bytes(self.current_path))
        self.status_var.set(f"已保存: {out}")

    def export_gim_zip(self) -> None:
        if not self.package:
            messagebox.showwarning("提示", "请先打开 .gim 或目录")
            return
        out = filedialog.asksaveasfilename(defaultextension=".gim", filetypes=[("GIM 文件", "*.gim")])
        if not out:
            return
        self.package.save_as_gim_zip(out)
        self.status_var.set(f"已导出: {out}")

    def render_from_path(self, path: str, text: str) -> None:
        self.render_canvas.delete("all")
        ext = Path(path).suffix.lower()
        if ext == ".mod":
            self._render_mod_text(text)
            return

        doc = parse_property_document(path, text)
        if doc is not None:
            self._render_property_style(doc)
            return

        self.render_canvas.create_text(30, 30, anchor=tk.NW, fill="#cfd8e3", text="该文本文件无可渲染模型，显示原始内容。")

    def render_from_binary(self, path: str, data: bytes) -> None:
        self.render_canvas.delete("all")
        self.render_canvas.create_text(30, 30, anchor=tk.NW, fill="#cfd8e3", text=f"{Path(path).name} 为二进制文件，暂不支持直接渲染。")
        self.render_canvas.create_rectangle(40, 80, 260, 220, outline="#4d90fe", width=2)
        self.render_canvas.create_text(150, 150, fill="#9fc1ff", text="BINARY MODEL")
        self.render_canvas.create_text(150, 180, fill="#9aa9bf", text=f"{len(data)} bytes")

    def _render_property_style(self, doc: PropertyDocument) -> None:
        flat = doc.to_flat_dict()
        voltage = flat.get("VoltageLevel") or flat.get("电压等级") or "10"
        name = flat.get("工程中名称") or flat.get("name") or flat.get("设备名称") or "设备"
        code = flat.get("电网工程标识系统编码") or flat.get("调度编码") or "N/A"
        canvas_w = max(self.render_canvas.winfo_width(), 960)
        canvas_h = max(self.render_canvas.winfo_height(), 560)
        self.render_canvas.create_rectangle(40, 40, canvas_w - 40, canvas_h - 40, fill="#121821", outline="#355a83", width=2)
        self.render_canvas.create_text(70, 70, anchor=tk.NW, fill="#f5f7fa", font=("Arial", 16, "bold"), text=name)
        self.render_canvas.create_text(70, 102, anchor=tk.NW, fill="#b8c5d8", text=f"编码: {code}")
        self.render_canvas.create_text(70, 126, anchor=tk.NW, fill="#ffd66b", text=f"电压等级: {voltage} kV")

        size_factor = max(0.8, min(1.8, float(voltage) / 10.0)) if str(voltage).replace(".", "", 1).isdigit() else 1.0
        self._render_procedural_equipment(size_factor=size_factor)
        self.render_canvas.create_text(70, canvas_h - 70, anchor=tk.NW, fill="#a7b7cd", text="说明：属性文件暂无可用MOD时，采用立体3D设备占位渲染。")

    def _build_cylinder(
        self,
        radius: float,
        height: float,
        center_x: float,
        center_y: float,
        center_z: float,
        segments: int = 24,
    ) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
        verts: list[tuple[float, float, float]] = []
        faces: list[tuple[int, int, int]] = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = center_x + radius * math.cos(angle)
            z = center_z + radius * math.sin(angle)
            verts.append((x, center_y - height / 2, z))
            verts.append((x, center_y + height / 2, z))

        for i in range(segments):
            a = 2 * i
            b = 2 * ((i + 1) % segments)
            faces.append((a, b, a + 1))
            faces.append((a + 1, b, b + 1))

        top_center = len(verts)
        verts.append((center_x, center_y + height / 2, center_z))
        bottom_center = len(verts)
        verts.append((center_x, center_y - height / 2, center_z))
        for i in range(segments):
            a = 2 * i
            b = 2 * ((i + 1) % segments)
            faces.append((top_center, a + 1, b + 1))
            faces.append((bottom_center, b, a))
        return verts, faces

    def _render_procedural_equipment(self, size_factor: float) -> None:
        mesh_vertices: list[tuple[float, float, float]] = []
        mesh_faces: list[tuple[int, int, int]] = []

        def append_mesh(
            verts: list[tuple[float, float, float]],
            faces: list[tuple[int, int, int]],
        ) -> None:
            base = len(mesh_vertices)
            mesh_vertices.extend(verts)
            mesh_faces.extend((a + base, b + base, c + base) for a, b, c in faces)

        # 底座
        base_box = [
            (-25, -180, -25), (25, -180, -25), (25, -160, -25), (-25, -160, -25),
            (-25, -180, 25), (25, -180, 25), (25, -160, 25), (-25, -160, 25),
        ]
        base_faces = [
            (0, 1, 2), (0, 2, 3), (4, 7, 6), (4, 6, 5),
            (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2),
            (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0),
        ]
        append_mesh([(x * size_factor, y * size_factor, z * size_factor) for x, y, z in base_box], base_faces)

        # 立柱
        pole_v, pole_f = self._build_cylinder(
            radius=7 * size_factor,
            height=130 * size_factor,
            center_x=0,
            center_y=-95 * size_factor,
            center_z=0,
            segments=20,
        )
        append_mesh(pole_v, pole_f)

        # 螺纹段（通过多段细圆柱模拟）
        for i in range(16):
            y = (-18 + i * 5) * size_factor
            ring_v, ring_f = self._build_cylinder(
                radius=(12 + (i % 2) * 1.8) * size_factor,
                height=3.2 * size_factor,
                center_x=0,
                center_y=y,
                center_z=0,
                segments=18,
            )
            append_mesh(ring_v, ring_f)

        # 顶部罐体
        tank_v, tank_f = self._build_cylinder(
            radius=20 * size_factor,
            height=35 * size_factor,
            center_x=0,
            center_y=52 * size_factor,
            center_z=0,
            segments=26,
        )
        append_mesh(tank_v, tank_f)

        self._render_mesh(mesh_vertices, mesh_faces, base_color="#d7dde2", line_color="#252a2f")
        self._draw_axis_gizmo()

    def _draw_axis_gizmo(self) -> None:
        origin = (0.0, -190.0, 0.0)
        axes = [
            ((32.0, -190.0, 0.0), "#ff5b5b"),
            ((0.0, -158.0, 0.0), "#4dfc5f"),
            ((0.0, -190.0, 32.0), "#5070ff"),
        ]
        ox, oy = self._project_point(*origin)
        for endpoint, color in axes:
            ex, ey = self._project_point(*endpoint)
            self.render_canvas.create_line(ox + 110, oy + 510, ex + 110, ey + 510, fill=color, width=3, arrow=tk.LAST)

    @staticmethod
    def _shade_color(base_hex: str, factor: float) -> str:
        factor = max(0.25, min(1.4, factor))
        r = int(base_hex[1:3], 16)
        g = int(base_hex[3:5], 16)
        b = int(base_hex[5:7], 16)
        rr = max(0, min(255, int(r * factor)))
        gg = max(0, min(255, int(g * factor)))
        bb = max(0, min(255, int(b * factor)))
        return f"#{rr:02x}{gg:02x}{bb:02x}"

    @staticmethod
    def _project_point(x: float, y: float, z: float) -> tuple[float, float]:
        yaw = math.radians(35)
        pitch = math.radians(25)
        cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
        cos_pitch, sin_pitch = math.cos(pitch), math.sin(pitch)

        x1 = x * cos_yaw + z * sin_yaw
        z1 = -x * sin_yaw + z * cos_yaw
        y1 = y * cos_pitch - z1 * sin_pitch
        return x1, y1

    def _project_points_fit(self, points: list[tuple[float, float, float]]) -> tuple[list[tuple[float, float]], float]:
        projected = [self._project_point(x, y, z) for x, y, z in points]
        xs = [p[0] for p in projected]
        ys = [p[1] for p in projected]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w = max(1e-6, max_x - min_x)
        h = max(1e-6, max_y - min_y)
        canvas_w = max(self.render_canvas.winfo_width(), 900)
        canvas_h = max(self.render_canvas.winfo_height(), 600)
        scale = min((canvas_w - 120) / w, (canvas_h - 120) / h)

        fitted: list[tuple[float, float]] = []
        for px, py in projected:
            sx = 60 + (px - min_x) * scale
            sy = 60 + (py - min_y) * scale
            fitted.append((sx, sy))
        return fitted, scale

    def _render_mesh(
        self,
        vertices: list[tuple[float, float, float]],
        faces: list[tuple[int, int, int]],
        base_color: str = "#d9dee2",
        line_color: str = "#2a2f34",
    ) -> bool:
        if not vertices or not faces:
            return False
        projected, _scale = self._project_points_fit(vertices)
        polys: list[tuple[float, list[float], str]] = []
        light = (0.45, 0.72, 0.52)

        for a, b, c in faces:
            if a >= len(vertices) or b >= len(vertices) or c >= len(vertices):
                continue
            ax, ay, az = vertices[a]
            bx, by, bz = vertices[b]
            cx, cy, cz = vertices[c]

            ux, uy, uz = bx - ax, by - ay, bz - az
            vx, vy, vz = cx - ax, cy - ay, cz - az
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            norm = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nx, ny, nz = nx / norm, ny / norm, nz / norm

            shade = 0.55 + max(0.0, nx * light[0] + ny * light[1] + nz * light[2]) * 0.8
            color = self._shade_color(base_color, shade)
            depth = (az + bz + cz) / 3
            pa = projected[a]
            pb = projected[b]
            pc = projected[c]
            polys.append((depth, [pa[0], pa[1], pb[0], pb[1], pc[0], pc[1]], color))

        polys.sort(key=lambda item: item[0])
        for _depth, pts, color in polys:
            self.render_canvas.create_polygon(pts, fill=color, outline=line_color, width=1)
        return True

    def _render_mod_text(self, text: str) -> bool:
        mode = self.render_mode_var.get()
        mesh_vertices, mesh_faces = parse_obj_mesh(text)
        if mesh_vertices and mode == "3D点云":
            self._render_points_cloud(mesh_vertices, "OBJ 顶点点云渲染")
            return True
        if mesh_vertices and mesh_faces and mode in ("自动", "3D线框"):
            if self._render_mesh(mesh_vertices, mesh_faces):
                self.render_canvas.create_text(
                    20,
                    20,
                    anchor=tk.NW,
                    fill="#d7e4f5",
                    text=f"OBJ 3D实体渲染: 顶点{len(mesh_vertices)} 面{len(mesh_faces)}",
                )
                return True

        vertices, edges = parse_obj_vertices_edges(text)
        if not vertices or not edges:
            points = parse_numeric_triplets(text)
            if points:
                self._render_points_cloud(points, "MOD 数值点云渲染")
                return True
            return False

        projected, scale = self._project_points_fit(vertices)

        for a, b in edges:
            if a < len(projected) and b < len(projected):
                x1, y1 = projected[a]
                x2, y2 = projected[b]
                width = 2 if mode == "3D线框" else 1
                color = "#8ad4ff" if mode == "3D线框" else "#7fc0ff"
                self.render_canvas.create_line(x1, y1, x2, y2, fill=color, width=width)

        self.render_canvas.create_text(
            20,
            20,
            anchor=tk.NW,
            fill="#d7e4f5",
            text=f"OBJ 3D线框渲染: 顶点{len(vertices)} 边{len(edges)} 缩放{scale:.2f}",
        )
        return True

    def _render_points_cloud(self, points: list[tuple[float, float, float]], title: str) -> None:
        projected, _scale = self._project_points_fit(points)

        step = max(1, len(points) // 3000)
        for idx in range(0, len(points), step):
            sx, sy = projected[idx]
            self.render_canvas.create_oval(sx - 1, sy - 1, sx + 1, sy + 1, outline="", fill="#7fc0ff")

        self.render_canvas.create_text(20, 20, anchor=tk.NW, fill="#d7e4f5", text=f"{title}: 点数{len(points)}")

    def render_mod(self, path: str, text: str, data: bytes) -> None:
        self.render_canvas.delete("all")
        if text:
            if self._render_mod_text(text):
                return

        pts = parse_points_from_binary(data)
        if pts:
            self._render_points_cloud(pts, "MOD 二进制点云渲染")
        else:
            self.render_canvas.create_text(
                30,
                30,
                anchor=tk.NW,
                fill="#cfd8e3",
                text=".mod 已打开，未识别出 OBJ/数值点云，显示二进制占位预览。",
            )
            self.render_from_binary(path, data)


def run() -> None:
    root = tk.Tk()
    GimDesktopApp(root)
    root.mainloop()
