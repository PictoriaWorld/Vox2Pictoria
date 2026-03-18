# Snake Arcade Rainforest

A surrealist 32x32-tile property with a dense rainforest, rickety boardwalk,
giant snake skull, and a gleaming Snake arcade machine.

## Prerequisites

- Python 3.10+
- No additional dependencies (uses only stdlib)

## Generation

### Phase 1: Individual Parts (for preview in MagicaVoxel)

```bash
cd examples/snake_arcade
python generate_parts.py
```

Output: `generated/parts/` — open any `.vox` file in MagicaVoxel to preview.

### Phase 2: Full Scene Assembly

```bash
python generate_scene.py
```

Output: `generated/snake_arcade.vox`

### Test Render

```bash
dotnet run -- --input examples/snake_arcade/generated/snake_arcade.vox --scene-test-run
```

Verify no bounding box overlap errors and height limits are respected.
Check that the arcade is a separate structure in `bin/structure_infos.json`.

### Full Render

```bash
dotnet run -- --input examples/snake_arcade/generated/snake_arcade.vox \
  --sun-angle 35 --sun-warmth 0.15 --ambient-color "0.08,0.12,0.06" \
  --emission-camera-cap 3.5 --emission-bounce-multiplier 2.0
```

Warm sun with green-tinted ambient for jungle atmosphere.
