# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.2.0] - 27-02-2026
### Added
- `.pstr` file generation per structure, output to `bin/StructureDefinitions/`. Each `.pstr` is a gzip-compressed tar archive containing metadata JSON and the rendered image. `.pstr` files can be drag and dropped into Pictoria in Create Structure mode to import the structure.

## [1.1.1] - 25-02-2026
### Added
- Validation that MagicaVoxel top level model/group (these correspond to Pictoria structures) bounding boxes do not intersect.
- Improved error messages for palette mismatches and oversized structures during `.vox` combine.

### Changes
- `.vox` combine now correctly flattens input scene graphs so structures are recognized individually.
- Generated `.vox` files now write MATL chunks for all 256 palette IDs, matching MagicaVoxel's save convention. This fixes MATL mismatch errors when combining a MagicaVoxel-resaved file with an untouched one.

### Fixes
- Fixed release notes ignoring text in backticks.
- Minor cleanup of the maze example.

## [1.1.0] - 24-02-2026
### Added
- Support for emissive, glass, and metal materials.
- `--combine` option to combine multiple `.vox` files into one `.vox` file (works around MagicaVoxel's project dimensions limit).
- `--sun-energy`, `--sun-color`, `--ambient-light-strength`, `--ambient-light-color` options for lighting control.
- `--emission-camera-cap` and `--emission-bounce-multiplier` options for emissive material tuning.
- `--tone-mapper` option to choose between AgX, Filmic, and Standard tone mapping.
- Maze example in `examples/maze/`.

### Changes
- Moved project to `src/Vox2Pictoria/` layout.
- Moved `assets/` and `examples/` to the repository root.
- Improved README documentation.

## [1.0.3] - 13-02-2026
### Changes
- Blender now uses Filmic color management instead of AgX so it matches MagicaVoxel's window preview more closely.

## [1.0.2] - 12-02-2026
### Fixes
- Fixed issue where bundled Blender process was not being terminated on program exit.
- Fixed --full-resolution not working properly.

## [1.0.1] - 12-02-2026
### Changes
- Improved clarity of `--help` output.

## [1.0.0] - 12-02-2026
- Initial release.
