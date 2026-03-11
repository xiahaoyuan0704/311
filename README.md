# GIM 桌面解析/渲染编辑器（Python）

这是一个使用 **Python + Tkinter** 编写的桌面程序，用于：

1. 解析 `.gim` 文件（当前实现为 JSON 结构的 GIM）。
2. 在桌面端渲染图层并查看/编辑各层级属性。

## 功能

- 打开 `.gim` 文件并解析出画布和层级结构。
- 左侧树形结构展示所有图层和嵌套层级。
- 中间画布实时渲染（当前支持 `rect`、`text` 类型）。
- 右侧属性面板编辑图层属性（位置、尺寸、颜色、可见性、透明度、文本等）。
- 支持保存/另存为 `.gim`。

## 运行方式

```bash
python3 gim_editor.py
```

> Tkinter 为 Python 标准库，通常无需额外安装依赖。

## `.gim` 数据格式（当前实现）

顶层字段：

- `canvas`: `{ width, height, background }`
- `layers`: 图层数组，每个图层支持 `children` 形成树结构。

图层通用字段示例：

```json
{
  "id": "layer-1",
  "name": "背景",
  "type": "rect",
  "visible": true,
  "opacity": 1,
  "x": 40,
  "y": 40,
  "width": 380,
  "height": 220,
  "rotation": 0,
  "fill": "#2b8cff",
  "text": "",
  "font_size": 14,
  "children": []
}
```

## 测试

```bash
python3 -m unittest -v
```

## 说明

如果你的真实 `.gim` 是二进制或其他规范，只需要在 `gim_model.py` 中替换 `load_gim/save_gim` 的解析逻辑，UI 与属性编辑逻辑仍可复用。
