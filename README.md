# GIM Desktop（完整桌面软件项目）

你要的不是“单个 `.py` 脚本”，而是一个可直接启动界面的完整桌面软件项目。这个仓库现在提供了：

- 可安装的桌面应用包：`gim_desktop/`
- 统一启动命令：`python3 -m gim_desktop`
- 一键启动脚本：`./run_desktop.sh`
- 兼容入口：`launch_gim_editor.py`

## 1) 直接运行桌面软件

```bash
./run_desktop.sh
```

或：

```bash
python3 -m gim_desktop
```

## 2) 安装为本地命令（可选）

```bash
python3 -m pip install -e .
```

安装后可直接运行：

```bash
gim-desktop
```

## 3) 已实现的核心能力

- 解析 `.gim`（当前按 JSON 结构）
- 左侧树形层级浏览（含 children 嵌套）
- 中间画布桌面渲染（`rect`、`text`）
- 右侧属性编辑并应用回图层
- 打开、保存、另存为

## 4) 当前 `.gim` 格式

顶层：

- `canvas`: `{ width, height, background }`
- `layers`: 图层数组（每层可含 `children`）

示例见：`sample.gim`

## 5) 测试

```bash
python3 -m unittest -v
python3 -m py_compile gim_desktop/*.py gim_editor.py gim_model.py launch_gim_editor.py
```

## 6) 目录结构

```text
gim_desktop/
  ├─ app.py          # 桌面 UI 与交互逻辑
  ├─ model.py        # .gim 数据模型与解析
  ├─ __main__.py     # 支持 python -m gim_desktop
  └─ __init__.py
run_desktop.sh       # 一键启动脚本
launch_gim_editor.py # 启动入口（便于桌面快捷方式绑定）
pyproject.toml       # 项目打包配置（支持 gim-desktop 命令）
```

> 如果你的真实 `.gim` 是二进制或私有协议，只需替换 `gim_desktop/model.py` 的 load/save 逻辑，桌面界面可保持不变。
