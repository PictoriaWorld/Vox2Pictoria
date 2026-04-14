# Maze

## Overview

MagicaVoxel maze scene designed for testing Vox2Pictoria's `.vox` combining feature.

Why combine multiple .vox files? MagicaVoxel limits scenes to 2000x2000x1000. Scenes may exceed that - like this maze scene. In this case, we split the maze into four parts. We've arbitrarily named each part a "zone".

*Note: this example has only been tested on Windows, if you encounter issues on macOS/Linux, feel free to open an issue or submit a PR.*

## Prerequisites
- **Python 3**. Required to run the zone generator script. Download it from [python.org](https://www.python.org/downloads/).
- **Pillow** Python library. Required to run the zone generator script. Install it with `pip install Pillow`.
- **Cinzel** font. Required for text in the scene. Download it from [Google Fonts](https://fonts.google.com/specimen/Cinzel), unzip, and install `Cinzel-VariableFont_wght.ttf`.

## Quick start

All commands must be run from the `examples/` directory.

### 1. Generate zones

```
python maze/generate_zone_voxs.py
```

This generates four `.vox` files in `maze/generated/zones/`: `zoneBlue.vox`, `zoneGreen.vox`, `zonePink.vox`, and `zoneYellow.vox`.

You can open these files in MagicaVoxel to preview them.

### 2. Test Render

Render the combined scene as a single, lower quality image to preview it:

PowerShell:
```pwsh
Vox2Pictoria --combine "maze/generated/zones/zonePink.vox 560 592" "maze/generated/zones/zoneGreen.vox 560 -528" "maze/generated/zones/zoneBlue.vox -560 592" "maze/generated/zones/zoneYellow.vox -560 -528" --scene-test-run --sun-energy 1 --sun-color 1 0.82 0.58 --ambient-light-strength 0.4 --ambient-light-color 1 0.82 0.58
```

Bash:
```bash
Vox2Pictoria \
  --combine \
    "maze/generated/zones/zonePink.vox 560 592" \
    "maze/generated/zones/zoneGreen.vox 560 -528" \
    "maze/generated/zones/zoneBlue.vox -560 592" \
    "maze/generated/zones/zoneYellow.vox -560 -528" \
  --scene-test-run \
  --sun-energy 1 \
  --sun-color 1 0.82 0.58 \
  --ambient-light-strength 0.4 \
  --ambient-light-color 1 0.82 0.58
```

Please find explanations for the command options in the [Vox2Pictoria documentation](../../README.md).

### 3. Full Render

Full render (this could take several hours, depending on your hardware):

PowerShell:
```pwsh
Vox2Pictoria --combine "maze/generated/zones/zonePink.vox 560 592" "maze/generated/zones/zoneGreen.vox 560 -528" "maze/generated/zones/zoneBlue.vox -560 592" "maze/generated/zones/zoneYellow.vox -560 -528" --full-samples --full-resolution --sun-energy 1 --sun-color 1 0.82 0.58 --ambient-light-strength 0.4 --ambient-light-color 1 0.82 0.58
```

Bash:
```bash
Vox2Pictoria \
  --combine \
    "maze/generated/zones/zonePink.vox 560 592" \
    "maze/generated/zones/zoneGreen.vox 560 -528" \
    "maze/generated/zones/zoneBlue.vox -560 592" \
    "maze/generated/zones/zoneYellow.vox -560 -528" \
  --full-samples \
  --full-resolution \
  --sun-energy 1 \
  --sun-color 1 0.82 0.58 \
  --ambient-light-strength 0.4 \
  --ambient-light-color 1 0.82 0.58
```