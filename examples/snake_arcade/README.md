# Snake Arcade Rainforest

A rainforest scene with a Nokia 3310 Snake arcade machine on an elevated platform, reached by an inclined boardwalk winding up through dense jungle. Uses a moonlit night atmosphere with warm torch lighting.

*Note: this example has only been tested on Windows. If you encounter issues on macOS/Linux, feel free to open an issue or submit a PR.*

## Prerequisites

Before using this example, make sure you have completed the following sections in the [main README](../../README.md):

- **[Installation](../../README.md#installation)** — download and set up Vox2Pictoria
- **[MagicaVoxel Scene Setup](../../README.md#magicavoxel-scene-setup)** — understand how MagicaVoxel scenes map to Pictoria (optional, but recommended)

You should also have [MagicaVoxel](https://ephtracy.github.io/) installed if you want to preview the scene before rendering.

## Previewing

Open `snakeArcade.vox` in MagicaVoxel to explore the scene before rendering.

## Rendering

All commands should be run from the `examples/snake_arcade/` directory. See [Arguments](../../README.md#arguments) in the main README for details on all command options.

This scene uses custom lighting to achieve its moonlit night look: low blue-tinted sun and ambient light, with higher emission values for the torch glow.

### 1. Test render

Generate a single overview image at low quality to verify the scene looks correct:

PowerShell:
```pwsh
Vox2Pictoria snakeArcade.vox --scene-test-run --sun-energy 3.85 --sun-color 0.4 0.5 1.0 --ambient-light-strength 0.7 --ambient-light-color 0.4 0.5 1.0 --emission-camera-cap 5.0 --emission-bounce-multiplier 4.0 --tone-mapper AgX
```

Bash:
```bash
Vox2Pictoria snakeArcade.vox \
  --scene-test-run \
  --sun-energy 3.85 \
  --sun-color 0.4 0.5 1.0 \
  --ambient-light-strength 0.7 \
  --ambient-light-color 0.4 0.5 1.0 \
  --emission-camera-cap 5.0 \
  --emission-bounce-multiplier 4.0 \
  --tone-mapper AgX
```

The output image will be at `temp/renders/scene.png`.

### 2. Full render

Once satisfied with the preview, run a full quality render:

PowerShell:
```pwsh
Vox2Pictoria snakeArcade.vox --full-samples --full-resolution --sun-energy 3.85 --sun-color 0.4 0.5 1.0 --ambient-light-strength 0.7 --ambient-light-color 0.4 0.5 1.0 --emission-camera-cap 5.0 --emission-bounce-multiplier 4.0 --tone-mapper AgX
```

Bash:
```bash
Vox2Pictoria snakeArcade.vox \
  --full-samples \
  --full-resolution \
  --sun-energy 3.85 \
  --sun-color 0.4 0.5 1.0 \
  --ambient-light-strength 0.7 \
  --ambient-light-color 0.4 0.5 1.0 \
  --emission-camera-cap 5.0 \
  --emission-bounce-multiplier 4.0 \
  --tone-mapper AgX
```

*This can take several hours depending on your hardware.*

The final `.pstr` files will be in `bin/StructureDefinitions/`. See [Usage](../../README.md#usage) in the main README for how to import these into Pictoria.
