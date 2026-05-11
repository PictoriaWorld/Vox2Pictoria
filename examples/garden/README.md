# Garden

A garden scene. This is also included in the Vox2Pictoria release as a sample scene.

## Prerequisites

Before using this example, make sure you have completed the following sections in the [main README](../../README.md):

- **[Installation](../../README.md#installation)** — download and set up Vox2Pictoria
- **[MagicaVoxel Scene Setup](../../README.md#magicavoxel-scene-setup)** — understand how MagicaVoxel scenes map to Pictoria (optional, but recommended)

You should also have [MagicaVoxel](https://ephtracy.github.io/) installed if you want to preview or edit the scene.

## Previewing

Open `garden.vox` in MagicaVoxel to explore the scene before rendering.

## Rendering

All commands should be run from the `examples/garden/` directory. See [Arguments](../../README.md#arguments) in the main README for details on all command options.

### 1. Test render

Generate a single overview image at low quality to verify the scene looks correct:

```
Vox2Pictoria garden.vox --scene-test-run
```

The output image will be at `temp/renders/scene.png`.

### 2. Full render

Once satisfied with the preview, run a full quality render:

```
Vox2Pictoria garden.vox --full-samples --full-resolution
```

*This can take several hours depending on your hardware.*

The final `.pstr` files will be in `bin/StructureDefinitions/`. See [Usage](../../README.md#usage) in the main README for how to import these into Pictoria.
