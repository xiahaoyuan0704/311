from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gim_desktop.model import (
    GimPackage,
    PropertyDocument,
    can_preview_as_text,
    load_gim_package,
    parse_obj_vertices_edges,
    parse_property_document,
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
        for fp in self.package.file_paths():
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
            text = self.package.read_text(path)
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
            self.render_from_path(path, text)
        else:
            self.current_doc = None
            self.raw_text.delete("1.0", tk.END)
            self.raw_text.insert(tk.END, f"二进制文件，大小: {len(data)} 字节")
            self.render_from_binary(path, data)
            self.status_var.set(f"已加载二进制文件: {path}")

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
        self.render_from_path(self.current_path, new_text)
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

        self.render_canvas.create_rectangle(70, 80, 980, 520, fill="#16212d", outline="#355a83", width=2)
        self.render_canvas.create_text(90, 105, anchor=tk.NW, fill="#f5f7fa", font=("Arial", 16, "bold"), text=name)
        self.render_canvas.create_text(90, 135, anchor=tk.NW, fill="#b8c5d8", text=f"编码: {code}")
        self.render_canvas.create_text(90, 160, anchor=tk.NW, fill="#ffd66b", text=f"电压等级: {voltage} kV")

        self.render_canvas.create_line(120, 320, 900, 320, fill="#ffcc33", width=8)
        for x in (220, 380, 540, 700, 860):
            self.render_canvas.create_oval(x - 22, 298, x + 22, 342, fill="#2f88ff", outline="")
            self.render_canvas.create_line(x, 342, x, 430, fill="#80b6ff", width=3)
            self.render_canvas.create_rectangle(x - 34, 430, x + 34, 470, fill="#204a7a", outline="#77a9e8")

        self.render_canvas.create_text(90, 540, anchor=tk.NW, fill="#a7b7cd", text="说明：这是根据属性生成的设备示意渲染，用于桌面查看模型样式。")

    def _render_mod_text(self, text: str) -> None:
        vertices, edges = parse_obj_vertices_edges(text)
        if not vertices or not edges:
            self.render_canvas.create_text(
                30,
                30,
                anchor=tk.NW,
                fill="#cfd8e3",
                text=".mod 已打开，但不是 OBJ 网格文本；已回退到通用渲染。",
            )
            self.render_canvas.create_rectangle(120, 120, 560, 360, outline="#4d90fe", width=2)
            self.render_canvas.create_text(340, 240, fill="#8fb4ff", text="MOD PREVIEW")
            return

        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w = max(1e-6, max_x - min_x)
        h = max(1e-6, max_y - min_y)
        canvas_w = max(self.render_canvas.winfo_width(), 900)
        canvas_h = max(self.render_canvas.winfo_height(), 600)
        scale = min((canvas_w - 120) / w, (canvas_h - 120) / h)

        projected: list[tuple[float, float]] = []
        for x, y, _z in vertices:
            sx = 60 + (x - min_x) * scale
            sy = 60 + (y - min_y) * scale
            projected.append((sx, sy))

        for a, b in edges:
            if a < len(projected) and b < len(projected):
                x1, y1 = projected[a]
                x2, y2 = projected[b]
                self.render_canvas.create_line(x1, y1, x2, y2, fill="#7fc0ff", width=1)

        self.render_canvas.create_text(20, 20, anchor=tk.NW, fill="#d7e4f5", text=f"OBJ样式渲染: 顶点{len(vertices)} 边{len(edges)}")


def run() -> None:
    root = tk.Tk()
    GimDesktopApp(root)
    root.mainloop()
