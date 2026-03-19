# Snake Arcade Rainforest

A procedurally generated rainforest scene with a Nokia 3310 Snake arcade machine on an elevated platform, reached by an inclined boardwalk winding up through dense jungle. Designed for rendering with Vox2Pictoria using Blender Cycles, with a moonlit night atmosphere and warm torch lighting.

*Note: this example has only been tested on Windows. If you encounter issues on macOS/Linux, feel free to open an issue or submit a PR.*

## Prerequisites

- Python 3.10+
- [Pillow](https://pypi.org/project/Pillow/) (`pip install Pillow`) — used to rasterize the arcade marquee text
- [Silkscreen](https://fonts.google.com/specimen/Silkscreen) font — download and install `Silkscreen-Regular.ttf`. On Windows, the script expects it at `~/AppData/Local/Microsoft/Windows/Fonts/Silkscreen-Regular.ttf` (the default location when installed for the current user).

## Quick start

All commands must be run from the `examples/snake_arcade/` directory.

### 1. Generate scene

```
python generate_scene.py
```

This generates `generated/snake_arcade.vox`.

You can open this file in MagicaVoxel to preview it.

### 2. Test Render

Render the scene as a single, lower quality image to preview it:

PowerShell:
```pwsh
Vox2Pictoria generated/snake_arcade.vox --scene-test-run --sun-energy 1.5 --sun-color 0.4 0.5 1.0 --ambient-light-strength 0.25 --ambient-light-color 0.4 0.5 1.0 --emission-camera-cap 5.0 --emission-bounce-multiplier 4.0 --tone-mapper AgX -o rendered
```

Bash:
```bash
Vox2Pictoria generated/snake_arcade.vox \
  --scene-test-run \
  --sun-energy 1.5 \
  --sun-color 0.4 0.5 1.0 \
  --ambient-light-strength 0.25 \
  --ambient-light-color 0.4 0.5 1.0 \
  --emission-camera-cap 5.0 \
  --emission-bounce-multiplier 4.0 \
  --tone-mapper AgX \
  -o rendered
```

Please find explanations for the command options in the [Vox2Pictoria documentation](../../README.md).

### 3. Full Render

Full render (this could take several hours, depending on your hardware):

PowerShell:
```pwsh
Vox2Pictoria generated/snake_arcade.vox --full-samples --full-resolution --sun-energy 1.5 --sun-color 0.4 0.5 1.0 --ambient-light-strength 0.25 --ambient-light-color 0.4 0.5 1.0 --emission-camera-cap 5.0 --emission-bounce-multiplier 4.0 --tone-mapper AgX -o rendered
```

Bash:
```bash
Vox2Pictoria generated/snake_arcade.vox \
  --full-samples \
  --full-resolution \
  --sun-energy 1.5 \
  --sun-color 0.4 0.5 1.0 \
  --ambient-light-strength 0.25 \
  --ambient-light-color 0.4 0.5 1.0 \
  --emission-camera-cap 5.0 \
  --emission-bounce-multiplier 4.0 \
  --tone-mapper AgX \
  -o rendered
```
