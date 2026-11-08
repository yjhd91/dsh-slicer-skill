---
name: slicer
description: >
  3D Slicer 统一入口（本机已装好、可直接驱动）。在正在运行的 Slicer 里执行 Python 并取回
  stdout / 返回值 / 异常栈，等价于「AI 直接操控 Slicer」。本机现状：Slicer 5.12.4（rev 34645 /
  Python 3.12.10），已装 15 个扩展（SegmentMesher、SlicerVMTK、TotalSegmentator、SlicerElastix、
  SegmentEditorExtraEffects、SurfaceWrapSolidify、SlicerCaseIterator、MeshStatisticsExtension 等）
  与 Slicey AI 面板模块。
  触发词: 3D Slicer · Slicer · slicer 桥 · 分割 · 体网格 · 网格化 · 中心线 · 血管 · VMTK ·
  TotalSegmentator · elastix · 配准 · 主动脉 · DICOM · MRML · Segment Editor · Slicey.
  Use when driving or scripting 3D Slicer, medical-image segmentation / meshing / registration,
  or extending Slicer modules. Not for generic image processing outside Slicer.
version: "1.0"
---

# slicer — 3D Slicer 统一入口

本技能把三件事合成一个入口：**驱动运行中的 Slicer**、**可用模块清单**、**Slicer 知识库**。
不用每次重新摸索路径——它们已经装好并测过。

## 0. 先决检查（每次开始先跑这一条）

```powershell
python "$env:USERPROFILE\.dsh\skills\slicer\scripts\slicer.py" --status
```

- 输出 `bridge: RUNNING` → 直接可用。
- 输出 `STOPPED` / `NOT RUNNING` → 让用户从开始菜单启动 Slicer（桥会随启动自动挂上），
  或代跑 `--start` 拉起一个（会在用户桌面上开窗，先问一句再拉）。

## 1. 怎么下发代码

```powershell
# 直接一行
python ...\scripts\slicer.py --code "slicer.util.getNodesByClass('vtkMRMLSegmentationNode')"

# 复杂逻辑写文件再送（推荐，避免引号地狱）
python ...\scripts\slicer.py --file C:\temp\my_task.py

# 机器可读
python ...\scripts\slicer.py --file my_task.py --json
```

脚本在 **Slicer 主线程**执行：
- 末尾若是表达式，其值按 REPL 语义返回（`--json` 里是 `result`）。
- `print()` 输出一并回传（`stdout`）。
- 抛异常回传完整 traceback（`error`），进程退出码非 0。

**硬性约定**：
- 只写能在 Slicer 里 import 的东西；`slicer` / `qt` 已注入命名空间，不必自己 import。
- 长任务会卡住 Slicer 界面（主线程），拆成小步；预计 >30s 的先告诉用户。
- 不要写 `sys.exit()`、不要调 `slicer.app.quit()`（会关掉用户的窗口）。
- 需要弹窗的 API 一律避开，改用返回值/日志。

## 2. 常用配方

```python
# 场景概览
{"nodes": slicer.mrmlScene.GetNumberOfNodes(),
 "seg": [n.GetName() for n in slicer.util.getNodesByClass("vtkMRMLSegmentationNode")],
 "vol": [n.GetName() for n in slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")]}

# 载入序列/DICOM 目录
slicer.util.loadVolume(r"D:\data\case\ct.nii.gz")

# 导出分割为模型（STL/OBJ）
import os
seg = slicer.util.getNode("Segmentation")
sh = slicer.modules.segmentations.logic()
out = r"D:\out"
os.makedirs(out, exist_ok=True)
sh.ExportAllSegmentsToModels(seg, out)
slicer.util.saveNode(...)  # 或逐个 model 节点 saveNodeModel

# 跑任意 CLI 模块（以 SegmentMesher 的 cfdmeshgenerator 为例，参数先查帮助）
slicer.modules.cfdmeshgenerator  # 查参数时用 module.cliModuleLogic 或 --help
```

取舍原则：**优先用已装扩展的模块**（见下节），不要手写已有实现；
API 细节先查 `references/knowledge.md`，别凭记忆写方法名。

## 3. 本机可用模块（按用途）

| 用途 | 扩展 | 加载后的模块名 |
|---|---|---|
| 分割→体网格（接 CFD） | SegmentMesher | `segmentmesher`、`cfdmeshgenerator` |
| 血管中心线/截面 | SlicerVMTK | `extractcenterline`、`extractskeleton` |
| 自动全身分割 | TotalSegmentator | `totalsegmentator` |
| 配准 | SlicerElastix | `elastix` |
| 批量遍历病例 | SlicerCaseIterator | `slicercaseiterator` |
| 网格质检 | MeshStatisticsExtension / ModelToModelDistance | `meshstatistics` |
| 外壳封闭/额外效果 | SurfaceWrapSolidify / SegmentEditorExtraEffects | `segmenteditorwrapsolidify`（效果，非模块） |
| AI 对话面板 | Slicey（自装，非索引扩展） | `slicey` |

完整清单与每个扩展的注意事项见 `references/extensions.md`。
**注意**：扩展内的模块名往往不等于扩展名（VMTK 暴露为 `extractcenterline`，
SurfaceWrapSolidify 是 Segment Editor 里的一个效果）。查不到就用关键词搜：
`sorted(n for n in dir(slicer.modules) if "mesh" in n.lower())`。

## 4. Slicey（Slicer 内的 AI 面板）

- 位置：`lib\Slicer-5.12\qt-scripted-modules\Slicey.py`（源码副本 `D:\SlicerModules\Slicey`）。
- 重装脚本：`D:\SlicerModules\install-slicey.ps1 -SlicerDir "D:\Slicer 5.12.4"`。
- 后端：Claude API / Claude 订阅 / ChatGPT 订阅 / OpenAI API / 本地 Anthropic 兼容服务器。
- 与本技能的关系：**本技能不经过 Slicey**——它直接驱动 Slicer，用当前对话的模型，
  不需要额外账号。Slicey 留给用户自己在 Slicer 界面里用（例如需要它的共享文件夹与审批流）。

## 5. 已知坑

- Slicer 只从 `qt-scripted-modules` **顶层 `*.py`** 加载脚本模块，放成子目录不认。
- `Modules/AdditionalPaths` 用 PythonQt 写列表会存成 `@Invalid()`；INI 里 `[Styles] AdditionalPaths`
  是配色路径，不是模块路径。
- PowerShell 5.1 `Set-Content -Encoding UTF8` 会写 BOM，Python 会报 `U+FEFF`；写盘用 Python 或
  `[System.IO.File]::WriteAllText(..., New-Object System.Text.UTF8Encoding($false))`。
- 同一时刻只允许一个 Slicer 服务队列；开第二个实例时桥会自动待机。
- 详细版（架构、MRML、构建系统、模块开发）见 `references/knowledge.md`。

## 6. 故障排查

| 现象 | 处理 |
|---|---|
| `--status` 报 NOT RUNNING | 启动 Slicer；或 `--start` |
| 报 SLOW / 超时 | Slicer 主线程被占（跑着长任务），等它结束或让用户取消 |
| 代码报 `NameError: slicer` | 用了 `--file` 但没走桥？确认脚本通过本 CLI 下发，命名空间才注入 |
| 模块找不到 | 用关键词搜 `dir(slicer.modules)`；确认扩展装了：`m.installedExtensions`（无括号） |
| 桥本身坏了 | `D:\SlicerModules\bridge\bridge.log`；必要时 `--restart` |
