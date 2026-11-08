# slicer — 3D Slicer 统一入口（DSH 技能包）

把「驱动运行中的 Slicer」「已装扩展与模块名」「Slicer 知识库」合成一个入口。
装到本机后，任何对话都能直接调用，不必每次重新摸索路径。

## 快速开始（已装好的机器）

```powershell
python "$env:USERPROFILE\.dsh\skills\slicer\scripts\slicer.py" --status
python "$env:USERPROFILE\.dsh\skills\slicer\scripts\slicer.py" --info
python "$env:USERPROFILE\.dsh\skills\slicer\scripts\slicer.py" --code "slicer.app.applicationVersion"
```

## 在另一台电脑上安装

```powershell
# 1. 克隆到 DSH 技能目录（目录名必须是 slicer）
git clone https://github.com/yjhd91/dsh-slicer-skill "$env:USERPROFILE\.dsh\skills\slicer"

# 2. 让那台机器的 Slicer 在启动时加载桥
powershell -File "$env:USERPROFILE\.dsh\skills\slicer\scripts\setup_bridge.ps1" -SlicerDir "D:\Slicer 5.12.4"

# 3. 正常启动 3D Slicer，然后确认
python "$env:USERPROFILE\.dsh\skills\slicer\scripts\slicer.py" --status
```

技能目录被 DSH 自动扫描，克隆完即可在新对话里命中 `slicer` 技能。
Slicer 装在别处时用 `-SlicerDir` 指定；路径非常规时用环境变量
`DSH_SLICER_EXE`、`DSH_SLICER_BRIDGE` 覆盖。

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 技能入口：何时用、怎么下发代码、坑与排查 |
| `scripts/slicer.py` | CLI 客户端（status / info / code / file / start / restart） |
| `scripts/bridge_autoload.py` | 桥的服务端：在 Slicer 主线程轮询队列并执行 |
| `scripts/setup_bridge.ps1` | 一键把桥挂到某台机器的 Slicer 启动配置里 |
| `references/extensions.md` | 扩展 ↔ 模块名对照，含装不上的两个 |
| `references/knowledge.md` | 上游 `pieper/slicer-skill` 的 Slicer 知识正文（48 KB） |
| `LICENSE` | 上游 MIT 许可证 |

## 工作原理

```
你（或 AI） --python slicer.py --code/--file-->
    写入 <bridge>/inbox/<id>.py
        ↓（Slicer 内 QTimer，每 200ms，主线程）
    执行，结果写 <bridge>/outbox/<id>.json
        ↓
    客户端读回 stdout / 返回值 / 异常栈
```

主线程执行保证了 MRML 与 Qt 对象操作是安全的；代价是长任务会卡住 Slicer 界面，
所以脚本要拆小步。<bridge>/heartbeat.json 每 200ms 刷新并带 pid，
用于判活与「只允许一个 Slicer 服务队列」。

## 来源与边界

`references/knowledge.md` 与 `LICENSE` 来自 [pieper/slicer-skill](https://github.com/pieper/slicer-skill)（MIT）。
上游附带的检索索引（BM25/向量库，需要 clone Slicer 源码构建）没有一并提供，
该知识正文作为静态参考；实时检索请用本技能的桥，或查 GitHub / Discourse。
