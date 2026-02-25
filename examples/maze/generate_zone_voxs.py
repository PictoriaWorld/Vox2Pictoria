"""Generate multi-model .vox files for each maze zone from maze_layout.png.

Reads the 70x70 maze image (3px border around 64x64 grid), classifies tiles by zone and type,
generates shelf and floor geometry, and writes per-zone .vox files.

Coordinate system (MagicaVoxel axes):
  Image up    = +x
  Image down  = -x
  Image left  = +y
  Image right = -y
  Image pixel (row, col): row increases downward (-x), col increases rightward (-y)

Light pixels = shelves, dark pixels = floor/empty.

Structure rules:
  - Shelves decomposed into rectangular groups -> Pictoria structures (<=512) -> MV models (<=256)
  - Floor: filled 512x512x1 Pictoria structures covering full zone + 3-tile border
  - Floor tiles placed under shelves too
"""

import struct
import os
import random
import sys

try:
    from PIL import Image
except ImportError:
    print("Pillow required: pip install Pillow")
    sys.exit(1)

from generate_part_voxs import (
    make_palette,
    write_chunk,
    _write_dict,
    build_lamp,
    generate_shelf_3conn,
    generate_shelf_2conn_line,
    generate_shelf_2conn_corner,
    generate_shelf_1conn,
    generate_shelf_1conn_2height,
    generate_shelf_2conn_3to2height,
    generate_entrance_plaque,
    generate_square_planter,
    generate_sandstone_planter,
    generate_tile,
    generate_staircase_treads,
    generate_staircase_top_tread,
    generate_staircase_balustrade,
    SHELF_STRUCT_TOP,
    SHELF_STRUCT_TOP_2H,
    TILE_LIGHT,
    VoxelModel,
    GRAIN_DARK_WOOD,
    METAL_DARK, METAL_MEDIUM, METAL_LIGHT,
    LAMP_WARM,
    WOOD_DARK,
    WOOD_DARKER,
    WOOD_DARKEST,
)


# ============================================================
# Pixel color -> (zone, tile_type) mapping
# ============================================================

PIXEL_MAP = {
    # Light = shelf, dark = floor/empty
    (255, 179, 251): ('pink', 'shelf'),
    (255, 180, 251): ('pink', 'shelf'),
    (255, 181, 252): ('pink', 'shelf'),
    (76, 0, 72):     ('pink', 'floor'),
    (75, 0, 71):     ('pink', 'floor'),
    (74, 0, 71):     ('pink', 'floor'),
    (179, 255, 193): ('green', 'shelf'),
    (180, 255, 194): ('green', 'shelf'),
    (181, 255, 194): ('green', 'shelf'),
    (0, 76, 14):     ('green', 'floor'),
    (0, 75, 14):     ('green', 'floor'),
    (0, 74, 13):     ('green', 'floor'),
    (179, 179, 255): ('blue', 'shelf'),
    (180, 180, 255): ('blue', 'shelf'),
    (0, 0, 76):      ('blue', 'floor'),
    (0, 0, 75):      ('blue', 'floor'),
    (0, 0, 74):      ('blue', 'floor'),
    (0, 0, 200):     ('blue', 'shelf_3to2'),   # blue 3-to-2 height transition
    (0, 0, 150):     ('blue', 'shelf_2h'),     # blue 2-height shelf
    (255, 253, 179): ('yellow', 'shelf'),
    (255, 253, 180): ('yellow', 'shelf'),
    (255, 200, 0):   ('yellow', 'shelf_3to2'),   # bright gold = 3-to-2 height transition
    (200, 200, 0):   ('yellow', 'shelf_3to2'),   # dark gold variant
    (255, 150, 0):   ('yellow', 'shelf_2h'),     # orange = 2-height shelf
    (200, 150, 0):   ('yellow', 'shelf_2h'),     # dark orange variant
    (76, 74, 0):     ('yellow', 'floor'),
    (75, 73, 0):     ('yellow', 'floor'),
    (74, 72, 0):     ('yellow', 'floor'),
    (179, 76, 14):   (None, 'stair'),
    (255, 74, 0):    (None, 'stair'),
}


# ============================================================
# Direction system (MagicaVoxel axes, Y flipped)
# ============================================================

DIRECTION_DELTAS = {
    '+x': (-1, 0),   # up in image
    '-x': (1, 0),    # down in image
    '+y': (0, -1),   # left in image
    '-y': (0, 1),    # right in image
}

ALL_DIRS = frozenset(['+x', '-x', '+y', '-y'])


# ============================================================
# Rotation lookup tables
# ============================================================

# 1conn canonical: single connection at -y
ROTATION_1CONN = {
    frozenset(['-y']): 0,
    frozenset(['+x']): 1,
    frozenset(['+y']): 2,
    frozenset(['-x']): 3,
}

# 2conn_line canonical: connections -y, +y
ROTATION_2CONN_LINE = {
    frozenset(['-y', '+y']): 0,
    frozenset(['+x', '-x']): 1,
}

# 2conn_corner canonical: connections -y, +x
ROTATION_2CONN_CORNER = {
    frozenset(['-y', '+x']): 0,
    frozenset(['+x', '+y']): 1,
    frozenset(['+y', '-x']): 2,
    frozenset(['-y', '-x']): 3,
}

# 3conn canonical: connections -y, +y, +x. Missing = -x (books face)
ROTATION_3CONN = {
    '-x': 0,
    '-y': 1,
    '+x': 2,
    '+y': 3,
}

# 2conn_3to2height canonical: connections along Â±y, short side = +y (S face = end panel)
ROTATION_2CONN_3TO2 = {
    '+y': 0,   # short side = S (canonical)
    '-x': 1,   # short side = W
    '-y': 2,   # short side = N
    '+x': 3,   # short side = E
}

# Shelf-like types for neighbor detection (all count as "shelf" connections)
SHELF_LIKE_TYPES = {'shelf', 'shelf_3to2', 'shelf_2h'}


# ============================================================
# Image parsing
# ============================================================

def parse_maze_image(filepath):
    """Parse maze_layout.png into a 64x64 grid."""
    img = Image.open(filepath).convert('RGB')
    if img.size != (70, 70):
        print(f"Warning: Expected 70x70 image, got {img.size}", flush=True)

    grid = {}
    unknown_colors = set()
    for row in range(64):
        for col in range(64):
            rgb = img.getpixel((col + 3, row + 3))[:3]
            if rgb in PIXEL_MAP:
                grid[(row, col)] = PIXEL_MAP[rgb]
            else:
                unknown_colors.add(rgb)

    if unknown_colors:
        print(f"Warning: Unknown pixel colors: {unknown_colors}", flush=True)
    return grid


def extract_zones(grid):
    """Split grid into per-zone dicts with zone-local coords."""
    zone_pixels = {}
    for (row, col), (zone, tile_type) in grid.items():
        if zone is None:
            continue
        zone_pixels.setdefault(zone, {})[(row, col)] = tile_type

    zones = {}
    for zone_name, pixels in zone_pixels.items():
        rows = [r for r, c in pixels]
        cols = [c for r, c in pixels]
        min_row, max_row = min(rows), max(rows)
        min_col, max_col = min(cols), max(cols)

        local = {}
        for (r, c), tt in pixels.items():
            local[(r - min_row, c - min_col)] = tt

        zones[zone_name] = {
            'tiles': local,
            'min_row': min_row,
            'min_col': min_col,
            'num_rows': max_row - min_row + 1,
            'num_cols': max_col - min_col + 1,
        }
    return zones


# ============================================================
# Shelf classification
# ============================================================

def classify_shelves(zone_tiles, global_shelves=None, zone_row_offset=0, zone_col_offset=0, global_grid=None):
    """Classify each shelf tile by type and rotation.

    If global_shelves is provided, neighbor checks use it (in global coords)
    so that shelves at zone edges see connections to adjacent zones.
    global_grid maps (row,col) -> (zone, tile_type) for cross-zone type lookups.
    Handles shelf, shelf_3to2, and shelf_2h tile types.
    """
    shelf_map = {}

    for (row, col), tile_type in zone_tiles.items():
        if tile_type not in SHELF_LIKE_TYPES:
            continue

        # shelf_2h tiles: always 1conn_2height
        if tile_type == 'shelf_2h':
            connected = set()
            for dir_name, (dr, dc) in DIRECTION_DELTAS.items():
                if global_shelves is not None:
                    gr = row + zone_row_offset + dr
                    gc = col + zone_col_offset + dc
                    if (gr, gc) in global_shelves:
                        connected.add(dir_name)
                else:
                    if zone_tiles.get((row + dr, col + dc)) in SHELF_LIKE_TYPES:
                        connected.add(dir_name)
            conn = frozenset(connected)
            steps = ROTATION_1CONN.get(conn, 0)
            shelf_map[(row, col)] = ('1conn_2height', steps)
            continue

        # shelf_3to2 tiles: always 2conn_3to2height
        if tile_type == 'shelf_3to2':
            # Determine which side is the "short" (2h) side
            # Use global_grid for cross-zone type detection; prioritize shelf_2h
            connected = set()
            short_side = None
            floor_side = None
            for dir_name, (dr, dc) in DIRECTION_DELTAS.items():
                nr, nc = row + dr, col + dc
                # Check local zone tiles first
                neighbor_type = zone_tiles.get((nr, nc))
                # Fall back to global grid for cross-zone neighbors
                if neighbor_type is None and global_grid is not None:
                    gr, gc = row + zone_row_offset + dr, col + zone_col_offset + dc
                    entry = global_grid.get((gr, gc))
                    if entry is not None:
                        neighbor_type = entry[1]
                if neighbor_type in SHELF_LIKE_TYPES:
                    connected.add(dir_name)
                if neighbor_type == 'shelf_2h':
                    short_side = dir_name
                elif neighbor_type == 'floor' and floor_side is None:
                    floor_side = dir_name
            # Prefer shelf_2h; fall back to floor
            if short_side is None:
                short_side = floor_side
            # If still nothing, pick first non-shelf direction
            if short_side is None:
                for dir_name, (dr, dc) in DIRECTION_DELTAS.items():
                    nr, nc = row + dr, col + dc
                    neighbor_type = zone_tiles.get((nr, nc))
                    if neighbor_type is None and global_grid is not None:
                        gr, gc = row + zone_row_offset + dr, col + zone_col_offset + dc
                        entry = global_grid.get((gr, gc))
                        if entry is not None:
                            neighbor_type = entry[1]
                    if neighbor_type not in SHELF_LIKE_TYPES and neighbor_type != 'shelf_3to2':
                        short_side = dir_name
                        break
            if short_side is None:
                short_side = '+y'  # fallback
            steps = ROTATION_2CONN_3TO2.get(short_side, 0)
            shelf_map[(row, col)] = ('2conn_3to2height', steps)
            continue

        # Regular shelf tiles
        connected = set()
        for dir_name, (dr, dc) in DIRECTION_DELTAS.items():
            if global_shelves is not None:
                gr = row + zone_row_offset + dr
                gc = col + zone_col_offset + dc
                if (gr, gc) in global_shelves:
                    connected.add(dir_name)
            else:
                if zone_tiles.get((row + dr, col + dc)) in SHELF_LIKE_TYPES:
                    connected.add(dir_name)

        n = len(connected)
        conn = frozenset(connected)

        if n == 0:
            print(f"  Warning: Isolated shelf at ({row}, {col}), using 1conn facing -y", flush=True)
            shelf_map[(row, col)] = ('1conn', 0)
        elif n == 1:
            steps = ROTATION_1CONN.get(conn)
            if steps is not None:
                shelf_map[(row, col)] = ('1conn', steps)
            else:
                print(f"  Warning: Unexpected 1conn at ({row}, {col}): {connected}", flush=True)
        elif n == 2:
            if conn in ROTATION_2CONN_LINE:
                shelf_map[(row, col)] = ('2conn_line', ROTATION_2CONN_LINE[conn])
            elif conn in ROTATION_2CONN_CORNER:
                shelf_map[(row, col)] = ('2conn_corner', ROTATION_2CONN_CORNER[conn])
            else:
                print(f"  Warning: Unexpected 2conn at ({row}, {col}): {connected}", flush=True)
        elif n == 3:
            missing = next(iter(ALL_DIRS - connected))
            steps = ROTATION_3CONN.get(missing)
            if steps is not None:
                shelf_map[(row, col)] = ('3conn', steps)
            else:
                print(f"  Warning: Unexpected 3conn at ({row}, {col}): {missing}", flush=True)
        else:
            print(f"  Warning: 4-connection shelf at ({row}, {col})", flush=True)

    return shelf_map


# ============================================================
# Voxel rotation
# ============================================================

def rotate_voxels_cw(voxel_dict, steps):
    """Rotate voxels by 90 * steps CW within 32x32 footprint.

    Formula per step: (x, y, z) -> (31-y, x, z)
    """
    steps = steps % 4
    if steps == 0:
        return voxel_dict

    result = {}
    for (x, y, z), c in voxel_dict.items():
        rx, ry = x, y
        for _ in range(steps):
            rx, ry = 31 - ry, rx
        result[(rx, ry, z)] = c
    return result


# ============================================================
# Shelf generators lookup
# ============================================================

SHELF_GENERATORS = {
    '3conn':              generate_shelf_3conn,
    '2conn_line':         generate_shelf_2conn_line,
    '2conn_corner':       generate_shelf_2conn_corner,
    '1conn':              generate_shelf_1conn,
    '1conn_2height':      generate_shelf_1conn_2height,
    '2conn_3to2height':   generate_shelf_2conn_3to2height,
}


# ============================================================
# Nook detection (3x1 floor alcoves for rectangular planters)
# ============================================================

# Nook patterns: offsets relative to anchor floor tile (r, c).
# Requires 3 back shelves + 2 side shelves (5 total).
NOOK_PATTERNS = {
    'south': {  # open toward +row
        'floor': [(0, 0), (0, 1), (0, 2)],
        'shelves': [(-1, 0), (-1, 1), (-1, 2), (0, -1), (0, 3)],
        'open': [(1, 0), (1, 1), (1, 2)],
    },
    'north': {  # open toward -row
        'floor': [(0, 0), (0, 1), (0, 2)],
        'shelves': [(1, 0), (1, 1), (1, 2), (0, -1), (0, 3)],
        'open': [(-1, 0), (-1, 1), (-1, 2)],
    },
    'east': {  # open toward +col
        'floor': [(0, 0), (1, 0), (2, 0)],
        'shelves': [(0, -1), (1, -1), (2, -1), (-1, 0), (3, 0)],
        'open': [(0, 1), (1, 1), (2, 1)],
    },
    'west': {  # open toward -col
        'floor': [(0, 0), (1, 0), (2, 0)],
        'shelves': [(0, 1), (1, 1), (2, 1), (-1, 0), (3, 0)],
        'open': [(0, -1), (1, -1), (2, -1)],
    },
}

# Planter voxel rotation per nook orientation.
# (ax, bx, cx, ay, by, cy): model_x = ax*px + bx*py + cx, model_y = ay*px + by*py + cy
# Planter model is 96 (x) x 32 (y). After rotation: south/north = 32x96, east/west = 96x32.
NOOK_PLANTER_ROT = {
    'south': (0, -1, 31,  -1, 0, 95),   # mx = 31-py, my = 95-px
    'north': (0, 1, 0,    -1, 0, 95),   # mx = py,    my = 95-px
    'east':  (-1, 0, 95,  0, -1, 31),   # mx = 95-px, my = 31-py
    'west':  (-1, 0, 95,  0, 1, 0),     # mx = 95-px, my = py
}


def detect_nooks(zone_tiles):
    """Find 3x1 floor nooks surrounded by shelves on 3 sides."""
    floor_set = {pos for pos, tt in zone_tiles.items() if tt == 'floor'}
    shelf_set = {pos for pos, tt in zone_tiles.items() if tt in SHELF_LIKE_TYPES}

    nooks = []
    claimed_floor = set()

    for r, c in sorted(floor_set):
        if (r, c) in claimed_floor:
            continue
        for orient, pat in NOOK_PATTERNS.items():
            floor_tiles = [(r + dr, c + dc) for dr, dc in pat['floor']]
            shelf_tiles = [(r + dr, c + dc) for dr, dc in pat['shelves']]
            open_tiles = [(r + dr, c + dc) for dr, dc in pat['open']]

            if (all(f in floor_set and f not in claimed_floor for f in floor_tiles)
                    and all(s in shelf_set for s in shelf_tiles)
                    and all(o not in shelf_set for o in open_tiles)):
                nooks.append({
                    'orientation': orient,
                    'floor': floor_tiles,
                })
                claimed_floor.update(floor_tiles)
                break

    return nooks


# ============================================================
# Structure decomposition
# ============================================================

MAX_PICT_TILES = 16   # 512 / 32 = max tiles per Pictoria axis
MAX_MV_TILES = 8      # 256 / 32 = max tiles per MV model axis


def decompose_into_rectangles(positions):
    """Greedy rectangle decomposition of a set of positions."""
    remaining = set(positions)
    rects = []
    while remaining:
        r, c = min(remaining)
        # Expand right
        c_end = c
        while (r, c_end + 1) in remaining:
            c_end += 1
        # Expand down
        r_end = r
        can_expand = True
        while can_expand:
            for ci in range(c, c_end + 1):
                if (r_end + 1, ci) not in remaining:
                    can_expand = False
                    break
            if can_expand:
                r_end += 1
        rects.append((r, c, r_end, c_end))
        for ri in range(r, r_end + 1):
            for ci in range(c, c_end + 1):
                remaining.discard((ri, ci))
    return rects


def tile_range_to_mv_regions(r1, c1, r2, c2):
    """Split tile range into MV model regions (max 8 tiles per axis)."""
    regions = []
    for mr in range(r1, r2 + 1, MAX_MV_TILES):
        for mc in range(c1, c2 + 1, MAX_MV_TILES):
            mr_end = min(mr + MAX_MV_TILES - 1, r2)
            mc_end = min(mc + MAX_MV_TILES - 1, c2)
            regions.append((mr, mc, mr_end, mc_end))
    return regions


def split_into_structures(r1, c1, r2, c2, tile_positions=None):
    """Split a tile rectangle into Pictoria structures containing MV models.

    Returns list of structures. Each structure is a list of MV regions.
    If tile_positions is given, skip MV regions with no tiles.
    """
    structures = []

    for pr in range(r1, r2 + 1, MAX_PICT_TILES):
        for pc in range(c1, c2 + 1, MAX_PICT_TILES):
            pr_end = min(pr + MAX_PICT_TILES - 1, r2)
            pc_end = min(pc + MAX_PICT_TILES - 1, c2)

            mv_regions = []
            for mr, mc, mr_end, mc_end in tile_range_to_mv_regions(pr, pc, pr_end, pc_end):
                if tile_positions is not None:
                    has_tile = any(
                        (ri, ci) in tile_positions
                        for ri in range(mr, mr_end + 1)
                        for ci in range(mc, mc_end + 1)
                    )
                    if not has_tile:
                        continue
                mv_regions.append((mr, mc, mr_end, mc_end))

            if mv_regions:
                structures.append(mv_regions)

    return structures


# ============================================================
# Model building (voxel generation + serialization)
# ============================================================

def _append_voxels(xyzi_bytes, voxel_dict, lx_base, ly_base, maxes, z_offset=0):
    """Append voxels to bytearray, update maxes. Returns count."""
    count = 0
    max_lx, max_ly, max_z = maxes
    for (vx, vy, vz), c in voxel_dict.items():
        lx = lx_base + vx
        ly = ly_base + vy
        lz = vz + z_offset
        xyzi_bytes.extend((lx, ly, lz, c))
        if lx > max_lx: max_lx = lx
        if ly > max_ly: max_ly = ly
        if lz > max_z: max_z = lz
        count += 1
    return count, (max_lx, max_ly, max_z)


def build_shelf_model(mr, mc, mr_end, mc_end, shelf_map, palette, seed_base,
                      outer_ring=frozenset(), bridge_tiles=frozenset()):
    """Build a shelf MV model covering tiles (mr,mc) to (mr_end,mc_end)."""
    xyzi_bytes = bytearray()
    maxes = (0, 0, 0)
    voxel_count = 0

    for row in range(mr, mr_end + 1):
        for col in range(mc, mc_end + 1):
            if (row, col) not in shelf_map:
                continue

            shelf_type, cw_steps = shelf_map[(row, col)]
            rng = random.Random(seed_base + row * 997 + col * 7919)
            gen_fn = SHELF_GENERATORS.get(shelf_type)
            if gen_fn is None:
                continue

            m = gen_fn(palette, None, rng, save=False)

            # Place planter on special shelves outside outer ring and not under bridge
            if ((row, col) not in outer_ring
                    and (row, col) not in bridge_tiles
                    and shelf_type in PLANTER_SHELF_TYPES):
                planter_rng = random.Random(seed_base + row * 3571 + col * 6197 + 99)
                planter_m = generate_square_planter(palette, None, planter_rng, save=False)

                # Add lamp inside planter on dead-end shelves only
                if shelf_type == '1conn':
                    lamp_m = VoxelModel()
                    build_lamp(lamp_m, base_z=0)
                    for (lx, ly, lz), c in lamp_m._v.items():
                        planter_m._v[(lx + 13, ly + 13, lz + 4)] = c

                for (px, py, pz), c in planter_m._v.items():
                    m._v[(px, py, pz + SHELF_STRUCT_TOP)] = c

            voxels = rotate_voxels_cw(m._v, cw_steps)

            lx_base = (mr_end - row) * 32
            ly_base = (mc_end - col) * 32
            cnt, maxes = _append_voxels(xyzi_bytes, voxels, lx_base, ly_base, maxes)
            voxel_count += cnt
            del m, voxels

    if voxel_count == 0:
        return None
    return _serialize_model(xyzi_bytes, voxel_count, maxes)


def build_planter_model(nook, palette, seed_base):
    """Build a standalone rectangular planter model, rotated for the nook orientation."""
    anchor_r, anchor_c = nook['floor'][0]
    planter_rng = random.Random(seed_base + anchor_r * 4517 + anchor_c * 7723 + 77)
    planter_m = generate_sandstone_planter(palette, None, planter_rng, save=False)

    ax, bx, cx, ay, by, cy = NOOK_PLANTER_ROT[nook['orientation']]

    xyzi_bytes = bytearray()
    maxes = (0, 0, 0)
    voxel_count = 0

    for (px, py, pz), c in planter_m._v.items():
        mx = ax * px + bx * py + cx
        my = ay * px + by * py + cy
        mz = pz
        xyzi_bytes.extend((mx, my, mz, c))
        if mx > maxes[0]: maxes = (mx, maxes[1], maxes[2])
        if my > maxes[1]: maxes = (maxes[0], my, maxes[2])
        if mz > maxes[2]: maxes = (maxes[0], maxes[1], mz)
        voxel_count += 1

    if voxel_count == 0:
        return None
    return _serialize_model(xyzi_bytes, voxel_count, maxes)


def build_staircase_models(palette, seed_base, ascend_dir):
    """Build staircase as two separate models (treads + top tread), rotated for placement.

    ascend_dir:
      'down' = ascends toward -lx (green zone, toward yellow)
      'up'   = ascends toward +lx (yellow zone, toward green)

    Each model has clean local coords starting at (0,0,0) with rotation applied.
    Explicit sizes match standalone .vox dimensions (rotated: y->lx, x->ly, z->lz).
    All positioning offsets (centering, floor, part placement) are returned separately
    for the caller to apply via world translation.

    Returns list of (model_dict, lx_offset, z_offset) tuples.
    ly_offset=16 (centering 64 in 96) is constant and handled by the caller.
    """
    rng_treads = random.Random(seed_base + 55001)
    rng_top = random.Random(seed_base + 55002)
    treads_m = generate_staircase_treads(palette, None, rng_treads, save=False)
    top_m = generate_staircase_top_tread(palette, None, rng_top, save=False)

    # Standalone sizes: treads (64, 88, 108), top tread (64, 8, 11)
    # After rotation (x->ly, y->lx): treads (88, 64, 108), top tread (8, 64, 11)
    #
    # In the combined 96-voxel lx span:
    #   'down': top tread at lx 0..7, treads at lx 8..95 â†’ offsets (8, 0)
    #   'up':   treads at lx 0..87, top tread at lx 88..95 â†’ offsets (0, 88)
    # Top tread z offset is always 97 (aligns with last tread surface).
    if ascend_dir == 'down':
        parts = [
            # (voxels, y_max for flip, explicit_maxes, lx_offset, z_offset)
            (treads_m._v,  87, (87, 63, 107),  8, 0),
            (top_m._v,      7, (7, 63, 10),    0, 97),
        ]
    else:  # 'up'
        parts = [
            (treads_m._v, None, (87, 63, 107),  0, 0),
            (top_m._v,    None, (7, 63, 10),   88, 97),
        ]

    results = []
    for voxel_dict, y_max, explicit_maxes, lx_off, z_off in parts:
        xyzi_bytes = bytearray()
        voxel_count = 0

        for (vx, vy, vz), c in voxel_dict.items():
            if ascend_dir == 'down':
                lx = y_max - vy
            else:
                lx = vy
            ly = vx
            lz = vz

            xyzi_bytes.extend((lx, ly, lz, c))
            voxel_count += 1

        if voxel_count > 0:
            results.append((_serialize_model(xyzi_bytes, voxel_count, explicit_maxes),
                            lx_off, z_off))

    return results


def build_staircase_balustrade_models(palette, seed_base, ascend_dir):
    """Build two balustrade models (one per side), rotated for placement.

    Balustrade model: x=0..4 (5px), y=0..95 (ascent), z=0..149 (height).
    After rotation (y->lx, x->ly): size (96, 5, 150).

    Returns list of (model_dict, lx_offset, ly_offset, z_offset) tuples.
    Two entries: left side and right side of the 64-wide staircase.
    """
    explicit_maxes = (95, 4, 149)

    # Left: inside_x=4 (x=4 faces the staircase at ly=16)
    # Right: inside_x=0 (x=0 faces the staircase at ly=79)
    sides = [
        (4, 11),   # (inside_x, ly_offset) â€” left balustrade
        (0, 80),   # right balustrade
    ]

    results = []
    for inside_x, ly_off in sides:
        rng_bal = random.Random(seed_base + 55003)
        bal_m = generate_staircase_balustrade(palette, None, rng_bal,
                                             inside_x=inside_x, save=False)

        xyzi_bytes = bytearray()
        voxel_count = 0

        for (vx, vy, vz), c in bal_m._v.items():
            if ascend_dir == 'down':
                lx = 95 - vy
            else:
                lx = vy
            ly = vx
            lz = vz

            xyzi_bytes.extend((lx, ly, lz, c))
            voxel_count += 1

        if voxel_count > 0:
            results.append((_serialize_model(xyzi_bytes, voxel_count, explicit_maxes),
                            0, ly_off, 0))

    return results


# ============================================================
# Bridge building
# ============================================================

# Bridge stringer z_center in zone coords (1 below staircase z_center(88)=108
# so balustrades sit at the right visual height relative to the deck).
_BRIDGE_ZC = 107          # zone z of stringer centerline
_BRIDGE_Z_OFF = 90        # balustrade z_off: model z=0 â†’ zone z=91 (crown top + 1)
_BRIDGE_DECK_Z_OFF = 106  # deck z_off: model z=0 â†’ zone z=107 (deck bottom)

# Stringer geometry in model z (relative to _BRIDGE_Z_OFF)
_STR_Z_CENTER = _BRIDGE_ZC - (_BRIDGE_Z_OFF + 1)  # 16
_STR_Z_TOP = _STR_Z_CENTER + 5                     # 21
_STR_Z_BOT = _STR_Z_CENTER - 4                     # 12
_STR_CAP_BOT = _STR_Z_TOP - 4                      # 17

# Baluster / rail in model z
_BAL_Z_BOT = _STR_Z_CENTER + 4       # 20
_BALUSTER_HEIGHT = 21
_RAIL_Z_BOT = _STR_Z_CENTER + 25     # 41
_RAIL_HEIGHT = 3

# Lamp post tile positions (tiles from staircase, 0-indexed)
_LAMP_TILES = [4, 8, 12]
_LAMP_POST_SIZE = 5

# Deck plank joints (darker than GRAIN_JOINT to contrast with GRAIN_DARK_WOOD surface)
_DECK_JOINT = [WOOD_DARKER, WOOD_DARKEST, WOOD_DARKER]


def _streak(rng, tones, length):
    """Generate a wood-grain color streak of given length."""
    pat, cur = [], rng.choice(tones)
    left = rng.randint(1, 12)
    for _ in range(length):
        if left <= 0:
            cur = rng.choice(tones)
            left = rng.randint(5, 12)
        pat.append(cur); left -= 1
    return pat


def _split_and_serialize(model, total_lx, ly_off, z_off, chunk_size=256):
    """Split a VoxelModel into <=256-wide chunks along lx and serialize.

    Returns list of (model_dict, lx_off, ly_off, z_off) tuples.
    """
    results = []
    for chunk_start in range(0, total_lx, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_lx)

        xyzi_bytes = bytearray()
        maxes = (0, 0, 0)
        count = 0

        for (x, y, z), c in model._v.items():
            if chunk_start <= x < chunk_end:
                lx = x - chunk_start
                xyzi_bytes.extend((lx, y, z, c))
                if lx > maxes[0]: maxes = (lx, maxes[1], maxes[2])
                if y > maxes[1]: maxes = (maxes[0], y, maxes[2])
                if z > maxes[2]: maxes = (maxes[0], maxes[1], z)
                count += 1

        if count > 0:
            result = _serialize_model(xyzi_bytes, count, maxes)
            results.append((result, chunk_start, ly_off, z_off))

    return results


def build_bridge_deck_models(rng, bridge_len):
    """Build bridge deck: 64 wide, 2 thick, with surface grain.

    Model coords: lx=0..bridge_len-1, ly=0..63, z=0..1.
    z=0 is bottom, z=1 is surface (grain).

    Returns list of (model_dict, lx_off, ly_off, z_off).
    ly_off=16 centers the 64-wide deck in the 96-wide span.
    z_off=94 places bottom at zone z=95, surface at z=96.
    """
    m = VoxelModel()

    # Bottom fill
    for lx in range(bridge_len):
        for ly in range(64):
            m.set(lx, ly, 0, WOOD_DARK)

    # Surface grain with plank joints every 8 voxels
    for lx in range(bridge_len):
        if lx % 8 == 0:
            for ly in range(64):
                m.set(lx, ly, 1, rng.choice(_DECK_JOINT))
        else:
            pat = _streak(rng, GRAIN_DARK_WOOD, 64)
            for li, ly in enumerate(range(64)):
                m.set(lx, ly, 1, pat[li])

    # Edge grain on front/back faces (lx=0 and lx=bridge_len-1)
    for lx_face in [0, bridge_len - 1]:
        pat = _streak(rng, GRAIN_DARK_WOOD, 64)
        for li, ly in enumerate(range(64)):
            m.set(lx_face, ly, 0, pat[li])

    return _split_and_serialize(m, bridge_len, 16, _BRIDGE_DECK_Z_OFF)


def build_bridge_balustrade_models(rng, bridge_len, stair_at_high_lx,
                                   support_positions=None):
    """Build bridge balustrade models for both sides.

    Each side: horizontal stringer + grooves + balusters + rail + lamp posts
    + support columns (if support_positions provided).
    stair_at_high_lx: True if staircase is at the high-lx end (green zone).
    support_positions: list of (tile_idx, col_offset, lx_within_tile).

    Returns list of per-side chunk lists.  Each inner list is
    [(model_dict, lx_off, ly_off, z_off), ...] for one balustrade side.
    """
    wood_tones = GRAIN_DARK_WOOD
    stringer_tones = GRAIN_DARK_WOOD
    num_tiles = bridge_len // 32

    # Compute lamp post lx positions (start of 5-voxel post)
    # Green zone (stair_at_high_lx) needs 13-tile to align first lamp 64 voxels
    # from staircase; yellow zone (not stair_at_high_lx) uses tile directly.
    lamp_lx_set = set()
    for tile in _LAMP_TILES:
        if stair_at_high_lx:
            lx_start = (13 - tile) * 32
        else:
            lx_start = tile * 32
        for dx in range(_LAMP_POST_SIZE):
            lamp_lx_set.add(lx_start + dx)

    # Compute lamp post start positions for building newel posts
    lamp_starts = []
    for tile in _LAMP_TILES:
        if stair_at_high_lx:
            lamp_starts.append((13 - tile) * 32)
        else:
            lamp_starts.append(tile * 32)

    # Pre-compute support lx positions per side (col_offset -> list of lx)
    side_supports = {0: [], 2: []}  # col_offset -> list of lx_center
    if support_positions:
        for tile_idx, col_offset, lx_within_tile in support_positions:
            if stair_at_high_lx:
                tile_lx_start = (num_tiles - 1 - tile_idx) * 32
            else:
                tile_lx_start = tile_idx * 32
            side_supports[col_offset].append(tile_lx_start + lx_within_tile)

    SUPPORT_H = _STR_Z_BOT  # supports fill model z 0 .. _STR_Z_BOT-1

    sides = [
        (4, 11, 0),   # (inside_ly, ly_off, col_offset) â€” left balustrade
        (0, 80, 2),   # right balustrade
    ]

    all_sides = []
    for inside_ly, ly_off, col_off in sides:
        m = VoxelModel()

        # --- Support columns (+ shaped, below stringer) ---
        for lx_c in side_supports.get(col_off, []):
            plus_xy = [
                (lx_c, 1),
                (lx_c - 1, 2), (lx_c, 2), (lx_c + 1, 2),
                (lx_c, 3),
            ]
            for bx, by in plus_xy:
                if 0 <= bx < bridge_len:
                    pat = _streak(rng, wood_tones, SUPPORT_H)
                    for zi in range(SUPPORT_H):
                        m.set(bx, by, zi, pat[zi])

        # --- Horizontal stringer ---
        for ly in range(5):
            # Cap (top 5 of band): z = _STR_CAP_BOT .. _STR_Z_TOP
            pat = _streak(rng, wood_tones, bridge_len)
            for z in range(_STR_CAP_BOT, _STR_Z_TOP + 1):
                for lx in range(bridge_len):
                    m.set(lx, ly, z, pat[lx])
                pat = _streak(rng, wood_tones, bridge_len)

            # Body (bottom of band): z = _STR_Z_BOT .. _STR_CAP_BOT-1
            for z in range(_STR_Z_BOT, _STR_CAP_BOT):
                pat = _streak(rng, stringer_tones, bridge_len)
                for lx in range(bridge_len):
                    m.set(lx, ly, z, pat[lx])

        # --- Grooves ---
        SIDE_OFFSETS = [+3, -2]
        for lx in range(bridge_len):
            for off in SIDE_OFFSETS:
                gz = _STR_Z_CENTER + off
                if _STR_Z_BOT <= gz <= _STR_Z_TOP:
                    m._v.pop((lx, 0, gz), None)
                    m._v.pop((lx, 4, gz), None)
            # Top groove
            groove_ly = inside_ly - 1 if inside_ly == 4 else inside_ly + 1
            m._v.pop((lx, groove_ly, _STR_Z_TOP), None)

        # --- Cross-beams below stringer ---
        # Identify first lamp post closest to staircase
        lamp_ranges = sorted(
            (ls, ls + _LAMP_POST_SIZE - 1)
            for ls in lamp_starts
            if 0 <= ls and ls + _LAMP_POST_SIZE - 1 < bridge_len
        )
        CROSSBEAM_H = 3
        # Skip the first cross-beam nearest the staircase
        stair_cb = max(range(0, bridge_len, 16)) if stair_at_high_lx else 0
        for cb_lx_c in range(0, bridge_len, 16):
            if cb_lx_c == stair_cb:
                continue
            for dlx in range(-1, 2):
                bx = cb_lx_c + dlx
                if 0 <= bx < bridge_len:
                    pat = _streak(rng, wood_tones, CROSSBEAM_H)
                    for dz in range(CROSSBEAM_H):
                        for ly in range(5):
                            m.set(bx, ly, _STR_Z_BOT - 1 - dz, pat[dz])

        # --- Paneled stringer body ---
        outer_ly = 0 if inside_ly == 4 else 4
        recess_ly = 1 if outer_ly == 0 else 3
        # Compute panel segments (gaps between lamp posts and bridge edges)
        panel_segs = []
        prev_end = -1
        for ls, le in lamp_ranges:
            if ls > prev_end + 1:
                panel_segs.append((prev_end + 1, ls - 1))
            prev_end = le
        if prev_end < bridge_len - 1:
            panel_segs.append((prev_end + 1, bridge_len - 1))
        # Carve recessed panels on outer face
        PANEL_FRAME_LX = 2
        PANEL_FRAME_Z = 1
        panel_z_lo = _STR_Z_BOT + PANEL_FRAME_Z
        panel_z_hi = _STR_CAP_BOT - 1 - PANEL_FRAME_Z
        for seg_start, seg_end in panel_segs:
            p_lx_lo = seg_start + PANEL_FRAME_LX
            p_lx_hi = seg_end - PANEL_FRAME_LX
            if p_lx_hi < p_lx_lo or panel_z_hi < panel_z_lo:
                continue
            panel_w = p_lx_hi - p_lx_lo + 1
            for z in range(panel_z_lo, panel_z_hi + 1):
                pat = _streak(rng, stringer_tones, panel_w)
                for i, lx in enumerate(range(p_lx_lo, p_lx_hi + 1)):
                    m._v.pop((lx, outer_ly, z), None)
                    m.set(lx, recess_ly, z, pat[i])

        # --- Balusters: + shaped 3x3, every 8 voxels ---
        for i in range(bridge_len // 8 + 1):
            lx_c = 1 + i * 8
            if lx_c >= bridge_len:
                break
            # Skip balusters that overlap with lamp posts
            if any(lx_c + dx in lamp_lx_set for dx in range(-1, 2)):
                continue
            plus_xy = [
                (lx_c, 1),
                (lx_c - 1, 2), (lx_c, 2), (lx_c + 1, 2),
                (lx_c, 3),
            ]
            for bx, by in plus_xy:
                if 0 <= bx < bridge_len:
                    pat = _streak(rng, wood_tones, _BALUSTER_HEIGHT)
                    for zi, z in enumerate(range(_BAL_Z_BOT, _BAL_Z_BOT + _BALUSTER_HEIGHT)):
                        m.set(bx, by, z, pat[zi])

        # --- Rail: 4â†’3â†’2 taper ---
        RAIL_LAYERS = [
            [0, 1, 2, 3],  # bottom: 4 wide
            [1, 2, 3],     # middle: 3 wide
            [1, 2],        # top: 2 wide
        ]
        for lx in range(bridge_len):
            pat = _streak(rng, GRAIN_DARK_WOOD, _RAIL_HEIGHT)
            for zi in range(_RAIL_HEIGHT):
                for ly in RAIL_LAYERS[zi]:
                    m.set(lx, ly, _RAIL_Z_BOT + zi, pat[zi])

        # --- Lamp posts (wood post + chamfered metal pole + lamp head) ---
        def _m():
            return 127 if rng.random() < 0.30 else METAL_DARK

        _POLE_H = 15
        # Shaft height: same as old design (z_cap=50 era)
        _old_cap = 50
        _z_base = _STR_Z_TOP + 1
        _plinth_h = 3
        _taper_h = 2
        _shaft_h = _old_cap - _z_base + 1 - _plinth_h - _taper_h - 6
        if _shaft_h < 4:
            _shaft_h = 4

        _band_positions = set()
        if _shaft_h > 8:
            _band_positions.add(0)
            _band_positions.add(_shaft_h - 1)
            _mid = _shaft_h // 2
            _band_positions.add(_mid)
            _band_positions.add(_mid - 1)

        for lx_start in lamp_starts:
            lx_end = lx_start + _LAMP_POST_SIZE - 1
            if lx_end >= bridge_len:
                continue

            for nlx in range(lx_start, lx_end + 1):
                clx = nlx - lx_start  # 0..4
                for nly in range(5):
                    is_3x3 = abs(clx - 2) <= 1 and abs(nly - 2) <= 1
                    is_corner = (clx in (0, 4)) and (nly in (0, 4))
                    is_edge = (clx in (0, 4)) or (nly in (0, 4))

                    z_cur = _z_base

                    # Plinth: 5x5 wood
                    for dz in range(_plinth_h):
                        m.set(nlx, nly, z_cur + dz, rng.choice(wood_tones))
                    z_cur += _plinth_h

                    # Taper layer 1: remove 4 corners
                    if _taper_h >= 1:
                        if (clx, nly) not in {(0,0),(0,4),(4,0),(4,4)}:
                            m.set(nlx, nly, z_cur, rng.choice(wood_tones))
                        z_cur += 1
                    # Taper layer 2: 3x3
                    if _taper_h >= 2:
                        if is_3x3:
                            m.set(nlx, nly, z_cur, rng.choice(wood_tones))
                        z_cur += 1

                    # Shaft: 3x3 with occasional 5x5 bands
                    pat = _streak(rng, wood_tones, _shaft_h)
                    for dz in range(_shaft_h):
                        if dz in _band_positions or is_3x3:
                            m.set(nlx, nly, z_cur + dz, pat[dz])
                    z_cur += _shaft_h

                    # Metal pole: 2x2
                    if clx in (1, 2) and nly in (1, 2):
                        for dz in range(_POLE_H):
                            m.set(nlx, nly, z_cur + dz, _m())
                    z_cur += _POLE_H

                    # Lantern base plate: 5x5 metal
                    m.set(nlx, nly, z_cur, _m())
                    z_cur += 1

                    # Housing: 3 layers, metal corners + emissive edges
                    for hz in range(3):
                        if is_corner:
                            m.set(nlx, nly, z_cur + hz, _m())
                        elif is_edge:
                            m.set(nlx, nly, z_cur + hz, LAMP_WARM)
                    z_cur += 3

                    # Top plate: 5x5 metal
                    m.set(nlx, nly, z_cur, _m())
                    z_cur += 1

                    # Taper: 3x3
                    if is_3x3:
                        m.set(nlx, nly, z_cur, _m())
                    z_cur += 1

                    # Taper: 1x1 cap
                    if clx == 2 and nly == 2:
                        m.set(nlx, nly, z_cur, _m())

        chunks = _split_and_serialize(m, bridge_len, ly_off, _BRIDGE_Z_OFF)
        all_sides.append(chunks)

    return all_sides



def build_floor_model(mr, mc, mr_end, mc_end, palette, seed_base, row_offset, col_offset):
    """Build a floor MV model filling every cell in (mr,mc) to (mr_end,mc_end).

    Uses expanded-grid coordinates. Seeds use zone-relative coords
    (subtracting row_offset/col_offset).
    """
    xyzi_bytes = bytearray()
    maxes = (0, 0, 0)
    voxel_count = 0

    for row in range(mr, mr_end + 1):
        for col in range(mc, mc_end + 1):
            lx_base = (mr_end - row) * 32
            ly_base = (mc_end - col) * 32

            # Zone-relative coords for deterministic seeding
            zr = row - row_offset
            zc = col - col_offset
            rng_a = random.Random(seed_base + zr * 1009 + zc * 8191 + 1)
            rng_b = random.Random(seed_base + zr * 1009 + zc * 8191 + 2)
            variant_a = (zr * 64 + zc) % 10
            variant_b = (zr * 64 + zc + 5) % 10

            tile_a = generate_tile(palette, None, variant_a, rng_a, save=False)
            tile_b = generate_tile(palette, None, variant_b, rng_b, save=False)

            if (row + col) % 2 == 0:
                # Seam parallel to x: tiles stacked in y
                cnt, maxes = _append_voxels(xyzi_bytes, tile_a._v, lx_base, ly_base, maxes)
                voxel_count += cnt
                cnt, maxes = _append_voxels(xyzi_bytes, tile_b._v, lx_base, ly_base + 16, maxes)
                voxel_count += cnt
            else:
                # Seam parallel to y: swap x,y to rotate 32x16 -> 16x32
                for (vx, vy, vz), c in tile_a._v.items():
                    lx, ly = lx_base + vy, ly_base + vx
                    xyzi_bytes.extend((lx, ly, vz, c))
                    if lx > maxes[0]: maxes = (lx, maxes[1], maxes[2])
                    if ly > maxes[1]: maxes = (maxes[0], ly, maxes[2])
                    if vz > maxes[2]: maxes = (maxes[0], maxes[1], vz)
                    voxel_count += 1
                for (vx, vy, vz), c in tile_b._v.items():
                    lx, ly = lx_base + 16 + vy, ly_base + vx
                    xyzi_bytes.extend((lx, ly, vz, c))
                    if lx > maxes[0]: maxes = (lx, maxes[1], maxes[2])
                    if ly > maxes[1]: maxes = (maxes[0], ly, maxes[2])
                    if vz > maxes[2]: maxes = (maxes[0], maxes[1], vz)
                    voxel_count += 1

            del tile_a, tile_b

    if voxel_count == 0:
        return None
    return _serialize_model(xyzi_bytes, voxel_count, maxes)


def _serialize_model(xyzi_bytes, voxel_count, maxes):
    """Serialize model to SIZE+XYZI chunk bytes."""
    max_lx, max_ly, max_z = maxes
    sx, sy, sz = max_lx + 1, max_ly + 1, max_z + 1
    size_content = struct.pack("<III", sx, sy, sz)
    xyzi_content = struct.pack("<I", voxel_count) + bytes(xyzi_bytes)
    model_data = write_chunk(b"SIZE", size_content) + write_chunk(b"XYZI", xyzi_content)
    return {
        'model_data': model_data,
        'size': (sx, sy, sz),
        'num_voxels': voxel_count,
    }


# ============================================================
# World coordinate helpers
# ============================================================

def tile_world_pos(row, col, total_rows, total_cols):
    """World position of tile (row, col)'s (0,0,0) corner."""
    return (total_rows - 1 - row) * 32, (total_cols - 1 - col) * 32


def model_world_origin(mr_end, mc_end, total_rows, total_cols):
    """World position of the (0,0,0) corner of a model at tile (mr_end, mc_end)."""
    return tile_world_pos(mr_end, mc_end, total_rows, total_cols)


def model_translation(world_x, world_y, size_x, size_y, size_z, shift_x, shift_y):
    """Compute nTRN _t translation for a model."""
    centered_x = world_x - shift_x
    centered_y = world_y - shift_y
    translate_x = centered_x + size_x // 2
    translate_y = centered_y + size_y // 2
    translate_z = size_z // 2
    return (translate_x, translate_y, translate_z)


def compute_parent_translation(children):
    """Compute parent nTRN translation for a grouped structure.

    children: list of ((sx, sy, sz), (tx, ty, tz))
    Returns (parent_tx, parent_ty, parent_tz).
    """
    min_x = min(tx - sx // 2 for (sx, _, _), (tx, _, _) in children)
    max_x = max(tx + sx - sx // 2 for (sx, _, _), (tx, _, _) in children)
    min_y = min(ty - sy // 2 for (_, sy, _), (_, ty, _) in children)
    max_y = max(ty + sy - sy // 2 for (_, sy, _), (_, ty, _) in children)
    min_z = min(tz - sz // 2 for (_, _, sz), (_, _, tz) in children)
    max_z = max(tz + sz - sz // 2 for (_, _, sz), (_, _, tz) in children)

    return (
        min_x + (max_x - min_x) // 2,
        min_y + (max_y - min_y) // 2,
        min_z + (max_z - min_z) // 2,
    )


# ============================================================
# .vox writer with nested scene graph
# ============================================================

def write_structured_vox(filepath, all_model_data, structures, total_x, total_y, palette):
    """Write multi-model .vox with nested scene graph.

    all_model_data: concatenated SIZE+XYZI bytes for all models
    structures: list of structure dicts, each with:
        'models': list of (model_index, (tx, ty, tz), (sx, sy, sz))
    If a structure has 1 model: flat nTRN -> nSHP
    If multiple models: nTRN -> nGRP -> [nTRN -> nSHP, ...]
    """
    # --- Build scene graph ---
    next_id = [2]  # start after root nTRN(0) and scene nGRP(1)

    def alloc_id():
        nid = next_id[0]
        next_id[0] += 1
        return nid

    scene_children_ids = []  # children of scene nGRP(1)
    scene_chunks = b""

    for structure in structures:
        models = structure['models']

        if len(models) == 1:
            # Flat: nTRN -> nSHP (direct child of scene group)
            model_idx, t, s = models[0]
            trn_id = alloc_id()
            shp_id = alloc_id()
            scene_children_ids.append(trn_id)

            trn = struct.pack("<I", trn_id)
            trn += _write_dict({'_name': structure['name']} if 'name' in structure else {})
            trn += struct.pack("<I", shp_id)
            trn += struct.pack("<i", -1)
            trn += struct.pack("<i", -1)
            trn += struct.pack("<I", 1)
            trn += _write_dict({"_t": f"{t[0]} {t[1]} {t[2]}"})
            scene_chunks += write_chunk(b"nTRN", trn)

            shp = struct.pack("<I", shp_id)
            shp += _write_dict({})
            shp += struct.pack("<I", 1)
            shp += struct.pack("<I", model_idx)
            shp += _write_dict({})
            scene_chunks += write_chunk(b"nSHP", shp)

        else:
            # Nested: nTRN -> nGRP -> [nTRN -> nSHP, ...]
            parent_trn_id = alloc_id()
            grp_id = alloc_id()
            scene_children_ids.append(parent_trn_id)

            # Compute parent translation
            children_for_parent = [(s, t) for _, t, s in models]
            parent_t = compute_parent_translation(children_for_parent)

            # Parent nTRN
            trn = struct.pack("<I", parent_trn_id)
            trn += _write_dict({'_name': structure['name']} if 'name' in structure else {})
            trn += struct.pack("<I", grp_id)
            trn += struct.pack("<i", -1)
            trn += struct.pack("<i", -1)
            trn += struct.pack("<I", 1)
            trn += _write_dict({"_t": f"{parent_t[0]} {parent_t[1]} {parent_t[2]}"})
            scene_chunks += write_chunk(b"nTRN", trn)

            # nGRP
            child_trn_ids = []
            for _ in models:
                child_trn_ids.append(alloc_id())
                alloc_id()  # reserve shp_id

            grp = struct.pack("<I", grp_id)
            grp += _write_dict({})
            grp += struct.pack("<I", len(models))
            for cid in child_trn_ids:
                grp += struct.pack("<I", cid)
            scene_chunks += write_chunk(b"nGRP", grp)

            # Child nTRN -> nSHP pairs (translations relative to parent)
            for i, (model_idx, t, s) in enumerate(models):
                trn_id = child_trn_ids[i]
                shp_id = trn_id + 1

                rel_t = (t[0] - parent_t[0], t[1] - parent_t[1], t[2] - parent_t[2])
                trn = struct.pack("<I", trn_id)
                trn += _write_dict({})
                trn += struct.pack("<I", shp_id)
                trn += struct.pack("<i", -1)
                trn += struct.pack("<i", -1)
                trn += struct.pack("<I", 1)
                trn += _write_dict({"_t": f"{rel_t[0]} {rel_t[1]} {rel_t[2]}"})
                scene_chunks += write_chunk(b"nTRN", trn)

                shp = struct.pack("<I", shp_id)
                shp += _write_dict({})
                shp += struct.pack("<I", 1)
                shp += struct.pack("<I", model_idx)
                shp += _write_dict({})
                scene_chunks += write_chunk(b"nSHP", shp)

    # Root nTRN(0) -> nGRP(1)
    trn_root = struct.pack("<I", 0)
    trn_root += _write_dict({"_name": "root"})
    trn_root += struct.pack("<I", 1)
    trn_root += struct.pack("<i", -1)
    trn_root += struct.pack("<i", -1)
    trn_root += struct.pack("<I", 1)
    trn_root += _write_dict({})
    root_chunk = write_chunk(b"nTRN", trn_root)

    grp1 = struct.pack("<I", 1)
    grp1 += _write_dict({})
    grp1 += struct.pack("<I", len(scene_children_ids))
    for cid in scene_children_ids:
        grp1 += struct.pack("<I", cid)
    grp1_chunk = write_chunk(b"nGRP", grp1)

    scene_graph = root_chunk + grp1_chunk + scene_chunks

    # RGBA palette
    rgba_content = b""
    for i in range(1, 256):
        r, g, b, a = palette[i] if i < len(palette) else (0, 0, 0, 255)
        rgba_content += struct.pack("<BBBB", r, g, b, a)
    rgba_content += struct.pack("<BBBB", 0, 0, 0, 0)
    rgba_chunk = write_chunk(b"RGBA", rgba_content)

    # MATL chunks — one per palette ID (1-256), matching MagicaVoxel convention
    _MATL_DIFFUSE_DEFAULT = {"_rough": "0.1", "_ior": "0.3", "_ri": "1.3", "_d": "0.05"}
    special_materials = {
        117: {"_type": "_emit", "_emit": "0.8", "_flux": "3"},
        METAL_LIGHT: {"_type": "_metal", "_metal": "0.8", "_rough": "0.3"},
    }
    matl_chunks = b""
    for mat_id in range(1, 257):
        props = special_materials.get(mat_id, _MATL_DIFFUSE_DEFAULT)
        matl_content = struct.pack("<I", mat_id) + _write_dict(props)
        matl_chunks += write_chunk(b"MATL", matl_content)

    # Assemble
    children = all_model_data + scene_graph + rgba_chunk + matl_chunks
    main_chunk = write_chunk(b"MAIN", b"", children)
    header = b"VOX " + struct.pack("<I", 200)

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(header + main_chunk)


# ============================================================
# Zone generation
# ============================================================

PLANTER_SHELF_TYPES = {'1conn', '3conn'}  # ends, t-junctions

FLOOR_BORDER = 3  # floor extends 3 tiles beyond shelves on outer edges

# Per-zone border: only outer edges get the 3-tile floor extension.
# In image space: pink=top-left, green=top-right, blue=bottom-left, yellow=bottom-right.
# "top"=min-row side, "bottom"=max-row side, "left"=min-col side, "right"=max-col side.
ZONE_BORDERS = {
    'pink':   {'top': FLOOR_BORDER, 'bottom': 0, 'left': FLOOR_BORDER, 'right': 0},
    'green':  {'top': FLOOR_BORDER, 'bottom': 0, 'left': 0, 'right': FLOOR_BORDER},
    'blue':   {'top': 0, 'bottom': FLOOR_BORDER, 'left': FLOOR_BORDER, 'right': 0},
    'yellow': {'top': 0, 'bottom': FLOOR_BORDER, 'left': 0, 'right': FLOOR_BORDER},
}


def generate_zone(zone_name, zone_info, shelf_map, palette, output_dir,
                   stair_tiles=None):
    """Full pipeline: decompose -> build models -> write .vox."""
    tiles = zone_info['tiles']
    num_rows = zone_info['num_rows']
    num_cols = zone_info['num_cols']

    # Per-side border widths (outer edges only)
    borders = ZONE_BORDERS.get(zone_name, {'top': 0, 'bottom': 0, 'left': 0, 'right': 0})
    b_top = borders['top']
    b_bot = borders['bottom']
    b_left = borders['left']
    b_right = borders['right']

    # Expanded grid dimensions
    exp_rows = num_rows + b_top + b_bot
    exp_cols = num_cols + b_left + b_right
    total_x = exp_rows * 32
    total_y = exp_cols * 32
    shift_x = total_x // 2
    shift_y = total_y // 2
    seed_base = hash(f"{zone_info['min_row']}_{zone_info['min_col']}") & 0xFFFFFFFF

    print(f"    borders: top={b_top} bot={b_bot} left={b_left} right={b_right} "
          f"-> expanded {exp_rows}x{exp_cols}", flush=True)

    # --- Early bridge detection: compute bridge_tiles for planter suppression ---
    bridge_tiles = set()  # zone-local (row, col) of shelves under the bridge
    bridge_info = None     # filled if this zone has a bridge

    if stair_tiles:
        zone_min_row = zone_info['min_row']
        zone_min_col = zone_info['min_col']
        zone_max_row = zone_min_row + num_rows - 1
        zone_max_col = zone_min_col + num_cols - 1

        _nearby_stairs = {
            (r, c) for r, c in stair_tiles
            if zone_min_row - 1 <= r <= zone_max_row + 1
            and zone_min_col - 1 <= c <= zone_max_col + 1
        }
        if _nearby_stairs:
            _stair_min_r = min(r for r, c in _nearby_stairs)
            _stair_min_c = min(c for r, c in _nearby_stairs)
            _local_r = _stair_min_r - zone_min_row
            _local_c = _stair_min_c - zone_min_col

            _ascend_dir = 'down' if b_bot == 0 else 'up'
            _stair_mr_end = _local_r + 2 + b_top
            _stair_mr = _stair_mr_end - 2

            if _ascend_dir == 'down':
                _bridge_mr = _stair_mr_end + 1
                _bridge_mr_end = exp_rows - 1
                _stair_at_high_lx = True
            else:
                _bridge_mr = 0
                _bridge_mr_end = _stair_mr - 1
                _stair_at_high_lx = False

            _bridge_num_tiles = _bridge_mr_end - _bridge_mr + 1
            if _bridge_num_tiles > 0:
                _stair_cols = range(_local_c, _local_c + 3)

                # Identify shelf tiles under the bridge path. For each shelf
                # under a balustrade, check row-direction neighbors to find
                # which lx-edge faces have crowns. Supports sit on crowns only.
                # col_offset: 0 = left balustrade, 2 = right balustrade.
                # lx_within_tile: 3 = low-lx crown, 28 = high-lx crown.
                _support_positions = []  # (tile_idx, col_offset, lx_within_tile)
                for _exp_row in range(_bridge_mr, _bridge_mr_end + 1):
                    _zone_row = _exp_row - b_top
                    if _ascend_dir == 'down':
                        _tile_from_stair = _exp_row - _bridge_mr
                    else:
                        _tile_from_stair = _bridge_mr_end - _exp_row
                    for _c in _stair_cols:
                        if tiles.get((_zone_row, _c)) in SHELF_LIKE_TYPES:
                            bridge_tiles.add((_zone_row, _c))
                            _col_offset = _local_c + 2 - _c
                            if _col_offset not in (0, 2):
                                continue  # middle column, no balustrade
                            # Crown on low-lx face if no shelf neighbor at row+1
                            _has_lo = tiles.get((_zone_row + 1, _c)) not in SHELF_LIKE_TYPES
                            # Crown on high-lx face if no shelf neighbor at row-1
                            _has_hi = tiles.get((_zone_row - 1, _c)) not in SHELF_LIKE_TYPES
                            if _has_lo:
                                _support_positions.append(
                                    (_tile_from_stair, _col_offset, 2))
                            if _has_hi:
                                _support_positions.append(
                                    (_tile_from_stair, _col_offset, 27))

                bridge_info = {
                    'bridge_mr': _bridge_mr,
                    'bridge_mr_end': _bridge_mr_end,
                    'num_tiles': _bridge_num_tiles,
                    'stair_at_high_lx': _stair_at_high_lx,
                    'stair_mc_end': _local_c + 2 + b_left,
                    'support_positions': _support_positions,
                }

                if bridge_tiles:
                    print(f"    Bridge path: {_bridge_num_tiles} tiles, "
                          f"{len(bridge_tiles)} shelf tiles under bridge", flush=True)

    all_model_data = b""
    model_count = 0
    total_voxels = 0
    structures = []

    # --- Shelves: decompose into rectangles, split into structures ---
    # Exclude 1conn_2height tiles from rectangle grouping â€” they become
    # standalone structures so their bounding boxes don't intersect the sign.
    entrance_2h_positions = {pos for pos, (st, _) in shelf_map.items()
                             if st == '1conn_2height'}
    shelf_positions = {pos for pos, tt in tiles.items()
                       if tt in SHELF_LIKE_TYPES} - entrance_2h_positions

    # Outer ring: shelves on scene-boundary edges only (not inner zone edges)
    shelf_rows = {r for r, c in shelf_positions}
    shelf_cols = {c for r, c in shelf_positions}
    min_r, max_r = min(shelf_rows), max(shelf_rows)
    min_c, max_c = min(shelf_cols), max(shelf_cols)
    outer_ring = frozenset(
        (r, c) for r, c in shelf_positions
        if (r == min_r and b_top > 0)
        or (r == max_r and b_bot > 0)
        or (c == min_c and b_left > 0)
        or (c == max_c and b_right > 0)
    )

    # Detect 3x1 nooks for rectangular planters
    nooks = detect_nooks(tiles)

    # Decompose bridge and non-bridge shelves separately so their bounding
    # boxes never overlap (bridge structures sit above bridge-path shelves).
    shelf_under_bridge = shelf_positions & bridge_tiles
    shelf_outside_bridge = shelf_positions - bridge_tiles
    shelf_rects = (decompose_into_rectangles(shelf_outside_bridge)
                   + decompose_into_rectangles(shelf_under_bridge))
    print(f"    {len(shelf_rects)} shelf rectangles", flush=True)

    shelf_struct_count = 0
    shelf_model_count = 0
    for rect in shelf_rects:
        r1, c1, r2, c2 = rect
        rect_structures = split_into_structures(r1, c1, r2, c2)

        for mv_regions in rect_structures:
            struct_models = []

            for mr, mc, mr_end, mc_end in mv_regions:
                result = build_shelf_model(mr, mc, mr_end, mc_end,
                                           shelf_map, palette, seed_base,
                                           outer_ring, bridge_tiles)
                if result is None:
                    continue

                model_idx = model_count
                all_model_data += result['model_data']
                model_count += 1
                shelf_model_count += 1
                total_voxels += result['num_voxels']

                sx, sy, sz = result['size']
                # Shelf zone-local -> expanded-local: add top/left border
                e_mr_end = mr_end + b_top
                e_mc_end = mc_end + b_left
                wx, wy = model_world_origin(e_mr_end, e_mc_end, exp_rows, exp_cols)
                t = model_translation(wx, wy, sx, sy, sz, shift_x, shift_y)
                t = (t[0], t[1], t[2] + 1)  # shelves sit 1 voxel above tile
                struct_models.append((model_idx, t, (sx, sy, sz)))

            if struct_models:
                structures.append({'models': struct_models})
                shelf_struct_count += 1

    # Place 1conn_2height shelves as standalone structures (separate bounding boxes)
    entrance_2h_struct = {}  # (r, c) -> (struct_idx, wx, wy)
    for pos in sorted(entrance_2h_positions):
        r, c = pos
        result = build_shelf_model(r, c, r, c, shelf_map, palette, seed_base,
                                   outer_ring, bridge_tiles)
        if result is None:
            continue
        model_idx = model_count
        all_model_data += result['model_data']
        model_count += 1
        shelf_model_count += 1
        total_voxels += result['num_voxels']

        sx, sy, sz = result['size']
        e_mr_end = r + b_top
        e_mc_end = c + b_left
        wx, wy = model_world_origin(e_mr_end, e_mc_end, exp_rows, exp_cols)
        t = model_translation(wx, wy, sx, sy, sz, shift_x, shift_y)
        t = (t[0], t[1], t[2] + 1)  # shelves sit 1 voxel above tile
        structures.append({'models': [(model_idx, t, (sx, sy, sz))]})
        entrance_2h_struct[(r, c)] = (len(structures) - 1, wx, wy)
        shelf_struct_count += 1

    print(f"    {shelf_struct_count} shelf structures, {shelf_model_count} shelf models", flush=True)

    # --- Helper: split a square planter for entrance shelves ---
    def _split_planter_for_entrance(shelf_rc, planter_rng):
        """Generate a planter, split at z=2.

        Appends bottom layers (z=0,1) to the shelf structure.
        Returns (upper_model_idx, upper_t, upper_size) for the plaque
        structure, or None if shelf not found.
        """
        nonlocal all_model_data, model_count, total_voxels

        if shelf_rc not in entrance_2h_struct:
            return None
        struct_idx, wx, wy = entrance_2h_struct[shelf_rc]

        planter_m = generate_square_planter(palette, None, planter_rng, save=False)

        # Split at z=4: bottom (z=0..3) and upper (z>=4)
        bottom_bytes = bytearray()
        bottom_count = 0
        upper_bytes = bytearray()
        upper_count = 0
        upper_max_z = 0

        for (vx, vy, vz), vc in planter_m._v.items():
            if vz < 4:
                bottom_bytes.extend((vx, vy, vz, vc))
                bottom_count += 1
            else:
                nz = vz - 4
                upper_bytes.extend((vx, vy, nz, vc))
                upper_count += 1
                if nz > upper_max_z:
                    upper_max_z = nz

        # Bottom model: 32x32x4, append to shelf structure
        if bottom_count > 0:
            bottom_result = _serialize_model(bottom_bytes, bottom_count, (31, 31, 3))
            bm_idx = model_count
            all_model_data += bottom_result['model_data']
            model_count += 1
            total_voxels += bottom_result['num_voxels']
            bsx, bsy, bsz = bottom_result['size']
            bt = model_translation(wx, wy, bsx, bsy, bsz, shift_x, shift_y)
            bt = (bt[0], bt[1], bt[2] + SHELF_STRUCT_TOP_2H + 1)
            structures[struct_idx]['models'].append((bm_idx, bt, (bsx, bsy, bsz)))

        # Upper model: 32x32xH, return for plaque structure
        if upper_count > 0:
            upper_result = _serialize_model(upper_bytes, upper_count, (31, 31, upper_max_z))
            um_idx = model_count
            all_model_data += upper_result['model_data']
            model_count += 1
            total_voxels += upper_result['num_voxels']
            usx, usy, usz = upper_result['size']
            ut = model_translation(wx, wy, usx, usy, usz, shift_x, shift_y)
            ut = (ut[0], ut[1], ut[2] + SHELF_STRUCT_TOP_2H + 5)
            return (um_idx, ut, (usx, usy, usz))

        return None

    # --- Entrance plaque: detect 1conn_2height pairs across a path ---
    entrance_2h_tiles = [(r, c) for (r, c), (st, _) in shelf_map.items()
                         if st == '1conn_2height']
    plaque_placed = False
    for r1, c1 in entrance_2h_tiles:
        if plaque_placed:
            break
        for r2, c2 in entrance_2h_tiles:
            if (r1, c1) >= (r2, c2):
                continue
            # Same row, separated by floor tiles (path between them)
            if r1 == r2:
                lo_c, hi_c = min(c1, c2), max(c1, c2)
                gap = hi_c - lo_c - 1
                if gap < 1 or gap > 5:
                    continue
                all_floor = all(tiles.get((r1, c)) == 'floor'
                                for c in range(lo_c + 1, hi_c))
                if not all_floor:
                    continue
                # Found entrance pair along a row (cols differ)
                # Path runs along y (col axis) â€” rotate plaque so 160 spans y
                plaque_rng = random.Random(seed_base + r1 * 7717 + lo_c * 3331)
                plaque_m, plaque_z_base = generate_entrance_plaque(palette, None, plaque_rng, save=False)

                e_mr = r1 + b_top
                e_mc_end = hi_c + b_left
                plaque_wx, plaque_wy = model_world_origin(e_mr, e_mc_end, exp_rows, exp_cols)
                psx, psy, psz = plaque_m.get_size()

                # Rotate 90 CCW so 160-wide dimension goes along y, text faces entrance
                rotated = {}
                for (vx, vy, vz), vc in plaque_m._v.items():
                    rotated[(vy, psx - 1 - vx, vz)] = vc
                r_sx = psy
                r_sy = psx
                r_sz = psz

                xyzi_bytes = bytearray()
                for (vx, vy, vz), vc in rotated.items():
                    xyzi_bytes.extend((vx, vy, vz, vc))
                p_maxes = (r_sx - 1, r_sy - 1, r_sz - 1)
                plaque_result = _serialize_model(xyzi_bytes, len(rotated), p_maxes)

                plaque_model_idx = model_count
                all_model_data += plaque_result['model_data']
                model_count += 1
                total_voxels += plaque_result['num_voxels']

                t = model_translation(plaque_wx, plaque_wy, r_sx, r_sy, r_sz, shift_x, shift_y)
                t = (t[0], t[1], t[2] + plaque_z_base)
                plaque_models = [(plaque_model_idx, t, (r_sx, r_sy, r_sz))]

                # Add planters on entrance shelves
                for shelf_c in (lo_c, hi_c):
                    p_rng = random.Random(seed_base + r1 * 9137 + shelf_c * 4391)
                    upper = _split_planter_for_entrance((r1, shelf_c), p_rng)
                    if upper:
                        plaque_models.append(upper)

                structures.append({'models': plaque_models})
                plaque_placed = True
                print(f"    Entrance plaque placed at row={r1}, cols={lo_c}..{hi_c}", flush=True)
                break

            # Same column, separated by floor tiles
            if c1 == c2:
                lo_r, hi_r = min(r1, r2), max(r1, r2)
                gap = hi_r - lo_r - 1
                if gap < 1 or gap > 5:
                    continue
                all_floor = all(tiles.get((r, c1)) == 'floor'
                                for r in range(lo_r + 1, hi_r))
                if not all_floor:
                    continue
                # Found entrance pair along a column (rows differ)
                # Path runs along x (row axis) â€” plaque 160-wide is already along x
                plaque_rng = random.Random(seed_base + lo_r * 7717 + c1 * 3331)
                plaque_m, plaque_z_base = generate_entrance_plaque(palette, None, plaque_rng, save=False)

                e_mr_end = hi_r + b_top
                e_mc = c1 + b_left
                plaque_wx, plaque_wy = model_world_origin(e_mr_end, e_mc, exp_rows, exp_cols)
                psx, psy, psz = plaque_m.get_size()

                xyzi_bytes = bytearray()
                for (vx, vy, vz), vc in plaque_m._v.items():
                    xyzi_bytes.extend((vx, vy, vz, vc))
                p_maxes = (psx - 1, psy - 1, psz - 1)
                plaque_result = _serialize_model(xyzi_bytes, len(plaque_m._v), p_maxes)

                plaque_model_idx = model_count
                all_model_data += plaque_result['model_data']
                model_count += 1
                total_voxels += plaque_result['num_voxels']

                t = model_translation(plaque_wx, plaque_wy, psx, psy, psz, shift_x, shift_y)
                t = (t[0], t[1], t[2] + plaque_z_base)
                plaque_models = [(plaque_model_idx, t, (psx, psy, psz))]

                # Add planters on entrance shelves
                for shelf_r in (lo_r, hi_r):
                    p_rng = random.Random(seed_base + shelf_r * 9137 + c1 * 4391)
                    upper = _split_planter_for_entrance((shelf_r, c1), p_rng)
                    if upper:
                        plaque_models.append(upper)

                structures.append({'models': plaque_models})
                plaque_placed = True
                print(f"    Entrance plaque placed at col={c1}, rows={lo_r}..{hi_r}", flush=True)
                break

    # --- Nooks: standalone rectangular planter per nook ---
    nook_model_count = 0
    for nook in nooks:
        result = build_planter_model(nook, palette, seed_base)
        if result is None:
            continue

        model_idx = model_count
        all_model_data += result['model_data']
        model_count += 1
        nook_model_count += 1
        total_voxels += result['num_voxels']

        sx, sy, sz = result['size']
        # Origin tile = (max floor row, max floor col)
        mr_end = max(r for r, c in nook['floor'])
        mc_end = max(c for r, c in nook['floor'])
        e_mr_end = mr_end + b_top
        e_mc_end = mc_end + b_left
        wx, wy = model_world_origin(e_mr_end, e_mc_end, exp_rows, exp_cols)
        t = model_translation(wx, wy, sx, sy, sz, shift_x, shift_y)
        t = (t[0], t[1], t[2] + 1)  # sit on floor (above z=0 floor tile)
        structures.append({'models': [(model_idx, t, (sx, sy, sz))]})

    print(f"    {len(nooks)} nooks, {nook_model_count} nook models", flush=True)

    # --- Floor: fill entire expanded grid as 512x512x1 structures ---
    floor_structures = split_into_structures(0, 0, exp_rows - 1, exp_cols - 1)

    floor_struct_count = 0
    floor_model_start = model_count
    for mv_regions in floor_structures:
        struct_models = []

        for mr, mc, mr_end, mc_end in mv_regions:
            result = build_floor_model(mr, mc, mr_end, mc_end,
                                       palette, seed_base, b_top, b_left)
            if result is None:
                continue

            model_idx = model_count
            all_model_data += result['model_data']
            model_count += 1
            total_voxels += result['num_voxels']

            sx, sy, sz = result['size']
            wx, wy = model_world_origin(mr_end, mc_end, exp_rows, exp_cols)
            t = model_translation(wx, wy, sx, sy, sz, shift_x, shift_y)
            struct_models.append((model_idx, t, (sx, sy, sz)))

        if struct_models:
            structures.append({'models': struct_models})
            floor_struct_count += 1

    print(f"    {floor_struct_count} floor structures, "
          f"{model_count - floor_model_start} floor models", flush=True)

    # --- Staircases: detect stair tiles adjacent to this zone ---
    if stair_tiles:
        # Find stair tiles within or adjacent to this zone's global row/col range
        zone_min_row = zone_info['min_row']
        zone_min_col = zone_info['min_col']
        zone_max_row = zone_min_row + num_rows - 1
        zone_max_col = zone_min_col + num_cols - 1

        # Stair tiles that fall within 1 tile of zone bounds (they're right at zone edge)
        nearby_stairs = {
            (r, c) for r, c in stair_tiles
            if zone_min_row - 1 <= r <= zone_max_row + 1
            and zone_min_col - 1 <= c <= zone_max_col + 1
        }

        if nearby_stairs:
            # Find the 3x3 block origin
            stair_min_r = min(r for r, c in nearby_stairs)
            stair_min_c = min(c for r, c in nearby_stairs)

            # Zone-local coords of the stair block
            local_r = stair_min_r - zone_min_row
            local_c = stair_min_c - zone_min_col

            # Determine ascent direction based on zone position
            # Green (b_bot==0): ascends toward bottom (toward yellow) -> 'down' (-lx)
            # Yellow (b_top==0): ascends toward top (toward green) -> 'up' (+lx)
            if b_bot == 0:
                ascend_dir = 'down'
            else:
                ascend_dir = 'up'

            stair_results = build_staircase_models(palette, seed_base, ascend_dir)
            # Origin tile: bottom-right of 3x3 block in expanded coords
            stair_mr_end = local_r + 2 + b_top
            stair_mc_end = local_c + 2 + b_left
            base_wx, base_wy = model_world_origin(stair_mr_end, stair_mc_end,
                                                    exp_rows, exp_cols)

            stair_voxels = 0
            prism_name = ('staircase_plusZPrism' if ascend_dir == 'down'
                          else 'staircase_minusZPrism')
            for i, (result, lx_offset, z_offset) in enumerate(stair_results):
                model_idx = model_count
                all_model_data += result['model_data']
                model_count += 1
                total_voxels += result['num_voxels']
                stair_voxels += result['num_voxels']

                sx, sy, sz = result['size']
                wx = base_wx + lx_offset
                wy = base_wy + 16  # center 64-wide staircase in 96-voxel span
                t = model_translation(wx, wy, sx, sy, sz, shift_x, shift_y)
                t = (t[0], t[1], t[2] + z_offset + 1)
                s = {'models': [(model_idx, t, (sx, sy, sz))]}
                if i == 0:
                    s['name'] = prism_name
                structures.append(s)

            print(f"    Staircase placed (ascend={ascend_dir}, "
                  f"local=({local_r},{local_c}), {stair_voxels:,} voxels, "
                  f"{len(stair_results)} models)", flush=True)

            # Balustrades: two identical panels, one on each side
            bal_results = build_staircase_balustrade_models(
                palette, seed_base, ascend_dir)
            bal_voxels = 0
            for result, lx_off, ly_off, z_off in bal_results:
                model_idx = model_count
                all_model_data += result['model_data']
                model_count += 1
                total_voxels += result['num_voxels']
                bal_voxels += result['num_voxels']

                sx, sy, sz = result['size']
                wx = base_wx + lx_off
                wy = base_wy + ly_off
                t = model_translation(wx, wy, sx, sy, sz, shift_x, shift_y)
                t = (t[0], t[1], t[2] + z_off + 1)
                structures.append({'models': [(model_idx, t, (sx, sy, sz))]})

            print(f"    Balustrades placed ({bal_voxels:,} voxels, "
                  f"{len(bal_results)} models)", flush=True)

    # --- Bridge: horizontal walkway from staircase top to zone edge ---
    if bridge_info is not None:
        bi = bridge_info
        bridge_len = bi['num_tiles'] * 32
        bridge_rng = random.Random(seed_base + 66001)

        # Bridge base world position: origin at bridge_mr_end, same mc_end as staircase
        bridge_base_wx, bridge_base_wy = model_world_origin(
            bi['bridge_mr_end'], bi['stair_mc_end'], exp_rows, exp_cols)

        bridge_voxels = 0
        bridge_model_start = model_count

        def _place_bridge_models(results_list, label):
            nonlocal all_model_data, model_count, total_voxels, bridge_voxels
            struct_models = []
            for result, lx_off, ly_off, z_off in results_list:
                model_idx = model_count
                all_model_data += result['model_data']
                model_count += 1
                total_voxels += result['num_voxels']
                bridge_voxels += result['num_voxels']

                sx, sy, sz = result['size']
                wx = bridge_base_wx + lx_off
                wy = bridge_base_wy + ly_off
                t = model_translation(wx, wy, sx, sy, sz, shift_x, shift_y)
                t = (t[0], t[1], t[2] + z_off + 1)
                struct_models.append((model_idx, t, (sx, sy, sz)))
            if struct_models:
                structures.append({'models': struct_models})

        # 1. Deck
        deck_results = build_bridge_deck_models(bridge_rng, bridge_len)
        _place_bridge_models(deck_results, "deck")

        # 2. Balustrades (both sides: stringers + balusters + rails + lamps + supports)
        bal_rng = random.Random(seed_base + 66002)
        bridge_bal_sides = build_bridge_balustrade_models(
            bal_rng, bridge_len, bi['stair_at_high_lx'],
            bi['support_positions'])
        for side_results in bridge_bal_sides:
            _place_bridge_models(side_results, "balustrade")

        print(f"    Bridge placed ({bridge_voxels:,} voxels, "
              f"{model_count - bridge_model_start} models)", flush=True)

    print(f"    {len(structures)} total structures, {model_count} models, "
          f"{total_voxels:,} voxels", flush=True)

    filepath = os.path.join(output_dir, f"zone_{zone_name}.vox")
    write_structured_vox(filepath, all_model_data, structures, total_x, total_y, palette)
    print(f"    Written: {filepath}", flush=True)


# ============================================================
# Main
# ============================================================

def main():
    maze_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(maze_dir, "misc", "maze_layout.png")
    output_dir = os.path.join(maze_dir, "generated", "zones")
    os.makedirs(output_dir, exist_ok=True)

    print("Parsing maze image...", flush=True)
    grid = parse_maze_image(image_path)
    print(f"  {len(grid)} pixels classified", flush=True)

    zones = extract_zones(grid)
    palette = make_palette()

    # Global shelf set for cross-zone neighbor checks
    global_shelves = {(r, c) for (r, c), (_, tt) in grid.items() if tt in SHELF_LIKE_TYPES}

    # Global stair tiles (zone=None, tile_type='stair')
    stair_tiles = {(r, c) for (r, c), (_, tt) in grid.items() if tt == 'stair'}

    for zone_name in sorted(zones):
        zone_info = zones[zone_name]
        tiles = zone_info['tiles']
        shelf_count = sum(1 for t in tiles.values() if t in SHELF_LIKE_TYPES)
        floor_count = sum(1 for t in tiles.values() if t == 'floor')

        print(f"\nZone {zone_name}: {zone_info['num_rows']}x{zone_info['num_cols']} tiles "
              f"({shelf_count} shelves, {floor_count} floor)", flush=True)

        shelf_map = classify_shelves(tiles, global_shelves,
                                     zone_info['min_row'], zone_info['min_col'],
                                     global_grid=grid)
        type_counts = {}
        for _, (st, _) in shelf_map.items():
            type_counts[st] = type_counts.get(st, 0) + 1
        for st, cnt in sorted(type_counts.items()):
            print(f"    {st}: {cnt}", flush=True)

        generate_zone(zone_name, zone_info, shelf_map, palette, output_dir,
                       stair_tiles=stair_tiles)

    print(f"\nDone! Zone files written to: {output_dir}", flush=True)


if __name__ == "__main__":
    main()

