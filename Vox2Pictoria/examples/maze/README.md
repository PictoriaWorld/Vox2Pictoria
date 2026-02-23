# Library Maze

Generates MagicaVoxel `.vox` files for a four-zone library maze, then renders them through the Vox2Pictoria pipeline.

## Scripts

| Script | Purpose |
|---|---|
| `generate_part_voxs.py` | Generates individual part `.vox` files (shelves, planters, lamps, tiles, etc.) for preview in MagicaVoxel. Output: `generated/parts/` |
| `generate_zone_voxs.py` | Reads `MAZE_LARGE.png`, assembles parts into four zone `.vox` files. Output: `generated/zones/` |

## Generate zones

```
python maze/generate_zone_voxs.py
```

## Render

All commands run from the repo root (`Vox2Pictoria/`).

> **PowerShell users:** Replace `\` with `` ` `` (backtick) for line continuation, or paste the single-line version.

### Scene test (fast preview)

Bash:
```bash
Vox2Pictoria \
  --combine \
    "maze/generated/zones/zone_pink.vox 560 592" \
    "maze/generated/zones/zone_green.vox 560 -528" \
    "maze/generated/zones/zone_blue.vox -560 592" \
    "maze/generated/zones/zone_yellow.vox -560 -528" \
  --scene-test-run \
  --sun-energy 1 \
  --sun-color 1 0.82 0.58 \
  --ambient-light-strength 0.4 \
  --ambient-light-color 1 0.82 0.58 \
  -o maze/generated/zones
```

PowerShell:
```pwsh
Vox2Pictoria --combine "maze/generated/zones/zone_pink.vox 560 592" "maze/generated/zones/zone_green.vox 560 -528" "maze/generated/zones/zone_blue.vox -560 592" "maze/generated/zones/zone_yellow.vox -560 -528" --scene-test-run --sun-energy 1 --sun-color 1 0.82 0.58 --ambient-light-strength 0.4 --ambient-light-color 1 0.82 0.58 -o maze/generated/zones
```

### Full render

Bash:
```bash
Vox2Pictoria \
  --combine \
    "maze/generated/zones/zone_pink.vox 560 592" \
    "maze/generated/zones/zone_green.vox 560 -528" \
    "maze/generated/zones/zone_blue.vox -560 592" \
    "maze/generated/zones/zone_yellow.vox -560 -528" \
  --full-samples \
  --full-resolution \
  --sun-energy 1 \
  --sun-color 1 0.82 0.58 \
  --ambient-light-strength 0.4 \
  --ambient-light-color 1 0.82 0.58 \
  -o maze/generated/zones
```

PowerShell:
```pwsh
Vox2Pictoria --combine "maze/generated/zones/zone_pink.vox 560 592" "maze/generated/zones/zone_green.vox 560 -528" "maze/generated/zones/zone_blue.vox -560 592" "maze/generated/zones/zone_yellow.vox -560 -528" --full-samples --full-resolution --sun-energy 1 --sun-color 1 0.82 0.58 --ambient-light-strength 0.4 --ambient-light-color 1 0.82 0.58 -o maze/generated/zones
```

### Zone center coordinates

| Zone | Position | Center (MV X, Y) |
|---|---|---|
| pink | top-left | 560, 592 |
| green | top-right | 560, -528 |
| blue | bottom-left | -560, 592 |
| yellow | bottom-right | -560, -528 |