"""
recipe/schema.py — recipe.json のデータクラス定義・読み書き
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Segment:
    t0: float
    t1: float
    time_warp_points: list[tuple[float, float]]
    pitch_target_curve: list[tuple[float, float]]  # [(時刻秒, Hz), ...]
    confidence: float
    pitch_strength: float
    time_strength: float
    protect_unvoiced: bool = True

    def to_dict(self) -> dict:
        return {
            "t0": self.t0,
            "t1": self.t1,
            "time_warp_points": [list(p) for p in self.time_warp_points],
            "pitch_target_curve": [list(p) for p in self.pitch_target_curve],
            "confidence": self.confidence,
            "pitch_strength": self.pitch_strength,
            "time_strength": self.time_strength,
            "protect_unvoiced": self.protect_unvoiced,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        return cls(
            t0=d["t0"],
            t1=d["t1"],
            time_warp_points=[tuple(p) for p in d["time_warp_points"]],
            pitch_target_curve=[tuple(p) for p in d["pitch_target_curve"]],
            confidence=d["confidence"],
            pitch_strength=d["pitch_strength"],
            time_strength=d["time_strength"],
            protect_unvoiced=d.get("protect_unvoiced", True),
        )


@dataclass
class Warning:
    t0: float
    t1: float
    reason: str
    detail: str = ""

    def to_dict(self) -> dict:
        return {"t0": self.t0, "t1": self.t1, "reason": self.reason, "detail": self.detail}

    @classmethod
    def from_dict(cls, d: dict) -> "Warning":
        return cls(t0=d["t0"], t1=d["t1"], reason=d["reason"], detail=d.get("detail", ""))


@dataclass
class Recipe:
    version: str
    sample_rate: int
    global_key_shift_semitones: float
    segments: list[Segment]
    warnings: list[Warning] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "sample_rate": self.sample_rate,
            "global_key_shift_semitones": self.global_key_shift_semitones,
            "segments": [s.to_dict() for s in self.segments],
            "warnings": [w.to_dict() for w in self.warnings],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    _SUPPORTED_VERSIONS = {"0.1"}

    @classmethod
    def load(cls, path: str | Path) -> "Recipe":
        path = Path(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"recipe.json の JSON パースに失敗しました: {path}\n  {e}") from e

        try:
            version = data["version"]
            if version not in cls._SUPPORTED_VERSIONS:
                raise ValueError(
                    f"未対応の recipe バージョン: {version!r}。"
                    f"対応バージョン: {cls._SUPPORTED_VERSIONS}"
                )
            return cls(
                version=version,
                sample_rate=int(data["sample_rate"]),
                global_key_shift_semitones=float(data["global_key_shift_semitones"]),
                segments=[Segment.from_dict(s) for s in data["segments"]],
                warnings=[Warning.from_dict(w) for w in data.get("warnings", [])],
            )
        except KeyError as e:
            raise ValueError(
                f"recipe.json に必須フィールドがありません: {e}\nファイル: {path}"
            ) from e
