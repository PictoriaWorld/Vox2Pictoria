# TODO

## Setup GitHub Actions for releases

Automate release packaging that bundles Blender with Vox2Pictoria per platform:

1. `dotnet publish` self-contained for each target (`win-x64`, `linux-x64`, `osx-arm64`)
2. Download the matching Blender 4.5 LTS portable/zip for each platform
3. Extract Blender into a `blender/` subdirectory next to the published executable
4. Include Blender's GPL license in the package
5. Zip each platform bundle and upload as a GitHub release artifact

The code already looks for bundled Blender at `<exe dir>/blender/blender[.exe]` and falls back to PATH for development.

## Make it easier to download and use

- Installers
- GUI

## Try removing occluded faces hack

The current pipeline renders each structure individually (neighbors hidden from camera via `visible_camera = False`), then patches boundary artifacts using a nearest-neighbor color sampling step (`FixOccludedFaces` in `PostProcessingService`).

In Blender 4.5, neighbors with `visible_camera = False` still participate in diffuse, glossy, and shadow rays. This means boundary faces should already be lit/shadowed correctly without the inpainting hack.

Test: run a full pipeline with `FixOccludedFaces` disabled and compare output. If results are clean, remove:
- `OccludedFacesObjService` (OBJ generation)
- Occluded faces rendering in `main.py`
- `FixOccludedFaces` and `FixPixelColor` in `PostProcessingService`
- `_scanOffsets` array in `PostProcessingService`
