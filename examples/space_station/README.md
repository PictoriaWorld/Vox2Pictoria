# Space Station

## Overview

Futuristic minimalist space station spawn lobby for Pictoria MMO. Players arrive here and interact with a help desk and 4 info kiosks. Theme: clean white surfaces, green planter beds, emissive light accents.

## Prerequisites
- **Python 3**. Required to run the scene generator script. Download it from [python.org](https://www.python.org/downloads/).
- **Pillow** Python library. Required for logo and icon rasterization. Install it with `pip install Pillow`.
- **ImageMagick** (optional). Used to re-rasterize SVG icons at specific sizes. Download from [imagemagick.org](https://imagemagick.org/script/download.php).

## Quick start

All commands must be run from the `examples/space_station/` directory.

### 1. Generate scene

```
python generate_scene.py
```

This generates `generated/space_station.vox` and `generated/palette.png`.

You can open `space_station.vox` in MagicaVoxel to preview it.

### 2. Test Render

Render the scene as a single, lower quality image to preview it:

PowerShell:
```pwsh
Vox2Pictoria generated/space_station.vox --scene-test-run --sun-energy 6 --sun-color 0.9 0.92 1.0 --ambient-light-strength 0 --ambient-light-color 0.85 0.88 1.0 --emission-camera-cap 100 --emission-bounce-multiplier 2.0 --tone-mapper AgX
```

Bash:
```bash
Vox2Pictoria \
  generated/space_station.vox \
  --scene-test-run \
  --sun-energy 6 \
  --sun-color 0.9 0.92 1.0 \
  --ambient-light-strength 0 \
  --ambient-light-color 0.85 0.88 1.0 \
  --emission-camera-cap 100 \
  --emission-bounce-multiplier 2.0 \
  --tone-mapper AgX
```

Please find explanations for the command options in the [Vox2Pictoria documentation](../../README.md).

### 3. Full Render

Full render (this could take several hours, depending on your hardware):

PowerShell:
```pwsh
Vox2Pictoria generated/space_station.vox --full-samples --full-resolution --sun-energy 6 --sun-color 0.9 0.92 1.0 --ambient-light-strength 0 --ambient-light-color 0.85 0.88 1.0 --emission-camera-cap 100 --emission-bounce-multiplier 2.0 --tone-mapper AgX
```

Bash:
```bash
Vox2Pictoria \
  generated/space_station.vox \
  --full-samples \
  --full-resolution \
  --sun-energy 6 \
  --sun-color 0.9 0.92 1.0 \
  --ambient-light-strength 0 \
  --ambient-light-color 0.85 0.88 1.0 \
  --emission-camera-cap 100 \
  --emission-bounce-multiplier 2.0 \
  --tone-mapper AgX
```
