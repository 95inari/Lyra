# Lyra

**人声自动编辑工具** — 自动将不同录音或不同歌手的人声对齐到参考音频的音高和时序。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

**语言：** [日本語](README.md) | [English](README_EN.md) | 简体中文 | [한국어](README_KO.md) | [Español](README_ES.md)

---

## 概述

Lyra 自动完成将一段人声录音对齐到另一段（参考音频）的处理流程。
结合基于 DTW 的时序校正与基于 RMVPE 的音高校正，大幅减少手动编辑的工作量。

**主要用途：**

- 将不同歌手演唱同一首歌的录音对齐到参考演唱
- 统一同一歌手多个录音之间的音高与时序
- 生成校正数据（`recipe.json`），作为人声混音的前处理步骤

## 处理流程

```
输入音频
  │
  ├─ ① 人声分离（Demucs htdemucs）  ※指定 --stem 时跳过
  ├─ ② 基频估计（RMVPE）
  ├─ ③ 起音点检测（librosa）
  ├─ ④ 调式偏移估计 / 手动指定
  ├─ ⑤ DTW 对齐
  └─ ⑥ 渲染（pyrubberband）
         │
         ├─ 校正后的 WAV
         └─ recipe.json（校正数据）
```

## 运行环境

| 项目 | 要求 |
|------|------|
| Python | 3.11 及以上 |
| 操作系统 | macOS / Linux / Windows |
| GPU | 可选（CPU 也可运行，但处理时间较长） |

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/<owner>/lyra.git
cd lyra
```

### 2. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 3. 下载模型

```bash
python scripts/download_models.py --rmvpe
```

> 从 Hugging Face 下载 RMVPE 模型（约 181 MB）。

## 快速开始

安装完成后，可以立即使用以下命令。

**CLI（命令行）**

```bash
lyra run --ref reference.wav --vocal new_vocal.wav
```

处理完成后，`edited_vocal.wav` 和 `recipe.json` 将生成在当前目录。

**GUI**

```bash
python -m gui.app
```

或直接启动：

```bash
python gui/app.py
```

窗口打开后，选择文件并点击运行按钮即可开始处理。

---

## 使用方法

### CLI

```bash
# 基本用法
lyra run --ref reference.wav --vocal new_vocal.wav

# 指定输出文件
lyra run --ref reference.wav --vocal new_vocal.wav \
    --out-wav output.wav --out-recipe recipe.json

# 修改预设（light / standard / strong）
lyra run --ref reference.wav --vocal new_vocal.wav --preset strong

# 直接指定人声轨（跳过分离处理）
lyra run --ref reference.wav --vocal vocal_stem.wav --stem

# 手动指定调式偏移（以半音为单位）
lyra run --ref reference.wav --vocal new_vocal.wav --key-shift -2
```

#### 选项说明

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--ref` | 必填 | 参考音频文件 |
| `--vocal` | 必填 | 待校正的人声文件 |
| `--preset` | `standard` | 校正强度（`light` / `standard` / `strong`） |
| `--stem` | false | 跳过人声分离 |
| `--key-shift` | 自动检测 | 调式偏移量（半音单位） |
| `--out-wav` | `output.wav` | 输出 WAV 文件路径 |
| `--out-recipe` | `recipe.json` | 输出 recipe.json 路径 |

### GUI

```bash
python -m gui.app
```

GUI 支持以下操作：

- 文件选择与处理执行
- 音高曲线可视化（参考、输入、校正后）
- 时序变形可视化
- 按片段调整音高与时序校正量
- 导出校正后的 WAV 与 recipe.json

### recipe.json

Lyra 将校正数据输出为 `recipe.json`，可供 DAW 插件或其他工具读取使用。

```json
{
  "version": "0.1",
  "sample_rate": 44100,
  "global_key_shift_semitones": 0.0,
  "segments": [
    {
      "t0": 0.0,
      "t1": 2.5,
      "time_warp_points": [[0.0, 0.0], [1.2, 1.35], [2.5, 2.5]],
      "pitch_target_curve": [[0.0, 220.0], [0.5, 246.9]],
      "confidence": 0.85,
      "pitch_strength": 1.0,
      "time_strength": 1.0
    }
  ]
}
```

## 开发

```bash
# 安装开发依赖（含测试工具）
pip install -e ".[dev]"

# 运行测试（无需模型）
pytest tests/test_smoke.py -v

# 集成测试（需要模型）
pytest tests/test_integration.py -v

# 代码检查
ruff check .
```

## 许可证说明

Lyra 以 MIT 许可证分发，但请注意以下依赖库的许可证：

- **pyrubberband**：GPL v2+ — 包含此依赖的商业闭源使用受到限制
- **PySide6**：LGPL v3 / 商业许可证 — 通过动态链接可在 LGPL 条款下使用
- **RMVPE 模型**：请查阅[原始仓库](https://github.com/yxlllc/RMVPE)的许可证

## 贡献

欢迎提交 Bug 报告、功能建议和 Pull Request。
详情请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT License](LICENSE) © 2025 Lyra Contributors
