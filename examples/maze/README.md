# Maze

A maze scene that demonstrates Vox2Pictoria's `.vox` combining feature.

MagicaVoxel limits scenes to 2000x2000x1000 voxels. Scenes that exceed this — like this maze — must be split into multiple `.vox` files. This example splits the maze into four color-coded zones that are combined at render time using the `--combine` option.

*Note: this example has only been tested on Windows. If you encounter issues on macOS/Linux, feel free to open an issue or submit a PR.*

## Prerequisites

Before using this example, make sure you have completed the following sections in the [main README](../../README.md):

- **[Installation](../../README.md#installation)** — download and set up Vox2Pictoria
- **[MagicaVoxel Scene Setup](../../README.md#magicavoxel-scene-setup)** — understand how MagicaVoxel scenes map to Pictoria (optional, but recommended)

You should also have [MagicaVoxel](https://ephtracy.github.io/) installed if you want to preview the zones before rendering.

## Previewing

Open any of the zone `.vox` files in MagicaVoxel to explore them individually: `zoneBlue.vox`, `zoneGreen.vox`, `zonePink.vox`, `zoneYellow.vox`.

## Rendering

All commands should be run from the `examples/maze/` directory. See [Arguments](../../README.md#arguments) in the main README for details on all command options.

The `--combine` option takes a list of quoted strings, each containing a `.vox` path and its center position in the combined scene.

### 1. Test render

Generate a single overview image at low quality to verify the combined scene looks correct:

PowerShell:
```pwsh
Vox2Pictoria --combine "zonePink.vox 560 592" "zoneGreen.vox 560 -528" "zoneBlue.vox -560 592" "zoneYellow.vox -560 -528" --scene-test-run --sun-energy 1 --sun-color 1 0.82 0.58 --ambient-light-strength 0.4 --ambient-light-color 1 0.82 0.58
```

Bash:
```bash
Vox2Pictoria \
  --combine \
    "zonePink.vox 560 592" \
    "zoneGreen.vox 560 -528" \
    "zoneBlue.vox -560 592" \
    "zoneYellow.vox -560 -528" \
  --scene-test-run \
  --sun-energy 1 \
  --sun-color 1 0.82 0.58 \
  --ambient-light-strength 0.4 \
  --ambient-light-color 1 0.82 0.58
```

The output image will be at `temp/renders/scene.png`.

### 2. Full render

Once satisfied with the preview, run a full quality render:

PowerShell:
```pwsh
Vox2Pictoria --combine "zonePink.vox 560 592" "zoneGreen.vox 560 -528" "zoneBlue.vox -560 592" "zoneYellow.vox -560 -528" --full-samples --full-resolution --sun-energy 1 --sun-color 1 0.82 0.58 --ambient-light-strength 0.4 --ambient-light-color 1 0.82 0.58
```

Bash:
```bash
Vox2Pictoria \
  --combine \
    "zonePink.vox 560 592" \
    "zoneGreen.vox 560 -528" \
    "zoneBlue.vox -560 592" \
    "zoneYellow.vox -560 -528" \
  --full-samples \
  --full-resolution \
  --sun-energy 1 \
  --sun-color 1 0.82 0.58 \
  --ambient-light-strength 0.4 \
  --ambient-light-color 1 0.82 0.58
```

*This can take several hours depending on your hardware.*

The final `.pstr` files will be in `bin/StructureDefinitions/`. See [Usage](../../README.md#usage) in the main README for how to import these into Pictoria.
