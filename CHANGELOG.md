# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.6.2] - 20-03-2026
### Fixed
- Structures with numeric name suffixes (e.g. `overgrowth_4`) were assigned wrong volume types instead of defaulting to cuboid.

## [1.6.1] - 19-03-2026
### Fixed
- `Unsupported volume type` errors.

## [1.6.0] - 19-03-2026
### Added
- Structures are now checked for extending below ground and violating Pictoria's height limits.
- `--no-validation` option to skip all structure validation (intersections, property bounds, and height limits).

## [1.5.1] - 14-03-2026
### Fixed
- `.ppty` and `.pstr` files now include the normalized MD5 base64 hash for structure images (`imageNormalizedMd5Base64`). Previously this field was always empty, causing import validation to fail in Pictoria.

## [1.5.0] - 11-03-2026
### Added
- `.ppty` file generation, output to `bin/PropertyDefinition/`. Each `.ppty` is a gzip-compressed tar archive bundling all structures in the scene with property-level metadata (tile dimensions). `.ppty` files can be drag and dropped into Pictoria in Create Property mode to import the property.
- Integration tests for `DefinitionService` (`.pstr` and `.ppty` generation).

## [1.4.0] - 10-03-2026
### Added
- `formatVersion` field in generated `.pstr` files. Set to `1` for the current format.

## [1.3.0] - 10-03-2026
### Changes
- .pstr coordinates are now relative to the MagicaVoxel scene's center in the horizontal plane. This allows us to remove the `--min-tile-x` and `--min-tile-z` options, simplifying the workflow - e.g. you no longer need to
re-run Vox2Pictoria if your property's tile location changes.

### Removed
- `--min-tile-x` and `--min-tile-z` CLI arguments. Pictoria now handles the coordinate offset on import.

## [1.2.1] - 27-02-2026
### Added
- `--no-render` option to regenerate structure_infos.json and .pstr files only. Useful for updating --min-tile-x/z without re-rendering. Rendered images must already exist on disk.
- `-v`/`--version` flag that prints the assembly version.

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
