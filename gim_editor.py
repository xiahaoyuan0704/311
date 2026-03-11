from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from gim_model import GimDocument, Layer, flatten_layers, load_gim, save_gim


class GimEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GIM Desktop Editor")
        self.current_file: Path | None = None
        self.document = GimDocument()
        self.layer_map: dict[str, Layer] = {}
        self.selected_layer_id: str | None = None

        self._build_ui()
        self._bind_events()
        self._new_document()

    def _build_ui(self) -> None:
        self.root.geometry("1280x800")

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=8, pady=8)

        ttk.Button(toolbar, text="新建", command=self._new_document).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="打开 .gim", command=self._open_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="保存", command=self._save_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="另存为", command=self._save_as).pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="准备就绪")
        ttk.Label(toolbar, textvariable=self.status_var).pack(side=tk.RIGHT, padx=8)

        body = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        left_frame = ttk.Labelframe(body, text="层级")
        body.add(left_frame, weight=2)

        self.layer_tree = ttk.Treeview(left_frame, columns=("type",), show="tree headings")
        self.layer_tree.heading("#0", text="名称")
        self.layer_tree.heading("type", text="类型")
        self.layer_tree.column("#0", width=220)
        self.layer_tree.column("type", width=100, anchor=tk.CENTER)
        self.layer_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        center_frame = ttk.Labelframe(body, text="桌面渲染")
        body.add(center_frame, weight=5)

        self.canvas = tk.Canvas(center_frame, bg="#1f1f1f")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        right_frame = ttk.Labelframe(body, text="属性")
        body.add(right_frame, weight=3)

        self.form_vars: dict[str, tk.StringVar] = {
            "name": tk.StringVar(),
            "type": tk.StringVar(),
            "visible": tk.StringVar(),
            "opacity": tk.StringVar(),
            "x": tk.StringVar(),
            "y": tk.StringVar(),
            "width": tk.StringVar(),
            "height": tk.StringVar(),
            "rotation": tk.StringVar(),
            "fill": tk.StringVar(),
            "text": tk.StringVar(),
            "font_size": tk.StringVar(),
        }

        fields = [
            ("name", "名称"),
            ("type", "类型"),
            ("visible", "可见(true/false)"),
            ("opacity", "透明度(0-1)"),
            ("x", "X"),
            ("y", "Y"),
            ("width", "宽"),
            ("height", "高"),
            ("rotation", "旋转"),
            ("fill", "颜色"),
            ("text", "文本"),
            ("font_size", "字号"),
        ]

        form = ttk.Frame(right_frame)
        form.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        for row, (key, label) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=2)
            entry = ttk.Entry(form, textvariable=self.form_vars[key])
            entry.grid(row=row, column=1, sticky="ew", pady=2)

        form.columnconfigure(1, weight=1)
        ttk.Button(form, text="应用到当前层", command=self._apply_properties).grid(
            row=len(fields), column=0, columnspan=2, pady=10, sticky="ew"
        )

    def _bind_events(self) -> None:
        self.layer_tree.bind("<<TreeviewSelect>>", self._on_layer_selected)

    def _new_document(self) -> None:
        self.current_file = None
        self.document = GimDocument(
            canvas_width=960,
            canvas_height=540,
            background="#202020",
            layers=[
                Layer(
                    id="layer-1",
                    name="背景矩形",
                    type="rect",
                    x=50,
                    y=50,
                    width=300,
                    height=180,
                    fill="#2b8cff",
                ),
                Layer(
                    id="layer-2",
                    name="标题文字",
                    type="text",
                    x=120,
                    y=140,
                    fill="#ffffff",
                    text="Hello GIM",
                    font_size=28,
                ),
            ],
        )
        self._refresh_all("已创建新文档")

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("GIM 文件", "*.gim"), ("JSON", "*.json")])
        if not path:
            return
        try:
            self.document = load_gim(path)
            self.current_file = Path(path)
            self._refresh_all(f"已打开: {self.current_file.name}")
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    def _save_file(self) -> None:
        if self.current_file is None:
            self._save_as()
            return
        save_gim(self.current_file, self.document)
        self.status_var.set(f"已保存: {self.current_file}")

    def _save_as(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".gim", filetypes=[("GIM 文件", "*.gim")])
        if not path:
            return
        self.current_file = Path(path)
        self._save_file()

    def _refresh_all(self, status: str = "") -> None:
        self.status_var.set(status or "完成")
        self._rebuild_layer_tree()
        self._render_canvas()
        self._clear_property_form()

    def _rebuild_layer_tree(self) -> None:
        self.layer_map = {layer.id: layer for layer in flatten_layers(self.document.layers)}
        self.layer_tree.delete(*self.layer_tree.get_children())

        def add_layer_nodes(parent: str, layers: list[Layer]) -> None:
            for layer in layers:
                item_id = self.layer_tree.insert(parent, tk.END, iid=layer.id, text=layer.name, values=(layer.type,))
                if layer.children:
                    add_layer_nodes(item_id, layer.children)

        add_layer_nodes("", self.document.layers)

    def _render_canvas(self) -> None:
        self.canvas.delete("all")
        self.canvas.configure(bg=self.document.background)

        def draw_layer(layer: Layer) -> None:
            if not layer.visible:
                return
            if layer.type == "rect":
                self.canvas.create_rectangle(
                    layer.x,
                    layer.y,
                    layer.x + layer.width,
                    layer.y + layer.height,
                    fill=layer.fill,
                    outline="",
                    stipple="gray50" if layer.opacity < 1 else "",
                )
            elif layer.type == "text":
                self.canvas.create_text(
                    layer.x,
                    layer.y,
                    text=layer.text,
                    fill=layer.fill,
                    font=("Arial", max(1, layer.font_size)),
                    anchor=tk.NW,
                )
            for child in layer.children:
                draw_layer(child)

        for item in self.document.layers:
            draw_layer(item)

    def _on_layer_selected(self, _event: tk.Event) -> None:
        selected = self.layer_tree.selection()
        if not selected:
            return
        layer_id = selected[0]
        layer = self.layer_map.get(layer_id)
        if layer is None:
            return
        self.selected_layer_id = layer_id
        self._populate_form(layer)

    def _populate_form(self, layer: Layer) -> None:
        self.form_vars["name"].set(layer.name)
        self.form_vars["type"].set(layer.type)
        self.form_vars["visible"].set(str(layer.visible).lower())
        self.form_vars["opacity"].set(str(layer.opacity))
        self.form_vars["x"].set(str(layer.x))
        self.form_vars["y"].set(str(layer.y))
        self.form_vars["width"].set(str(layer.width))
        self.form_vars["height"].set(str(layer.height))
        self.form_vars["rotation"].set(str(layer.rotation))
        self.form_vars["fill"].set(layer.fill)
        self.form_vars["text"].set(layer.text)
        self.form_vars["font_size"].set(str(layer.font_size))

    def _clear_property_form(self) -> None:
        for var in self.form_vars.values():
            var.set("")

    def _apply_properties(self) -> None:
        if not self.selected_layer_id:
            messagebox.showwarning("提示", "请先选择一个图层")
            return
        layer = self.layer_map.get(self.selected_layer_id)
        if layer is None:
            return

        try:
            layer.name = self.form_vars["name"].get() or layer.name
            layer.type = self.form_vars["type"].get() or layer.type
            layer.visible = self.form_vars["visible"].get().strip().lower() != "false"
            layer.opacity = float(self.form_vars["opacity"].get() or layer.opacity)
            layer.x = float(self.form_vars["x"].get() or layer.x)
            layer.y = float(self.form_vars["y"].get() or layer.y)
            layer.width = float(self.form_vars["width"].get() or layer.width)
            layer.height = float(self.form_vars["height"].get() or layer.height)
            layer.rotation = float(self.form_vars["rotation"].get() or layer.rotation)
            layer.fill = self.form_vars["fill"].get() or layer.fill
            layer.text = self.form_vars["text"].get()
            layer.font_size = int(self.form_vars["font_size"].get() or layer.font_size)
        except ValueError as exc:
            messagebox.showerror("属性错误", f"数值格式无效: {exc}")
            return

        self._refresh_all("已应用属性修改")


def main() -> None:
    root = tk.Tk()
    app = GimEditorApp(root)
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()
