# GIM Desktop（可打开真实目录结构的桌面软件）

这个版本支持你描述的 `.gim` 内容组织方式：例如 `CBM/ DEV/ MOD/ PHM` 目录，以及其中 `.fam/.cbm/.dev/.mod/.phm` 文件。

尤其是 `.fam` 这种文本属性格式（如 `[设计参数]` + `键=中文名=值`）可以直接解析、查看、编辑。

## 功能

- 打开 `.gim` 文件（按 zip 容器读取）或打开解压后的目录。
- 左侧展示完整文件树（CBM/DEV/MOD/PHM 等）。
- 点击 `.fam` 文件后：
  - 自动解析 `[节]` 与 `键=中文名=值`
  - 表格查看属性（键、中文名、值）
  - 支持在 UI 中修改并写回内存包
- 支持导出为新的 `.gim`（zip）文件。
- 其他文本文件支持原始文本预览。

## 启动

```bash
./run_desktop.sh
```

或：

```bash
python3 -m gim_desktop
```

## 安装命令行入口（可选）

```bash
python3 -m pip install -e .
gim-desktop
```

## 示例 `.fam`（已支持）

```ini
[设计参数]
VoltageLevel=电压等级=10
电网工程标识系统编码=电网工程标识系统编码=30ATD01GL1015
```

## 测试

```bash
python3 -m unittest -v
python3 -m py_compile gim_desktop/*.py gim_editor.py gim_model.py launch_gim_editor.py
```

> 注意：在无桌面显示环境（无 `$DISPLAY`）的服务器/容器里，Tk 界面无法弹窗，这是环境限制，不是程序逻辑问题。
