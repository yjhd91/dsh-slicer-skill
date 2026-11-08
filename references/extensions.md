# 已装扩展与模块对照（Slicer 5.12.4 rev 34645，Windows x64）

装机日期 2026-11-08。全部经 `extensionsManagerModel().downloadAndInstallExtensionByName()` 安装，
下载 50.3 MB，`D:\Slicer 5.12.4\slicer.org\Extensions-34645`。

## 关键条目

| 扩展 | 暴露的模块（`dir(slicer.modules)` 里的名字） | 用途与注意 |
|---|---|---|
| SegmentMesher | `segmentmesher`、`cfdmeshgenerator` | 分割标签 → 体网格。`cfdmeshgenerator` 是专门给 CFD 的；内部走 Cleaver/tetgen。 |
| SlicerVMTK | `extractcenterline`、`extractskeleton`（另有截面分析等） | 血管中心线、半径、截面。**扩展名不等于模块名**，按 `vmtk` 搜是搜不到的。 |
| TotalSegmentator | `totalsegmentator` | 百余类自动分割（本机 ts117 标签同源）。首次运行会下载权重，耗时且占盘。 |
| SlicerElastix | `elastix` | 强度配准。 |
| SlicerCaseIterator | `slicercaseiterator` | 批量遍历病例（适合 802 例这种队列）。 |
| MeshStatisticsExtension | `meshstatistics` | 网格统计质检。 |
| ModelToModelDistance | `modelToModelDistance`（CLI） | 两模型间距离，可做配准/网格比对。 |
| SegmentEditorExtraEffects | 无独立模块，向 Segment Editor 注入效果（如 `robuststatisticssegmenter`） | 是效果集合，不在模块列表里作为一个模块出现。 |
| SurfaceWrapSolidify | 效果 `segmenteditorwrapsolidify` | 外壳封闭，网格化前处理。同上，属于 Segment Editor 效果。 |
| ExtraMarkups | `extraMarkups...` 系列 | 额外 markups 形状。 |
| MarkupsToModel | `markupsToModel` | 标记点 → 模型。 |
| NNUNet | 无独立模块（库/CLI 支撑） | TotalSegmentator 等的底层。 |
| PyTorch | 无独立模块 | 向 Slicer 的 Python 提供 PyTorch 工具链。 |
| SlicerDevelopmentToolbox | 无独立模块（库） | 其他扩展的依赖。 |
| SlicerPythonTestRunner | 无独立模块（库） | 依赖。 |
| Slicey（自装，非索引扩展） | `slicey` | Slicer 内 AI 对话面板，见 SKILL.md 第 4 节。 |

## 没装上的

- `AortaSegmentation`：rev 34645 win 无构建，管理器返回 False。
- `HexaMesher`：同上。

需要时去 `https://extensions.slicer.org/catalog/All/34645/win` 核对是否有对应构建。

## 怎么自己查

```python
# 装了什么（注意：installedExtensions 是属性，不加括号）
[slicer.app.extensionsManagerModel().installedExtensions]

# 装了但不确定模块名
sorted(n for n in dir(slicer.modules) if "mesh" in n.lower())

# 再装一个
slicer.app.extensionsManagerModel().downloadAndInstallExtensionByName("SlicerRadiomics")
```

装完需要**重启 Slicer** 才会加载。
