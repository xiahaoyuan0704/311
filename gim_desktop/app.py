from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gim_desktop.model import FamDocument, GimPackage, load_gim_package


class GimDesktopApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GIM 桌面解析工具")
        self.root.geometry("1280x820")

        self.package: GimPackage | None = None
        self.selected_path: str | None = None
        self.current_fam: FamDocument | None = None
        self.current_fam_path: str | None = None

        self.status_var = tk.StringVar(value="请选择 .gim 文件或解压目录")

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=8, pady=8)

        ttk.Button(toolbar, text="打开 .gim", command=self.open_gim_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="打开目录", command=self.open_gim_directory).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="保存当前FAM", command=self.save_current_fam).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="导出为 .gim(zip)", command=self.export_gim_zip).pack(side=tk.LEFT, padx=4)

        ttk.Label(toolbar, textvariable=self.status_var).pack(side=tk.RIGHT, padx=8)

        main = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        left = ttk.Labelframe(main, text="文件结构")
        main.add(left, weight=3)

        self.tree = ttk.Treeview(left, show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_file)

        right = ttk.Labelframe(main, text="属性与内容")
        main.add(right, weight=7)

        right_pane = ttk.Panedwindow(right, orient=tk.VERTICAL)
        right_pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        top = ttk.Labelframe(right_pane, text="FAM 属性编辑")
        right_pane.add(top, weight=6)

        self.prop_table = ttk.Treeview(top, columns=("key", "label", "value"), show="headings")
        self.prop_table.heading("key", text="属性键")
        self.prop_table.heading("label", text="中文名")
        self.prop_table.heading("value", text="值")
        self.prop_table.column("key", width=220)
        self.prop_table.column("label", width=260)
        self.prop_table.column("value", width=320)
        self.prop_table.pack(fill=tk.BOTH, expand=True)

        edit_frame = ttk.Frame(top)
        edit_frame.pack(fill=tk.X, pady=6)
        self.key_var = tk.StringVar()
        self.label_var = tk.StringVar()
        self.value_var = tk.StringVar()
        ttk.Label(edit_frame, text="键").grid(row=0, column=0, padx=4)
        ttk.Entry(edit_frame, textvariable=self.key_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Label(edit_frame, text="中文名").grid(row=0, column=2, padx=4)
        ttk.Entry(edit_frame, textvariable=self.label_var).grid(row=0, column=3, sticky="ew", padx=4)
        ttk.Label(edit_frame, text="值").grid(row=0, column=4, padx=4)
        ttk.Entry(edit_frame, textvariable=self.value_var).grid(row=0, column=5, sticky="ew", padx=4)
        ttk.Button(edit_frame, text="应用到选中行", command=self.apply_property_edit).grid(row=0, column=6, padx=6)
        edit_frame.columnconfigure(1, weight=1)
        edit_frame.columnconfigure(3, weight=1)
        edit_frame.columnconfigure(5, weight=2)

        self.prop_table.bind("<<TreeviewSelect>>", self.on_select_property)

        bottom = ttk.Labelframe(right_pane, text="原始文本预览")
        right_pane.add(bottom, weight=4)

        self.raw_text = tk.Text(bottom, height=14, wrap="none")
        self.raw_text.pack(fill=tk.BOTH, expand=True)

    def open_gim_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("GIM 文件", "*.gim"), ("全部文件", "*.*")])
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

        existing_nodes: set[str] = set()
        for file_path in self.package.file_paths():
            parts = file_path.split("/")
            parent = ""
            current = ""
            for part in parts:
                current = f"{current}/{part}" if current else part
                if current in existing_nodes:
                    parent = current
                    continue
                self.tree.insert(parent, tk.END, iid=current, text=part)
                existing_nodes.add(current)
                parent = current

    def clear_detail(self) -> None:
        self.current_fam = None
        self.current_fam_path = None
        self.selected_path = None
        self.prop_table.delete(*self.prop_table.get_children())
        self.raw_text.delete("1.0", tk.END)

    def on_select_file(self, _event: tk.Event) -> None:
        if not self.package:
            return
        selected = self.tree.selection()
        if not selected:
            return
        path = selected[0]
        if path not in self.package.files:
            return

        self.selected_path = path
        lower = path.lower()

        if lower.endswith(".fam"):
            text = self.package.read_text(path)
            fam = FamDocument.parse(text)
            self.current_fam = fam
            self.current_fam_path = path
            self.show_fam(fam)
            self.raw_text.delete("1.0", tk.END)
            self.raw_text.insert(tk.END, text)
            self.status_var.set(f"已打开 FAM: {path}")
            return

        self.current_fam = None
        self.current_fam_path = None
        self.prop_table.delete(*self.prop_table.get_children())

        preview = self.package.read_text(path)
        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert(tk.END, preview)
        self.status_var.set(f"已预览: {path}")

    def show_fam(self, fam: FamDocument) -> None:
        self.prop_table.delete(*self.prop_table.get_children())
        for section in fam.sections:
            sec_id = self.prop_table.insert("", tk.END, values=(f"[{section.name}]", "", ""))
            for idx, item in enumerate(section.properties):
                row_id = f"{sec_id}:{idx}"
                self.prop_table.insert("", tk.END, iid=row_id, values=(item.key, item.label, item.value))

    def on_select_property(self, _event: tk.Event) -> None:
        sel = self.prop_table.selection()
        if not sel:
            return
        row = self.prop_table.item(sel[0], "values")
        if not row or row[0].startswith("["):
            return
        self.key_var.set(row[0])
        self.label_var.set(row[1])
        self.value_var.set(row[2])

    def apply_property_edit(self) -> None:
        if not self.current_fam or not self.current_fam_path or not self.package:
            messagebox.showwarning("提示", "请先选择一个 .fam 文件")
            return
        sel = self.prop_table.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选中一个属性行")
            return

        row_id = sel[0]
        if ":" not in row_id:
            messagebox.showwarning("提示", "请选择具体属性，不是分组头")
            return

        sec_part, idx_part = row_id.split(":", 1)
        idx = int(idx_part)

        section_name = self.prop_table.item(sec_part, "values")[0].strip("[]")
        target_section = next((sec for sec in self.current_fam.sections if sec.name == section_name), None)
        if target_section is None or idx >= len(target_section.properties):
            return

        prop = target_section.properties[idx]
        prop.key = self.key_var.get().strip() or prop.key
        prop.label = self.label_var.get().strip() or prop.label
        prop.value = self.value_var.get().strip()

        self.show_fam(self.current_fam)
        new_text = self.current_fam.to_text()
        self.raw_text.delete("1.0", tk.END)
        self.raw_text.insert(tk.END, new_text)
        self.package.write_text(self.current_fam_path, new_text)
        self.status_var.set(f"已更新属性: {self.current_fam_path}")

    def save_current_fam(self) -> None:
        if not self.current_fam_path or not self.package:
            messagebox.showwarning("提示", "请先选择 .fam 文件")
            return
        path = filedialog.asksaveasfilename(defaultextension=".fam", filetypes=[("FAM 文件", "*.fam")])
        if not path:
            return
        Path(path).write_text(self.package.read_text(self.current_fam_path), encoding="utf-8")
        self.status_var.set(f"已保存: {path}")

    def export_gim_zip(self) -> None:
        if not self.package:
            messagebox.showwarning("提示", "请先打开 .gim 或目录")
            return
        output = filedialog.asksaveasfilename(defaultextension=".gim", filetypes=[("GIM 文件", "*.gim")])
        if not output:
            return
        self.package.save_as_gim_zip(output)
        self.status_var.set(f"已导出: {output}")


def run() -> None:
    root = tk.Tk()
    GimDesktopApp(root)
    root.mainloop()
