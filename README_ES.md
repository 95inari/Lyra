# Lyra

**Herramienta de edición vocal automatizada** — Alinea automáticamente la voz de distintas tomas o cantantes al tono y tiempo de una pista de referencia.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

**Idiomas:** [日本語](README.md) | [English](README_EN.md) | [简体中文](README_ZH.md) | [한국어](README_KO.md) | Español

---

## Descripción general

Lyra automatiza el proceso de alinear una grabación vocal con otra (referencia).
Combinando la corrección de tempo basada en DTW con la corrección de tono basada en RMVPE, reduce drásticamente el tiempo dedicado a la edición manual.

**Principales casos de uso:**

- Alinear una toma de un cantante diferente a una interpretación de referencia de la misma canción
- Unificar el tono y el tiempo entre múltiples tomas del mismo cantante
- Generar datos de corrección (`recipe.json`) como preprocesamiento para la mezcla vocal

## Flujo de procesamiento

```
Audio de entrada
  │
  ├─ ① Separación vocal (Demucs htdemucs)  *omitido con --stem
  ├─ ② Estimación de F0 (RMVPE)
  ├─ ③ Detección de onset (librosa)
  ├─ ④ Estimación de desplazamiento de tono / ajuste manual
  ├─ ⑤ Alineación DTW
  └─ ⑥ Renderizado (pyrubberband)
         │
         ├─ WAV corregido
         └─ recipe.json (datos de corrección)
```

## Requisitos

| Elemento | Requisito |
|----------|-----------|
| Python | 3.11 o superior |
| SO | macOS / Linux / Windows |
| GPU | Opcional (funciona en CPU, pero el procesamiento tarda más) |

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/<owner>/lyra.git
cd lyra
```

### 2. Instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Descargar modelos

```bash
python scripts/download_models.py --rmvpe
```

> Descarga el modelo RMVPE (~181 MB) desde Hugging Face.

## Inicio rápido

Una vez completada la instalación, puedes empezar de inmediato con los siguientes comandos.

**CLI (línea de comandos)**

```bash
lyra run --ref reference.wav --vocal new_vocal.wav
```

Al finalizar el procesamiento, se generan `edited_vocal.wav` y `recipe.json` en el directorio actual.

**GUI**

```bash
python -m gui.app
```

O lanzar directamente:

```bash
python gui/app.py
```

Una vez abierta la ventana, selecciona los archivos y haz clic en el botón Ejecutar para iniciar el procesamiento.

---

## Uso

### CLI

```bash
# Uso básico
lyra run --ref reference.wav --vocal new_vocal.wav

# Especificar archivos de salida
lyra run --ref reference.wav --vocal new_vocal.wav \
    --out-wav output.wav --out-recipe recipe.json

# Cambiar preset (light / standard / strong)
lyra run --ref reference.wav --vocal new_vocal.wav --preset strong

# Proporcionar stem vocal directamente (omitir separación)
lyra run --ref reference.wav --vocal vocal_stem.wav --stem

# Especificar desplazamiento de tono manualmente (en semitonos)
lyra run --ref reference.wav --vocal new_vocal.wav --key-shift -2
```

#### Opciones

| Opción | Valor por defecto | Descripción |
|--------|-------------------|-------------|
| `--ref` | obligatorio | Archivo de audio de referencia |
| `--vocal` | obligatorio | Archivo vocal a corregir |
| `--preset` | `standard` | Intensidad de corrección (`light` / `standard` / `strong`) |
| `--stem` | false | Omitir separación vocal |
| `--key-shift` | detección automática | Desplazamiento de tono (en semitonos) |
| `--out-wav` | `output.wav` | Ruta del archivo WAV de salida |
| `--out-recipe` | `recipe.json` | Ruta del archivo recipe.json de salida |

### GUI

```bash
python -m gui.app
```

La GUI permite:

- Selección de archivos y ejecución del procesamiento
- Visualización de curvas de tono (referencia, entrada, corregido)
- Visualización del ajuste de tempo
- Ajuste de corrección de tono y tiempo por segmento
- Exportación de WAV corregido y recipe.json

### recipe.json

Lyra exporta los datos de corrección como `recipe.json`. Este archivo puede ser importado por plugins de DAW u otras herramientas.

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

## Desarrollo

```bash
# Instalar con herramientas de desarrollo
pip install -e ".[dev]"

# Ejecutar pruebas (sin modelos)
pytest tests/test_smoke.py -v

# Pruebas de integración (requiere modelos)
pytest tests/test_integration.py -v

# Lint
ruff check .
```

## Notas sobre licencias

Lyra se distribuye bajo la Licencia MIT, pero ten en cuenta las licencias de las siguientes dependencias:

- **pyrubberband**: GPL v2+ — El uso comercial de código cerrado que incluye esta dependencia está restringido
- **PySide6**: LGPL v3 / Licencia comercial — Disponible bajo términos LGPL mediante enlace dinámico
- **Modelo RMVPE**: Consulta la licencia en el [repositorio original](https://github.com/yxlllc/RMVPE)

## Contribuir

Se aceptan reportes de errores, solicitudes de funciones y pull requests.
Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para más detalles.

## Licencia

[MIT License](LICENSE) © 2025 Lyra Contributors
