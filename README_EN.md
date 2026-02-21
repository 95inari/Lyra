# Lyra

**Automated Vocal Editing Tool** — Automatically aligns vocals from different takes or singers to match the pitch and timing of a reference track.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

**Languages:** [日本語](README.md) | English | [简体中文](README_ZH.md) | [한국어](README_KO.md) | [Español](README_ES.md)

---

## Overview

Lyra automates the process of aligning one vocal recording to another (reference). By combining DTW-based timing correction with RMVPE-based pitch correction, it dramatically reduces the time spent on manual editing.

**Main use cases:**

- Align a take sung by a different singer to a reference performance of the same song
- Unify pitch and timing across multiple takes by the same singer
- Generate correction data (`recipe.json`) as pre-processing for vocal mixing

## Processing Pipeline

```
Input Audio
  │
  ├─ ① Vocal Separation (Demucs htdemucs)  *skipped when --stem is specified
  ├─ ② F0 Estimation (RMVPE)
  ├─ ③ Onset Detection (librosa)
  ├─ ④ Key Shift Estimation / Manual Override
  ├─ ⑤ DTW Alignment
  └─ ⑥ Rendering (pyrubberband)
         │
         ├─ Corrected WAV
         └─ recipe.json (correction data)
```

## Requirements

| Item | Requirement |
|------|-------------|
| Python | 3.11 or higher |
| OS | macOS / Linux / Windows |
| GPU | Optional (works on CPU, but processing takes longer) |

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/<owner>/lyra.git
cd lyra
```

### 2. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Download Models

```bash
python scripts/download_models.py --rmvpe
```

> Downloads the RMVPE model (~181 MB) from Hugging Face.

## Quick Start

Once installation is complete, you can start right away with the following commands.

**CLI (Command Line)**

```bash
lyra run --ref reference.wav --vocal new_vocal.wav
```

When processing completes, `edited_vocal.wav` and `recipe.json` are generated in the current directory.

**GUI**

```bash
python -m gui.app
```

Or launch directly:

```bash
python gui/app.py
```

Once the window opens, select files and click the Run button to start processing.

---

## Usage

### CLI

```bash
# Basic usage
lyra run --ref reference.wav --vocal new_vocal.wav

# Specify output files
lyra run --ref reference.wav --vocal new_vocal.wav \
    --out-wav output.wav --out-recipe recipe.json

# Change preset (light / standard / strong)
lyra run --ref reference.wav --vocal new_vocal.wav --preset strong

# Provide vocal stem directly (skip separation)
lyra run --ref reference.wav --vocal vocal_stem.wav --stem

# Manually specify key shift (in semitones)
lyra run --ref reference.wav --vocal new_vocal.wav --key-shift -2
```

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--ref` | required | Reference audio file |
| `--vocal` | required | Vocal file to correct |
| `--preset` | `standard` | Correction strength (`light` / `standard` / `strong`) |
| `--stem` | false | Skip vocal separation |
| `--key-shift` | auto-detected | Key shift amount (in semitones) |
| `--out-wav` | `output.wav` | Output WAV file path |
| `--out-recipe` | `recipe.json` | Output recipe.json path |

### GUI

```bash
python -m gui.app
```

The GUI supports:

- File selection and processing execution
- Pitch curve visualization (reference, input, corrected)
- Timing warp visualization
- Per-segment pitch and timing correction adjustment
- Export of corrected WAV and recipe.json

### recipe.json

Lyra outputs correction data as `recipe.json`. This file can be imported by DAW plugins or other tools.

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

## Development

```bash
# Install with dev tools
pip install -e ".[dev]"

# Run tests (no models required)
pytest tests/test_smoke.py -v

# Integration tests (models required)
pytest tests/test_integration.py -v

# Lint
ruff check .
```

## License Notes

Lyra is distributed under the MIT License, but please note the licenses of the following dependencies:

- **pyrubberband**: GPL v2+ — Commercial closed-source use that includes this dependency is restricted
- **PySide6**: LGPL v3 / Commercial License — Available under LGPL terms via dynamic linking
- **RMVPE model**: Please check the license at the [original repository](https://github.com/yxlllc/RMVPE)

## Contributing

Bug reports, feature requests, and pull requests are welcome.
See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

[MIT License](LICENSE) © 2025 Lyra Contributors
