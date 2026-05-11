# Space Station

A futuristic minimalist space station spawn lobby for the Pictoria MMO. Clean white surfaces, green planter beds, and emissive light accents. Players arrive here and interact with a help desk and 4 info kiosks.

*Note: this example has only been tested on Windows. If you encounter issues on macOS/Linux, feel free to open an issue or submit a PR.*

## Prerequisites

Before using this example, make sure you have completed the following sections in the [main README](../../README.md):

- **[Installation](../../README.md#installation)** — download and set up Vox2Pictoria
- **[MagicaVoxel Scene Setup](../../README.md#magicavoxel-scene-setup)** — understand how MagicaVoxel scenes map to Pictoria (optional, but recommended)

You should also have [MagicaVoxel](https://ephtracy.github.io/) installed if you want to preview the scene before rendering.

## Previewing

Open `spaceStation.vox` in MagicaVoxel to explore the scene before rendering.

## Rendering

All commands should be run from the `examples/space_station/` directory. See [Arguments](../../README.md#arguments) in the main README for details on all command options.

This scene uses bright sun energy with zero ambient light and a high emission camera cap, relying on the emissive surfaces to provide most of the interior lighting.

### 1. Test render

Generate a single overview image at low quality to verify the scene looks correct:

PowerShell:
```pwsh
Vox2Pictoria spaceStation.vox --scene-test-run --sun-energy 6 --sun-color 0.9 0.92 1.0 --ambient-light-strength 0 --ambient-light-color 0.85 0.88 1.0 --emission-camera-cap 100 --emission-bounce-multiplier 2.0 --tone-mapper AgX
```

Bash:
```bash
Vox2Pictoria spaceStation.vox \
  --scene-test-run \
  --sun-energy 6 \
  --sun-color 0.9 0.92 1.0 \
  --ambient-light-strength 0 \
  --ambient-light-color 0.85 0.88 1.0 \
  --emission-camera-cap 100 \
  --emission-bounce-multiplier 2.0 \
  --tone-mapper AgX
```

The output image will be at `temp/renders/scene.png`.

### 2. Full render

Once satisfied with the preview, run a full quality render:

PowerShell:
```pwsh
Vox2Pictoria spaceStation.vox --full-samples --full-resolution --sun-energy 6 --sun-color 0.9 0.92 1.0 --ambient-light-strength 0 --ambient-light-color 0.85 0.88 1.0 --emission-camera-cap 100 --emission-bounce-multiplier 2.0 --tone-mapper AgX
```

Bash:
```bash
Vox2Pictoria spaceStation.vox \
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

*This can take several hours depending on your hardware.*

The final `.pstr` files will be in `bin/StructureDefinitions/`. See [Usage](../../README.md#usage) in the main README for how to import these into Pictoria.
