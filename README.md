# GIM Desktop（可解析真实 .gim、提取属性并渲染）

这版重点修复你反馈的问题：

- 打开后提示“二进制文件不支持渲染”
- 看不到任何属性

现在已支持：即便文件是二进制存储，也会自动尝试提取可识别属性（含中文编码）。

## 已实现能力

- 打开 `.gim`（zip）或解压目录。
- 非 zip 的 `.gim` 也可打开（单文件回退）。
- 多编码自动解码：`utf-8 / utf-8-sig / gb18030 / gbk / utf-16`。
- 属性解析不限 `.fam`：支持 `.fam/.cbm/.dev/.phm/.ini/.cfg/.txt/.gim`。
- 对“看起来是二进制”的文件，会尝试从字节中提取属性行（如 `[设计参数]`、`key=label=value`）。
- 属性可视化编辑（键/显示名/值）并写回当前包。
- 渲染：
  - 属性驱动设备示意渲染；
  - `.mod` 中 OBJ 文本线框渲染；
  - 确实无法解析时显示二进制占位预览。

## 启动

```bash
./run_desktop.sh
```

或

```bash
python3 -m gim_desktop
```

## 测试

```bash
python3 -m unittest -v
python3 -m py_compile gim_desktop/*.py gim_editor.py gim_model.py launch_gim_editor.py
```

> 若在服务器/容器中无图形桌面（无 `$DISPLAY`），GUI 无法弹窗，这是环境限制。
