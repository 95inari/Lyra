# Lyra

**보컬 편집 자동화 도구** — 다른 테이크나 다른 가수의 보컬을 레퍼런스의 피치·타이밍에 자동으로 맞춰줍니다.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

**언어:** [日本語](README.md) | [English](README_EN.md) | [简体中文](README_ZH.md) | 한국어 | [Español](README_ES.md)

---

## 개요

Lyra는 한 보컬 녹음을 다른 녹음(레퍼런스)에 맞추는 처리를 자동화하는 도구입니다.
DTW 기반 타이밍 보정과 RMVPE 기반 피치 보정을 결합하여 수동 편집 작업량을 대폭 줄입니다.

**주요 용도:**

- 같은 곡을 다른 가수가 녹음한 테이크를 레퍼런스에 가깝게 맞추기
- 같은 가수의 여러 테이크 간 피치·타이밍 통일
- 보컬 믹스 전처리로 보정 데이터(`recipe.json`) 생성

## 처리 파이프라인

```
입력 오디오
  │
  ├─ ① 보컬 분리 (Demucs htdemucs)  ※--stem 지정 시 스킵
  ├─ ② F0 추정 (RMVPE)
  ├─ ③ 온셋 감지 (librosa)
  ├─ ④ 키 시프트 추정 / 수동 지정
  ├─ ⑤ DTW 정렬
  └─ ⑥ 렌더링 (pyrubberband)
         │
         ├─ 보정된 WAV
         └─ recipe.json (보정 데이터)
```

## 동작 환경

| 항목 | 요구 사항 |
|------|----------|
| Python | 3.11 이상 |
| OS | macOS / Linux / Windows |
| GPU | 선택 사항 (CPU로도 동작하지만 처리 시간이 길어집니다) |

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/<owner>/lyra.git
cd lyra
```

### 2. 의존성 설치

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 3. 모델 다운로드

```bash
python scripts/download_models.py --rmvpe
```

> Hugging Face에서 RMVPE 모델(약 181 MB)을 다운로드합니다.

## 빠른 시작

설치 완료 후 다음 명령어로 바로 사용할 수 있습니다.

**CLI (커맨드 라인)**

```bash
lyra run --ref reference.wav --vocal new_vocal.wav
```

처리가 완료되면 `edited_vocal.wav`와 `recipe.json`이 현재 디렉토리에 생성됩니다.

**GUI**

```bash
python -m gui.app
```

또는 직접 실행:

```bash
python gui/app.py
```

창이 열리면 파일을 선택하고 실행 버튼을 클릭하면 처리가 시작됩니다.

---

## 사용 방법

### CLI

```bash
# 기본 사용법
lyra run --ref reference.wav --vocal new_vocal.wav

# 출력 파일 지정
lyra run --ref reference.wav --vocal new_vocal.wav \
    --out-wav output.wav --out-recipe recipe.json

# 프리셋 변경 (light / standard / strong)
lyra run --ref reference.wav --vocal new_vocal.wav --preset strong

# 보컬 스템 직접 지정 (분리 처리 스킵)
lyra run --ref reference.wav --vocal vocal_stem.wav --stem

# 키 시프트 수동 지정 (반음 단위)
lyra run --ref reference.wav --vocal new_vocal.wav --key-shift -2
```

#### 옵션 목록

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--ref` | 필수 | 레퍼런스 오디오 파일 |
| `--vocal` | 필수 | 보정할 보컬 파일 |
| `--preset` | `standard` | 보정 강도 (`light` / `standard` / `strong`) |
| `--stem` | false | 보컬 분리 스킵 |
| `--key-shift` | 자동 감지 | 키 시프트 양 (반음 단위) |
| `--out-wav` | `output.wav` | 출력 WAV 파일 경로 |
| `--out-recipe` | `recipe.json` | 출력 recipe.json 경로 |

### GUI

```bash
python -m gui.app
```

GUI에서 가능한 작업:

- 파일 선택 및 처리 실행
- 피치 커브 시각화 (레퍼런스·입력·보정 후)
- 타이밍 워프 시각화
- 세그먼트별 피치·타이밍 보정량 조정
- 보정된 WAV와 recipe.json 내보내기

### recipe.json

Lyra는 보정 데이터를 `recipe.json`으로 출력합니다.
이 파일은 DAW 플러그인이나 다른 도구에서 불러와 활용할 수 있습니다.

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

## 개발

```bash
# 개발용 설치 (테스트 도구 포함)
pip install -e ".[dev]"

# 테스트 실행 (모델 불필요)
pytest tests/test_smoke.py -v

# 통합 테스트 (모델 필요)
pytest tests/test_integration.py -v

# 린트
ruff check .
```

## 라이선스 주의 사항

Lyra는 MIT License로 배포되지만 다음 의존 라이브러리의 라이선스에 유의하세요:

- **pyrubberband**: GPL v2+ — 이 의존성을 포함한 상업적 클로즈드 소스 사용에는 제한이 있습니다
- **PySide6**: LGPL v3 / 상업 라이선스 — 동적 링크를 통해 LGPL 조건 하에 사용 가능
- **RMVPE 모델**: [원본 저장소](https://github.com/yxlllc/RMVPE)의 라이선스를 확인하세요

## 기여

버그 보고, 기능 제안, 풀 리퀘스트를 환영합니다.
자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

## 라이선스

[MIT License](LICENSE) © 2025 Lyra Contributors
