# GIM Desktop（可打开真实 .gim，并解析/编辑多类型属性 + 基础渲染）

你提到的问题有 3 个：

1. 打开 `.gim` 报错（例如 `file is not a file` / `not a zip file`）
2. 需要解析的不只是 `.fam`，还包括其他属性文件
3. 需要能渲染，看到具体模型样式

本版本已针对这 3 点做了修复和增强。

## 已实现能力

- 支持打开：
  - `.gim`（zip 容器）
  - 解压后的目录（CBM/DEV/MOD/PHM）
  - 非 zip 的 `.gim` 也可打开（按单文件包回退，不再直接报错）
- 属性解析（不仅是 `.fam`）：
  - `.fam/.cbm/.dev/.phm/.ini/.cfg/.txt`
  - 支持 `[分节]` + `key=label=value` / `key=value`
- 属性编辑：
  - 表格查看键/显示名/值
  - 修改后写回当前包内文件
  - 可保存当前文件或导出整包 `.gim`
- 渲染：
  - 属性文件：根据关键属性生成设备示意渲染（电压等级、设备名称、编码）
  - `.mod` 文本：若为 OBJ 结构（`v/f`），可进行线框渲染预览
  - 二进制模型：显示占位卡片与文件信息（大小）

## 启动

```bash
./run_desktop.sh
```

或：

```bash
python3 -m gim_desktop
```

## 使用流程

1. 点击“打开 `.gim`”或“打开目录”
2. 左侧选择 `DEV/CBM/PHM/FAM` 等属性文件进行解析编辑
3. 切换到“模型渲染”页查看示意/线框渲染
4. 修改后点击“导出 `.gim(zip)`”

## 测试

```bash
python3 -m unittest -v
python3 -m py_compile gim_desktop/*.py gim_editor.py gim_model.py launch_gim_editor.py
```

> 说明：如果运行环境没有图形桌面（无 `$DISPLAY`），Tk 窗口无法弹出，这是环境限制。
