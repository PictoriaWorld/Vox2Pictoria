# TODO

1. Make it easier to download and use

- Installers
- GUI

2. Write tests

- Unit tests for core logic
- End-to-end tests for the full pipeline

3. Cleanup

- Why are we including Vox2Pictoria.pdb in releases?
- Github actions script that creates releases doesn't copy backtick fenced strings correctly - see release 1.0.1

4. Try removing occluded faces hack

The current pipeline renders each structure individually (neighbors hidden from camera via `visible_camera = False`), then patches boundary artifacts using a nearest-neighbor color sampling step (`FixOccludedFaces` in `PostProcessingService`).

In Blender 4.5, neighbors with `visible_camera = False` still participate in diffuse, glossy, and shadow rays. This means boundary faces should already be lit/shadowed correctly without the inpainting hack.

Test: run a full pipeline with `FixOccludedFaces` disabled and compare output. If results are clean, remove:
- `OccludedFacesObjService` (OBJ generation)
- Occluded faces rendering in `main.py`
- `FixOccludedFaces` and `FixPixelColor` in `PostProcessingService`
- `_scanOffsets` array in `PostProcessingService`