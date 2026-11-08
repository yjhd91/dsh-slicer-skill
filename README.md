# slicer — 3D Slicer 统一入口（DSH 技能包）

本目录打包了三件事，装在本机、可直接用：

1. **驱动运行中的 Slicer** —— 通过 `scripts/slicer.py` 把 Python 送进正在运行的 Slicer 执行并取回结果。
2. **模块清单** —— 已装 15 个扩展及其真实模块名（`references/extensions.md`）。
3. **Slicer 知识库** —— 架构、MRML、模块开发、构建系统、踩坑记录（`references/knowledge.md`）。

## 快速开始

```powershell
python "$env:USERPROFILE\.dsh\skills\slicer\scripts\slicer.py" --status
python "$env:USERPROFILE\.dsh\skills\slicer\scripts\slicer.py" --info
python "$env:USERPROFILE\.dsh\skills\slicer\scripts\slicer.py" --code "slicer.app.applicationVersion"
```

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 技能入口：何时用、怎么下发代码、坑与排查 |
| `scripts/slicer.py` | CLI 客户端（status / info / code / file / start / restart） |
| `references/extensions.md` | 扩展 ↔ 模块名对照，含没装上的两个 |
| `references/knowledge.md` | 上游 `pieper/slicer-skill` 的 Slicer 知识正文（48 KB） |
| `LICENSE` | 上游 MIT 许可证 |

## 依赖的外部资产（不在本目录内）

| 路径 | 作用 |
|---|---|
| `D:\Slicer 5.12.4` | Slicer 本体（rev 34645，Python 3.12.10） |
| `D:\SlicerModules\bridge` | 桥的服务端 `bridge_autoload.py`、队列、心跳 |
| `D:\SlicerModules\Slicey` | Slicey 源码副本；`install-slicey.ps1` 重装 |
| `D:\Slicer 5.12.4\bin\SlicerLauncherSettings.ini` | 已加 `--python-script`，正常启动即自动挂桥 |

路径变了用环境变量覆盖：`DSH_SLICER_BRIDGE`、`DSH_SLICER_EXE`。

## 来源与边界

`references/knowledge.md` 与 `LICENSE` 来自 [pieper/slicer-skill](https://github.com/pieper/slicer-skill)（MIT）。
上游附带的检索索引（BM25/向量库，需要 clone Slicer 源码构建）本机没有构建，
所以那份知识正文只作为静态参考；实时检索请直接用本技能的桥，或查 GitHub / Discourse。
