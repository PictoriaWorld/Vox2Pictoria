"""Snake Arcade Rainforest — Scene assembly.

Assembles individual parts into a 44x44 tile (1408x1408 voxel) scene
as a single multi-model .vox file with proper scene graph for Vox2Pictoria.

The 34x34 content area is centered inside a 5-tile padding border that
provides height-limit headroom.  Padding tiles get forest vegetation
scaled to their per-tile height limit (sparse at the very edge, denser
inward).  Content-area forest is built with the original edge-fade and
zone thresholds so the interior look is preserved.

Height zones for content forest (distance from content-area edge):
  Low (0-1):   52      Mid (2-4):   130     Tall (5-8):  235
  Inner (9+):  383
"""

import struct
import os
import random
import math

from generate_parts import (
    write_chunk, _write_dict, VoxelModel,
    make_palette, get_materials, save_palette_png,
    build_ground_forest, build_ground_clearing, build_boardwalk,
    build_tiki_torch, build_skull, build_arcade, build_arcade_cabinet,
    build_camp, build_snakeskin, build_tablet, build_sign,
    _fill_ground_layer, _fill_ground_cover, _scatter_flowers,
    _grow_trunk, _grow_branch, _grow_buttress, _grow_vines,
    _moss_on_trunk, _build_canopy_dome, _add_epiphytes,
    _leaf_cluster, _build_understory,
    G_BRIGHT, G_MID, G_DARK, EARTH_TONES, CLEARING_TONES,
    BARK_TONES, TRUNK_TONES, ROOT_TONES, MOSS_TONES,
    BOARDWALK_TONES, VINE_TONES, BAMBOO_TONES_ALL,
    BARK_PALETTE_OPTIONS, CANOPY_PALETTES,
    TORCH_FLAME_1, TORCH_FLAME_2, TORCH_ROPE, BAMBOO_NODE,
    BAMBOO_LIGHT, BAMBOO_MID_1, BAMBOO_MID_2, BAMBOO_DARK,
    STONE_LIGHT, STONE_MID, STONE_DARK,
    FLOWER_RED_1, FLOWER_RED_2, FLOWER_ORANGE,
    FLOWER_PINK, FLOWER_PURPLE, FLOWER_MAGENTA, FLOWER_WHITE,
    LEAF_BLUE_2, LEAF_BLUE_3,
    LEAF_DARK_1, LEAF_DARK_2, LEAF_DARK_3,
    LEAF_FRESH_1, LEAF_FRESH_2, LEAF_MID_1, LEAF_MID_2,
    LEAF_BRIGHT_1, LEAF_BRIGHT_2,
    streak,
    STAIN_TONES,
    EARTH_HUMUS, EARTH_DARK, EARTH_MUD, EARTH_PACKED, EARTH_LIGHT,
    EARTH_LITTER_1, EARTH_LITTER_2, EARTH_CLAY, EARTH_GRAVEL,
)


# ============================================================
# Constants
# ============================================================

EDGE_PADDING = 5             # padding tiles on each side for height-limit headroom
CONTENT_GRID_SIZE = 34       # original content area (34x34)
GRID_SIZE = CONTENT_GRID_SIZE + 2 * EDGE_PADDING  # 44
TILE_SIZE = 32               # 32 voxels per tile
WORLD_SIZE = GRID_SIZE * TILE_SIZE
MAX_PICT_TILES = 16  # 512 / 32
MAX_MV_TILES = 8     # 256 / 32

# Height limit by distance from property edge
_HEIGHT_TABLE = [1, 52, 78, 104, 130, 156, 182, 209, 235, 261, 287, 313, 339, 365, 384]

def max_height_for_tile(row, col):
    dist = min(row, col, GRID_SIZE - 1 - row, GRID_SIZE - 1 - col)
    idx = min(dist, len(_HEIGHT_TABLE) - 1)
    return _HEIGHT_TABLE[idx]


# Height zone thresholds (used only for tree tier/style selection, not grouping)
ZONE_LOW_MAX    = 52
ZONE_MID_MAX    = 130
ZONE_TALL_MAX   = 235

# Vegetation zone mapping: ring → veg_zone_max
# Controls what vegetation spawns (independent of Pictoria height limits)
# Rings 0-4: bare, 5: low start, 6-10: mid, 11-14: high, 15+: inner
def veg_zone_for_ring(d):
    if d <= 1:
        return 1       # leaf patches only
    elif d <= 5:
        return 10      # ground cover only — ferns, rocks, grass (below 30 = no understory trees)
    elif d == 6:
        return 30      # understory/ferns/rocks only (below 52 = no trees)
    elif d == 7:
        return 40      # understory only (below 52 = no main trees)
    elif d <= 10:
        return 130     # mid — medium trees
    elif d <= 14:
        return 235     # high — tall trees
    else:
        return 384     # inner — heroes possible


# ============================================================
# Boardwalk / platform / arcade layout
# ============================================================

# Platform: 7x7 tiles (offset by EDGE_PADDING)
PLATFORM_R_START, PLATFORM_R_END = 13 + EDGE_PADDING, 19 + EDGE_PADDING
PLATFORM_C_START, PLATFORM_C_END = 13 + EDGE_PADDING, 19 + EDGE_PADDING

# Arcade: positioned by world coords, not tile
ARCADE_ROW, ARCADE_COL = 16 + EDGE_PADDING, 16 + EDGE_PADDING

# Platform deck world-z (elevated above canopy)
PLATFORM_DECK_Z = 280

# Boardwalk: 2 tiles wide, climbs from south (offset by EDGE_PADDING)
BOARDWALK_COLS = (16 + EDGE_PADDING, 17 + EDGE_PADDING)
BOARDWALK_ROW_START = 31 + EDGE_PADDING   # southernmost (entry)
BOARDWALK_ROW_END = 20 + EDGE_PADDING     # connects to platform south edge

# Deck clearance above ground for boardwalk stilts at entry
DECK_CLEARANCE = 10

# Locked ring 15+ trees: (wx, wy, seed) — deterministic regardless of code changes
INNER_TREES = [
    (897,527,47804753),(926,569,1503649994),(815,503,398186343),(908,618,1601105040),
    (883,568,585993450),(756,513,165948251),(859,661,221309012),(789,567,2071118315),
    (736,564,475550730),(865,606,1332150035),(838,536,687707461),(685,489,852273223),
    (686,539,65955444),(900,678,1534517269),(926,740,1072921206),
    (818,886,601839122),(886,759,1114880407),(848,846,2030855890),(878,800,1099687153),
    (896,864,1357016230),(564,505,732288846),(608,554,1081987958),
    (594,626,156507457),(881,863,1376289815),(510,558,1734389991),(504,602,1878370879),
    (781,896,1327245464),(666,840,396427735),(831,919,1602643431),(559,565,1024983102),
    (897,913,1147927019),(561,759,1446432959),(752,854,448815349),(864,839,628056566),
    (486,653,1349818055),(652,899,283423199),(555,635,129374172),(740,909,924366217),
    (520,505,798510432),(678,885,1444035888),(482,788,1543734922),(604,876,1965393946),
    (596,824,1261055773),(532,794,2101423603),(582,838,895864729),(493,855,1747456774),
    (550,892,1830040134),(534,848,388314920),(494,917,1351741359),
]


def compute_boardwalk_boundaries(rng):
    """Compute deck z at each row boundary for the inclined boardwalk.

    Returns list of 13 world-z values (12 segments).
    boundaries[0] = south edge (entry_z=1)
    boundaries[12] = PLATFORM_DECK_Z
    Total rise = 279. Bresenham handles non-divisible rises per segment.
    Random weights give varied slopes for a rustic feel.
    """
    n_segments = BOARDWALK_ROW_START - BOARDWALK_ROW_END + 1  # 12
    entry_z = 1
    total_rise = PLATFORM_DECK_Z  # 280 — boardwalk spans 280 voxels of rise

    # Random weights → varied rise per segment
    weights = [rng.uniform(0.7, 1.3) for _ in range(n_segments)]
    total_w = sum(weights)
    # Distribute total_rise as integers, rounding to keep sum exact
    rises = [int(total_rise * w / total_w) for w in weights]
    # Fix rounding error: distribute remainder
    remainder = total_rise - sum(rises)
    for i in range(remainder):
        rises[i] += 1

    boundaries = [entry_z]
    for rise in rises:
        boundaries.append(boundaries[-1] + rise)
    return boundaries


# ============================================================
# Grid building
# ============================================================


def build_grid():
    """Build tile grid with forest, boardwalk, platform, and arcade tiles."""
    grid = {}
    boardwalk_tiles = set()

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            grid[(r, c)] = 'forest'

    # Platform
    for r in range(PLATFORM_R_START, PLATFORM_R_END + 1):
        for c in range(PLATFORM_C_START, PLATFORM_C_END + 1):
            grid[(r, c)] = 'platform'

    # Arcade (within platform)
    grid[(ARCADE_ROW, ARCADE_COL)] = 'arcade'

    # Boardwalk: 2 tiles wide, rows 18-31
    for r in range(BOARDWALK_ROW_END, BOARDWALK_ROW_START + 1):
        for c in BOARDWALK_COLS:
            if grid[(r, c)] == 'forest':
                grid[(r, c)] = 'boardwalk'
                boardwalk_tiles.add((r, c))

    # Dirt path from boardwalk entry to property edge
    for r in range(BOARDWALK_ROW_START + 1, GRID_SIZE):
        for c in BOARDWALK_COLS:
            if grid[(r, c)] == 'forest':
                grid[(r, c)] = 'path'

    return grid, boardwalk_tiles


# ============================================================
# Structure decomposition (from maze example)
# ============================================================

def decompose_into_rectangles(positions):
    """Greedy rectangle decomposition of a set of positions."""
    remaining = set(positions)
    rects = []
    while remaining:
        r, c = min(remaining)
        c_end = c
        while (r, c_end + 1) in remaining:
            c_end += 1
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
    """Split a tile rectangle into Pictoria structures containing MV models."""
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
# World coordinate helpers
# ============================================================

def tile_world_pos(row, col):
    """World position of tile (row, col)'s (0,0,0) corner in the 32x32 grid."""
    return (GRID_SIZE - 1 - row) * TILE_SIZE, (GRID_SIZE - 1 - col) * TILE_SIZE


def model_world_origin(mr_end, mc_end, dx=0, dy=0):
    wx, wy = tile_world_pos(mr_end, mc_end)
    return wx + dx, wy + dy


def model_translation(world_x, world_y, size_x, size_y, size_z, shift_x, shift_y):
    centered_x = world_x - shift_x
    centered_y = world_y - shift_y
    translate_x = centered_x + size_x // 2
    translate_y = centered_y + size_y // 2
    translate_z = size_z // 2
    return (translate_x, translate_y, translate_z)


def compute_parent_translation(children):
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
# Model serialization
# ============================================================

def _serialize_model(xyzi_bytes, voxel_count, maxes):
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


def _voxelmodel_to_serialized(model):
    """Serialize a VoxelModel into model_data dict. Skips out-of-range voxels."""
    xyzi_bytes = bytearray()
    maxes = (0, 0, 0)
    count = 0
    for (x, y, z), c in model._v.items():
        if x < 0 or x > 255 or y < 0 or y > 255 or z < 0 or z > 255:
            continue
        xyzi_bytes.extend((x, y, z, c))
        if x > maxes[0]: maxes = (x, maxes[1], maxes[2])
        if y > maxes[1]: maxes = (maxes[0], y, maxes[2])
        if z > maxes[2]: maxes = (maxes[0], maxes[1], z)
        count += 1
    if count == 0:
        return None
    return _serialize_model(xyzi_bytes, count, maxes)


def _voxelmodel_to_vertical_slices(model):
    """Split a VoxelModel into <=256-high vertical slices.
    Returns list of (serialized_model_dict, z_offset) tuples."""
    if not model._v:
        return []
    explicit = model._explicit_size
    max_z = (explicit[2] - 1) if explicit else max(z for (_, _, z) in model._v.keys())
    slices = []
    for z_base in range(0, max_z + 1, 256):
        z_top = z_base + 255
        xyzi_bytes = bytearray()
        # Start maxes from explicit size if set, else from content
        if explicit:
            slice_max_z = min(explicit[2] - 1, z_top) - z_base
            maxes = (explicit[0] - 1, explicit[1] - 1, slice_max_z)
        else:
            maxes = (0, 0, 0)
        count = 0
        for (x, y, z), c in model._v.items():
            if z < z_base or z > z_top:
                continue
            if x < 0 or x > 255 or y < 0 or y > 255:
                continue
            lz = z - z_base  # local z within this slice
            xyzi_bytes.extend((x, y, lz, c))
            if not explicit:
                if x > maxes[0]: maxes = (x, maxes[1], maxes[2])
                if y > maxes[1]: maxes = (maxes[0], y, maxes[2])
                if lz > maxes[2]: maxes = (maxes[0], maxes[1], lz)
            count += 1
        if count > 0:
            slices.append((_serialize_model(xyzi_bytes, count, maxes), z_base))
    return slices


# ============================================================
# Model builders for scene
# ============================================================

HILL_PEAK_HEIGHT = 160  # max ground elevation at center (leaves ~224 voxels for trees at inner zone)
HILL_CENTER_WORLD = WORLD_SIZE // 2  # center of world in voxels
_HILL_RADIUS = CONTENT_GRID_SIZE * TILE_SIZE // 2  # fixed radius — preserves hill shape


def _hill_elevation(world_x, world_y):
    """Compute ground elevation at a world-space voxel position.
    Smooth hill peaking at center, falling to 0 beyond _HILL_RADIUS."""
    dx = world_x - HILL_CENTER_WORLD
    dy = world_y - HILL_CENTER_WORLD
    dist = math.sqrt(dx * dx + dy * dy)
    t = max(0.0, 1.0 - dist / _HILL_RADIUS)
    return int(HILL_PEAK_HEIGHT * t * t)


def build_forest_model(mr, mc, mr_end, mc_end, zone_max_height, rng, grid, boardwalk_tiles):
    """Build a forest model covering the given tile range.

    zone_max_height is the MAX height limit across the block (for tree tier
    selection).  Per-position heights come from _HEIGHT_TABLE so trees near
    the property edge are shorter.  Trees whose canopy extends into a ring
    with a LOWER limit are dropped entirely.
    """
    width = (mr_end - mr + 1) * TILE_SIZE
    depth = (mc_end - mc + 1) * TILE_SIZE
    m = VoxelModel()
    max_xi = width - 1
    max_yi = depth - 1

    # Compute ground elevation range for this model region
    # World coords: model local (0,0) = tile (mr_end, mc_end) corner
    def _local_to_world(lx, ly):
        wx = (GRID_SIZE - 1 - mr_end) * TILE_SIZE + lx
        wy = (GRID_SIZE - 1 - mc_end) * TILE_SIZE + ly
        return wx, wy

    def _ring_at(lx, ly):
        """Property-edge distance of local position."""
        wx, wy = _local_to_world(lx, ly)
        r = GRID_SIZE - 1 - wx // TILE_SIZE
        c = GRID_SIZE - 1 - wy // TILE_SIZE
        return min(r, c, GRID_SIZE - 1 - r, GRID_SIZE - 1 - c)

    # Find min/max ground elevation across this model
    min_elev = 999
    max_elev = 0
    for lx in range(0, width, 4):  # sample every 4 voxels
        for ly in range(0, depth, 4):
            wx, wy = _local_to_world(lx, ly)
            e = _hill_elevation(wx, wy)
            min_elev = min(min_elev, e)
            max_elev = max(max_elev, e)

    # The model z=0 starts at min_elev in world space.
    # Vertical slicing handles z>255, so max_z can exceed 255.
    base_elev = min_elev
    max_z = zone_max_height - base_elev - 1  # overall model bound

    def _max_z_at(lx, ly):
        """Per-position height limit from _HEIGHT_TABLE."""
        d = _ring_at(lx, ly)
        return _HEIGHT_TABLE[min(d, len(_HEIGHT_TABLE) - 1)] - base_elev - 1

    # Fill ground: hill terrain relative to base_elev
    # Boardwalk tiles get flat ground at z=1
    for lx in range(width):
        for ly in range(depth):
            wx, wy = _local_to_world(lx, ly)
            tile_r = GRID_SIZE - 1 - wx // TILE_SIZE
            tile_c = GRID_SIZE - 1 - wy // TILE_SIZE
            if (tile_r, tile_c) in boardwalk_tiles or grid.get((tile_r, tile_c)) == 'path':
                elev = max(0, 1 - base_elev)
            else:
                elev = max(0, _hill_elevation(wx, wy) - base_elev)
            edge_dist = min(wx, wy, WORLD_SIZE - 1 - wx, WORLD_SIZE - 1 - wy)
            is_outer_ring = edge_dist < TILE_SIZE

            for z in range(elev + 1):
                r_val = rng.random()
                if z == elev:
                    if is_outer_ring:
                        # Outer ring: dark ground with embedded rocks
                        if r_val < 0.03:
                            m.set(lx, ly, z, rng.choice([STONE_MID, STONE_DARK]))
                        elif r_val < 0.35:
                            m.set(lx, ly, z, rng.choice(G_DARK))
                        else:
                            m.set(lx, ly, z, rng.choice(EARTH_TONES))
                    else:
                        if r_val < 0.35:
                            m.set(lx, ly, z, rng.choice(G_DARK))
                        else:
                            m.set(lx, ly, z, rng.choice(EARTH_TONES))
                else:
                    m.set(lx, ly, z, rng.choice(EARTH_TONES))

    # Precompute ground elevation at sampled points for tree placement
    def _ground_z(lx, ly):
        wx, wy = _local_to_world(lx, ly)
        return _hill_elevation(wx, wy) - base_elev

    def _edge_fade(lx, ly):
        """Returns fade value from 0.0 at property edge to 1.0 three tiles in."""
        wx, wy = _local_to_world(lx, ly)
        dist = min(wx, wy, WORLD_SIZE - 1 - wx, WORLD_SIZE - 1 - wy)
        return min(1.0, dist / (TILE_SIZE * 3))

    # Trees based on zone height
    all_canopy = []
    trunk_positions = set()

    def try_tree(h_range, w_range, r_range, n_branches, n_buttresses):
        for _ in range(50):
            tx = rng.randint(8, max(9, max_xi - 8))
            ty = rng.randint(8, max(9, max_yi - 8))
            too_close = any(abs(tx - ex) + abs(ty - ey) < 14 for ex, ey in trunk_positions)
            if too_close:
                continue
            trunk_positions.add((tx, ty))

            # Skip trees near property edge based on fade
            fade = _edge_fade(tx, ty)
            if rng.random() > fade:
                continue

            # Per-position height cap
            gz = _ground_z(tx, ty)
            local_max_z = _max_z_at(tx, ty)
            available_z = local_max_z - gz

            h = rng.randint(h_range[0], h_range[1])
            h = min(h, available_z)
            # Scale tree height down near edge
            h = max(5, int(h * fade))
            if h < 5:
                return
            w = rng.randint(w_range[0], w_range[1])

            bark = rng.choice(BARK_PALETTE_OPTIONS)
            canopy_pal = rng.choice(CANOPY_PALETTES)
            has_moss = rng.random() < 0.35

            # ~12% of trees are flowering — pick one flower color
            is_flowering = rng.random() < 0.12
            if is_flowering:
                flower_color = rng.choices(
                    [FLOWER_RED_1, FLOWER_RED_2, FLOWER_WHITE],
                    weights=[3, 3, 2], k=1)[0]
            else:
                flower_color = None

            # Build entire tree into a temp model for extension check
            tree_m = VoxelModel()

            trunk_m = VoxelModel()
            path = _grow_trunk(trunk_m, tx, ty, h, w, rng, tones=bark,
                              max_x=max_xi, max_y=max_yi)
            shifted_path = []
            for (vx, vy, vz), c in trunk_m._v.items():
                tree_m.set(vx, vy, vz + gz, c)
            for (px, py, pz) in path:
                shifted_path.append((px, py, pz + gz))

            if has_moss:
                _moss_on_trunk(tree_m, shifted_path, w, rng, max_x=max_xi, max_y=max_yi)
            if rng.random() < 0.4:
                _add_epiphytes(tree_m, shifted_path, w, rng,
                              max_x=max_xi, max_y=max_yi, max_z=local_max_z)

            # Buttress roots at ground level
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]
            rng.shuffle(dirs)
            butt_h = max(5, h // 8)
            for bi in range(min(n_buttresses, len(dirs))):
                ddx, ddy = dirs[bi]
                _grow_buttress(tree_m, tx, ty, gz, ddx * 0.7, ddy * 0.7, rng,
                              max_x=max_xi, max_y=max_yi, height=butt_h)

            # Dome canopy
            tree_canopy = []
            if len(shifted_path) > 10:
                trunk_height = len(shifted_path)
                tree_canopy = _build_canopy_dome(tree_m, shifted_path, trunk_height, bark, canopy_pal,
                                                  r_range, rng, max_xi, max_yi, local_max_z)

                # Flowering tree: scatter flowers across this tree's canopy
                if flower_color and tree_canopy:
                    num_flowers = max(5, len(tree_canopy) // 8)
                    for _ in range(num_flowers):
                        pos = rng.choice(tree_canopy)
                        fx = pos[0] + rng.randint(-1, 1)
                        fy = pos[1] + rng.randint(-1, 1)
                        fz = pos[2] + rng.randint(-1, 1)
                        if 0 <= fx <= max_xi and 0 <= fy <= max_yi and 0 <= fz <= local_max_z:
                            tree_m.set(fx, fy, fz, flower_color)

            # Drop tree if canopy extends into a ring with LOWER height limit
            trunk_ring = _ring_at(tx, ty)
            extends_outward = False
            for (vx, vy, _) in tree_m._v:
                if _ring_at(vx, vy) < trunk_ring:
                    extends_outward = True
                    break
            if extends_outward:
                continue  # drop this tree, try next position

            # Merge approved tree into main model
            for (vx, vy, vz), c in tree_m._v.items():
                m.set(vx, vy, vz, c)
            all_canopy.extend(tree_canopy)
            return

    # Scale tree count by area
    area_tiles = (mr_end - mr + 1) * (mc_end - mc + 1)

    if zone_max_height >= 235:
        # Hero emergents: 2-3 massive trees with BIG canopy clusters
        for _ in range(min(3, max(2, area_tiles // 8))):
            try_tree((180, max_z - 5), (5, 7), (14, 20),
                    rng.randint(8, 12), rng.randint(5, 6))
        # Regular emergents
        for _ in range(max(2, area_tiles // 6)):
            try_tree((120, max_z - 20), (4, 6), (9, 14),
                    rng.randint(4, 6), rng.randint(4, 6))
        # Varied canopy
        for _ in range(max(4, area_tiles // 3)):
            try_tree((30, max_z - 20), (2, 4), (7, 10),
                    rng.randint(2, 4), rng.randint(2, 3))
    elif zone_max_height >= 130:
        # Mid zone — varied heights
        for _ in range(max(3, area_tiles // 3)):
            try_tree((30, max_z - 20), (2, 4), (7, 10),
                    rng.randint(2, 4), rng.randint(2, 3))
    elif zone_max_height >= 52:
        # Low zone — scale tree style with available budget
        tree_h_cap = max(16, max_z - 10)
        tree_w = (1, min(3, 1 + tree_h_cap // 40))
        canopy_r = (4, min(8, 4 + tree_h_cap // 30))
        for _ in range(max(2, area_tiles // 4)):
            try_tree((15, tree_h_cap), tree_w, canopy_r,
                    rng.randint(1, 2), rng.randint(1, 2))

    # Understory — placed at ground level
    num_under = max(12, area_tiles * 2)
    for _ in range(num_under):
        ux = rng.randint(3, max(4, max_xi - 3))
        uy = rng.randint(3, max(4, max_yi - 3))
        fade = _edge_fade(ux, uy)
        if fade < 0.34 or rng.random() > fade:
            continue
        gz = _ground_z(ux, uy)
        avail = _max_z_at(ux, uy) - gz
        if avail < 3:
            continue
        max_h = max(3, int(int(avail * 0.5) * fade))
        under_m = VoxelModel()
        _build_understory(under_m, ux, uy, max_h, rng,
                         max_x=max_xi, max_y=max_yi, max_z=avail)
        for (vx, vy, vz), c in under_m._v.items():
            if vz + gz <= _max_z_at(ux, uy):
                m.set(vx, vy, vz + gz, c)

    # Mossy stones scattered on the hill
    num_stones = max(2, area_tiles // 4)
    for _ in range(num_stones):
        sx = rng.randint(5, max(6, max_xi - 5))
        sy = rng.randint(5, max(6, max_yi - 5))
        gz = _ground_z(sx, sy)
        stone_r = rng.randint(2, 5)
        stone_h = rng.randint(2, 4)
        # In outer ring, flatten stones to ground level only
        fade = _edge_fade(sx, sy)
        if fade < 0.34:
            stone_h = 1
        local_limit = _max_z_at(sx, sy)
        if gz + stone_h > local_limit:
            stone_h = max(1, local_limit - gz)
        for dx in range(-stone_r, stone_r + 1):
            for dy in range(-stone_r, stone_r + 1):
                if dx * dx + dy * dy <= stone_r * stone_r:
                    for dz in range(stone_h):
                        px, py, pz = sx + dx, sy + dy, gz + dz
                        if 0 <= px <= max_xi and 0 <= py <= max_yi and pz >= 0:
                            if dz == stone_h - 1 and rng.random() < 0.6:
                                m.set(px, py, pz, rng.choice(MOSS_TONES))
                            else:
                                m.set(px, py, pz, rng.choice([STONE_LIGHT, STONE_MID, STONE_DARK]))

    # Vines — heavy hanging lianas from canopy and high branches
    if all_canopy:
        _grow_vines(m, all_canopy, rng, count=max(15, area_tiles * 2),
                    max_x=max_xi, max_y=max_yi, max_z=max_z)


    # Dense ground cover at terrain surface — faded near edge
    floor_pal = (G_DARK, G_DARK, [LEAF_DARK_1, LEAF_DARK_2, LEAF_DARK_3, LEAF_BLUE_2, LEAF_BLUE_3])
    for _ in range((width * depth) // 16):
        cx = rng.randint(2, max(3, max_xi - 2))
        cy = rng.randint(2, max(3, max_yi - 2))
        fade = _edge_fade(cx, cy)
        if rng.random() > fade:
            continue
        gz = _ground_z(cx, cy)
        # In outer ring (fade < 0.34), keep plants flat at ground level
        if fade < 0.34:
            cover_max_z = gz
        else:
            cover_max_z = min(gz + 8, _max_z_at(cx, cy))
        r_val = rng.uniform(2.0, 4.0)
        _leaf_cluster(m, cx, cy, gz, r_val, floor_pal, rng,
                     max_x=max_xi, max_y=max_yi, max_z=cover_max_z)

    # Broad-leaf plants and ground ferns on terrain — faded near edge
    from generate_parts import _build_broad_leaf_plant, _build_giant_fern
    for _ in range((width * depth) // 250):
        bx = rng.randint(3, max(4, max_xi - 3))
        by = rng.randint(3, max(4, max_yi - 3))
        fade_bx = _edge_fade(bx, by)
        if fade_bx < 0.34 or rng.random() > fade_bx:
            continue
        gz = _ground_z(bx, by)
        plant_max_z = _max_z_at(bx, by) - gz
        if plant_max_z < 3:
            continue
        plant_m = VoxelModel()
        if rng.random() < 0.5:
            _build_broad_leaf_plant(plant_m, bx, by, rng,
                                   max_x=max_xi, max_y=max_yi, max_z=plant_max_z)
        else:
            _build_giant_fern(plant_m, bx, by, rng,
                             max_x=max_xi, max_y=max_yi, max_z=plant_max_z)
        for (vx, vy, vz), c in plant_m._v.items():
            if vz + gz <= _max_z_at(bx, by):
                m.set(vx, vy, vz + gz, c)

    return m, base_elev


def _place_tiki_torch(model, x, y, rng):
    """Place a tiki torch at the given position within a model."""
    pole_height = 22
    for z in range(pole_height):
        tone = BAMBOO_MID_1
        if z % 5 == 0:
            tone = BAMBOO_NODE
        elif z % 5 == 1:
            tone = BAMBOO_DARK
        else:
            tone = rng.choice([BAMBOO_LIGHT, BAMBOO_MID_1, BAMBOO_MID_2])
        for dx in range(2):
            for dy in range(2):
                model.set(x + dx, y + dy, z, tone)
    # Rope
    for z in [pole_height - 4, pole_height - 3]:
        for dx in range(-1, 3):
            for dy in range(-1, 3):
                if (dx in (-1, 2)) or (dy in (-1, 2)):
                    model.set(x + dx, y + dy, z, TORCH_ROPE)
    # Fire bowl
    bowl_z = pole_height
    for dx in range(4):
        for dy in range(4):
            edge = (dx == 0 or dx == 3 or dy == 0 or dy == 3)
            if edge:
                model.set(x - 1 + dx, y - 1 + dy, bowl_z, BAMBOO_DARK)
            else:
                model.set(x - 1 + dx, y - 1 + dy, bowl_z,
                         rng.choice([TORCH_FLAME_1, TORCH_FLAME_2]))
    for dz in range(1, 3):
        for dx in range(1, 3):
            for dy in range(1, 3):
                model.set(x - 1 + dx, y - 1 + dy, bowl_z + dz,
                         rng.choice([TORCH_FLAME_1, TORCH_FLAME_2]))


def _weather_planks(m, rng):
    """Weather boardwalk/platform planks: scattered moss."""
    bw_set = set(BOARDWALK_TONES)
    for (vx, vy, vz), c in list(m._v.items()):
        if c in bw_set and rng.random() < 0.20:
            m.set(vx, vy, vz, rng.choice([MOSS_TONES[2], MOSS_TONES[3],
                                           MOSS_TONES[5], MOSS_TONES[7]]))


def build_clearing_model(mr, mc, mr_end, mc_end, rng):
    """Build clearing model: ground + sparse low cover."""
    width = (mr_end - mr + 1) * TILE_SIZE
    depth = (mc_end - mc + 1) * TILE_SIZE
    m = VoxelModel()

    for x in range(width):
        for y in range(depth):
            c = rng.choice(CLEARING_TONES)
            if rng.random() < 0.04:
                c = rng.choice(MOSS_TONES[:4])
            m.set(x, y, 0, c)

    # Sparse ground cover
    for _ in range((width * depth) // 80):
        cx = rng.randint(1, width - 2)
        cy = rng.randint(1, depth - 2)
        r = rng.uniform(1.0, 2.0)
        _leaf_cluster(m, cx, cy, 1, r, (G_BRIGHT, G_MID, G_DARK), rng,
                     max_x=width - 1, max_y=depth - 1, max_z=4)

    return m


def _build_bearer_beams(m, lx_base, ly_base, width, depth, rng, z_func,
                        beam_positions, beam_width_range=(1, 2), lx_offset=0):
    """Lay longitudinal bearer beams running along lx (direction of rise).

    These beams sit 1-2 voxels below the plank surface and provide the
    structural support that planks rest on.
    beam_positions: list of ly positions where beams run.
    beam_width_range: (min, max) width of each beam in ly direction.
    lx_offset: shift beam draw position in the ascending direction.
    """
    for by in beam_positions:
        beam_width = rng.randint(beam_width_range[0], beam_width_range[1])
        for lx in range(width):
            draw_lx = lx + lx_offset
            if draw_lx >= width:
                break
            base_z = z_func(lx)  # z from original position
            beam_z = base_z - 1
            for dw in range(beam_width):
                py = ly_base + by + dw
                if 0 <= py < ly_base + depth:
                    if rng.random() < 0.02:
                        continue
                    m.set(lx_base + draw_lx, py, beam_z, rng.choice(BOARDWALK_TONES))


def _lay_planks(m, lx_base, ly_base, width, depth, rng, z_func,
                plank_widths=(2, 3, 3, 4, 4, 5, 6), gap_range=(1, 2),
                trim_choices=(0, 0, 0, 1, 2, 3, 5, 7)):
    """Lay rickety planks across a deck surface.

    Each plank is one long board spanning most/all of the depth (ly).
    z_func(lx) returns the base deck z at a given lx position.
    """
    lx = 0
    while lx < width:
        # Gap between plank rows along lx
        lx += rng.randint(gap_range[0], gap_range[1])
        if lx >= width:
            break

        # Width of this plank in lx
        plank_w = rng.choices(plank_widths, k=1)[0]
        plank_w = min(plank_w, width - lx)
        z_wobble = 0  # all planks at same z for walkability

        # Each plank spans most/all of the depth, with random trim at ends
        trim_start = rng.choices(trim_choices, k=1)[0]
        trim_end = rng.choices(trim_choices, k=1)[0]
        dy_start = trim_start
        dy_end = depth - trim_end
        if dy_end <= dy_start + 4:
            dy_start = 0
            dy_end = depth

        plank_len = dy_end - dy_start
        tone = streak(BOARDWALK_TONES, plank_len, rng)

        # Use z at leftmost edge — entire plank is a flat stair tread
        # guaranteed under the hypotenuse (int truncation creates bottom/top gaps)
        base_z = z_func(lx) + z_wobble

        for pw in range(plank_w):
            curr_lx = lx + pw
            if curr_lx >= width:
                break
            # Irregular edges: jitter start/end per row
            row_start = dy_start + rng.randint(-1, 2)
            row_end = dy_end + rng.randint(-2, 1)
            row_start = max(0, row_start)
            row_end = min(depth, row_end)
            if row_end <= row_start:
                continue
            for ply in range(row_end - row_start):
                if rng.random() < 0.03:
                    continue
                tone_idx = min(ply + row_start - dy_start, plank_len - 1)
                tone_idx = max(0, tone_idx)
                c = tone[tone_idx]
                # Per-voxel noise: ~20% chance to shift to a nearby boardwalk tone
                if rng.random() < 0.20:
                    bw_idx = BOARDWALK_TONES.index(c) if c in BOARDWALK_TONES else -1
                    if bw_idx >= 0:
                        new_idx = max(0, min(len(BOARDWALK_TONES) - 1,
                                             bw_idx + rng.choice([-1, 1])))
                        c = BOARDWALK_TONES[new_idx]
                m.set(lx_base + curr_lx, ly_base + row_start + ply, base_z, c)

        lx += plank_w


def _build_inclined_deck(m, lx_base, ly_base, south_z, north_z, width, depth, rng,
                         n_steps=3, include_transition_step=False):
    """Build an inclined deck as a staircase under the hypotenuse.

    N steps with stepDepth = advance / (N+1).
    Step i cumulative z = floor(rise * i / (N+1))  (Bresenham integer formula).
    Varying integer step heights track the hypotenuse without requiring
    rise to be divisible by (N+1).

    If include_transition_step, step 0 is included (at z below south_z)
    to bridge the gap from the previous segment. It ends up in the base model.
    """
    advance = width
    rise = north_z - south_z
    n_div = n_steps + 1
    step_depth = advance / n_div
    step_rise = rise / n_div
    def _step_start(i):
        return math.ceil(i * step_depth)
    def z_func(lx):
        if rise <= 0:
            return south_z
        step = min(lx * n_div // advance, n_steps)
        if step == 0 and not include_transition_step:
            return south_z - 1  # bottom gap — no deck in prism
        return south_z + math.floor(step * step_rise) - 1
    # Bearer beams at ~1/4, 1/2, 3/4 across the depth (with jitter)
    beam_positions = [
        max(3, depth // 4 + rng.randint(-2, 2)),
        depth // 2 + rng.randint(-2, 2),
        min(depth - 4, 3 * depth // 4 + rng.randint(-2, 2)),
    ]
    # Beam diagonal: starts 1 step_rise lower when transition step included
    beam_z_start = south_z - 1 if not include_transition_step else south_z - 1 - math.floor(step_rise)
    def beam_z_func(lx):
        return beam_z_start + (rise * lx) // max(1, width)
    _build_bearer_beams(m, lx_base, ly_base, width, depth, rng, beam_z_func, beam_positions,
                        lx_offset=2)

    # Lay one plank per step with rickety varying widths
    plank_drawn_widths = (3, 4, 4, 4, 5, 5, 5, 6, 6, 6)
    offset_choices = (0, 0, 0, 1, 1, 2)
    z_wobble_choices = (0, 0, 0, 0, -1)
    trim_choices = (0, 0, 0, 1, 2, 3, 5, 7)
    first_step = 0 if include_transition_step else 1
    print(f"  step_depth={step_depth}, step_rise={step_rise}, n_steps={n_steps}, n_div={n_div}")
    for i in range(first_step, n_div):
        step_lx = _step_start(i)
        step_z = south_z + math.floor(i * step_rise) - 1 + rng.choice(z_wobble_choices)

        # Random offset forward (ascending direction) — creates rickety gaps
        offset = rng.choice(offset_choices)
        plank_lx = step_lx + offset

        # Random drawn width 3-6, favouring wider planks
        plank_w = rng.choice(plank_drawn_widths)
        plank_w = min(plank_w, width - plank_lx)

        prism_z = step_z - south_z
        print(f"  step {i}: start_x={plank_lx} (step_lx={step_lx}+offset={offset}), "
              f"width={plank_w}, end_x={plank_lx + plank_w}, z={prism_z}")

        # Per-plank ly trim and color streak
        trim_start = rng.choices(trim_choices, k=1)[0]
        trim_end = rng.choices(trim_choices, k=1)[0]
        dy_start = trim_start
        dy_end = depth - trim_end
        if dy_end <= dy_start + 4:
            dy_start = 0
            dy_end = depth
        plank_len = dy_end - dy_start
        tone = streak(BOARDWALK_TONES, plank_len, rng)

        for pw in range(plank_w):
            curr_lx = plank_lx + pw
            if curr_lx >= width:
                break
            # Irregular edges: jitter start/end per column
            row_start = max(0, dy_start + rng.randint(-1, 2))
            row_end = min(depth, dy_end + rng.randint(-2, 1))
            if row_end <= row_start:
                continue
            for ply in range(row_end - row_start):
                if rng.random() < 0.03:
                    continue
                tone_idx = max(0, min(ply + row_start - dy_start, plank_len - 1))
                c = tone[tone_idx]
                if rng.random() < 0.20:
                    bw_idx = BOARDWALK_TONES.index(c) if c in BOARDWALK_TONES else -1
                    if bw_idx >= 0:
                        new_idx = max(0, min(len(BOARDWALK_TONES) - 1,
                                             bw_idx + rng.choice([-1, 1])))
                        c = BOARDWALK_TONES[new_idx]
                m.set(lx_base + curr_lx, ly_base + row_start + ply, step_z, c)

    return beam_positions


def _build_flat_deck(m, lx_base, ly_base, deck_z, width, depth, rng,
                     beam_width_range=(1, 2), num_beams=3,
                     plank_widths=None, plank_gap_range=None,
                     plank_trim_choices=None):
    """Build a flat deck: bearer beams + planks on top."""
    beam_positions = [
        max(3, int(depth * (i + 1) / (num_beams + 1)) + rng.randint(-2, 2))
        for i in range(num_beams)
    ]
    _build_bearer_beams(m, lx_base, ly_base, width, depth, rng, lambda lx: deck_z,
                        beam_positions, beam_width_range)
    kwargs = {}
    if plank_widths is not None:
        kwargs['plank_widths'] = plank_widths
    if plank_gap_range is not None:
        kwargs['gap_range'] = plank_gap_range
    if plank_trim_choices is not None:
        kwargs['trim_choices'] = plank_trim_choices
    _lay_planks(m, lx_base, ly_base, width, depth, rng, lambda lx: deck_z, **kwargs)
    return beam_positions


def build_boardwalk_segment(row, south_z, north_z, rng, n_tiles=1, include_transition_step=False):
    """Build a boardwalk segment spanning n_tiles tiles as one prism model.

    Returns (prism_model, base_model_or_None).
    prism_model has explicit size advance × depth × (rise + 1).
    base_model is None when south_z <= 1 (nothing meaningful below).
    """
    mc_end = BOARDWALK_COLS[1]
    width = n_tiles * TILE_SIZE
    depth = (BOARDWALK_COLS[1] - BOARDWALK_COLS[0] + 1) * TILE_SIZE  # 64
    m = VoxelModel()

    south_z_local = south_z
    north_z_local = north_z

    rise = north_z_local - south_z_local
    advance = width
    n_div = advance // 4 * 85 // 100  # 85% of original, average step depth ≈ 4.7
    n_steps = n_div - 1
    step_depth_local = advance / n_div
    step_rise_local = rise / n_div
    def _deck_z_at_lx(lx):
        if rise <= 0:
            return south_z_local
        step = min(int(lx / step_depth_local), n_steps)
        if step == 0:
            return south_z_local  # bottom gap
        return south_z_local + math.floor(step * step_rise_local)

    # Fill ground terrain
    for lx in range(width):
        for ly in range(depth):
            m.set(lx, ly, 0, rng.choice(EARTH_TONES))

    # Build inclined deck (beams + planks); get beam ly positions back
    beam_positions = _build_inclined_deck(m, 0, 0, south_z_local, north_z_local, width, depth, rng,
                                          n_steps=n_steps,
                                          include_transition_step=include_transition_step)

    # Stilts: candidates every ~16 lx along beam positions and edges
    margin_x = 4
    margin_y = 4
    stilt_lx_positions = list(range(margin_x, width - margin_x, 16))
    all_stilt_candidates = []
    for slx in stilt_lx_positions:
        for by in beam_positions:
            all_stilt_candidates.append((slx, by))
    for slx in stilt_lx_positions:
        for sy in [margin_y, depth - 1 - margin_y]:
            all_stilt_candidates.append((slx, sy))
    # Keep 50%
    stilt_positions = [s for s in all_stilt_candidates if rng.random() < 0.5]

    # Plus-shaped 4×4 stilt posts (no corner voxels)
    _plus_offsets = [(dx, dy) for dx in range(4) for dy in range(4)
                     if not ((dx in (0, 3)) and (dy in (0, 3)))]

    for sx, sy in stilt_positions:
        dz = _deck_z_at_lx(sx) - 1
        if dz <= 0:
            continue
        for z in range(1, dz):
            for ddx, ddy in _plus_offsets:
                px, py = sx - 1 + ddx, sy - 1 + ddy
                if 0 <= px < width and 0 <= py < depth:
                    m.set(px, py, z, rng.choice(BOARDWALK_TONES))

    # --- Dense jungle undergrowth below the deck ---
    from generate_parts import _build_understory, _build_broad_leaf_plant, _build_giant_fern

    # Ferns, understory plants growing up from ground
    for _ in range(max(20, (width * depth) // 50)):
        ux = rng.randint(1, width - 2)
        uy = rng.randint(1, depth - 2)
        deck_z_here = _deck_z_at_lx(ux)
        headroom = deck_z_here
        if headroom < 4:
            continue
        max_h = max(3, min(headroom - 2, 25))
        under_m = VoxelModel()
        choice = rng.random()
        if choice < 0.4:
            _build_understory(under_m, 16, 16, max_h, rng, max_x=31, max_y=31, max_z=max_h)
        elif choice < 0.7:
            _build_broad_leaf_plant(under_m, 16, 16, rng, max_x=31, max_y=31, max_z=max_h)
        else:
            _build_giant_fern(under_m, 16, 16, rng, max_x=31, max_y=31, max_z=max_h)
        for (vx, vy, vz), c in under_m._v.items():
            px = ux + vx - 16
            py = uy + vy - 16
            pz = 1 + vz
            if 0 <= px < width and 0 <= py < depth and pz < deck_z_here - 2:
                m.set(px, py, pz, c)

    # Thick ground cover clusters below deck
    floor_pal = (G_DARK, G_DARK, [LEAF_DARK_1, LEAF_DARK_2, LEAF_DARK_3, LEAF_BLUE_2, LEAF_BLUE_3])
    for _ in range(max(40, (width * depth) // 20)):
        cx = rng.randint(1, width - 2)
        cy = rng.randint(1, depth - 2)
        deck_z_here = _deck_z_at_lx(cx)
        if deck_z_here < 3:
            continue
        r_val = rng.uniform(2.0, 5.0)
        _leaf_cluster(m, cx, cy, 1, r_val, floor_pal, rng,
                     max_x=width - 1, max_y=depth - 1, max_z=deck_z_here - 2)

    # Hanging vines from underside of deck — biased toward edges (more sun)
    for _ in range(max(4, (width * depth) // 300)):
        vx = rng.randint(0, width - 1)
        # Bias toward edges: pick a side then place near it
        if rng.random() < 0.8:
            vy = rng.randint(0, 10) if rng.random() < 0.5 else rng.randint(depth - 11, depth - 1)
        else:
            vy = rng.randint(0, depth - 1)
        deck_z_here = _deck_z_at_lx(vx)
        headroom = deck_z_here
        vine_len = rng.randint(max(5, headroom // 3), max(6, headroom * 2 // 3))
        for dz in range(vine_len):
            vz = deck_z_here - 2 - dz
            if vz < 0:
                break
            sway_x = vx + (rng.choice([-1, 0, 1]) if dz > 3 else 0)
            sway_y = vy + (rng.choice([-1, 0, 1]) if dz > 3 else 0)
            if 0 <= sway_x < width and 0 <= sway_y < depth:
                # Thick vine: 2×2 core
                for vdx in range(2):
                    for vdy in range(2):
                        px, py = sway_x + vdx, sway_y + vdy
                        if 0 <= px < width and 0 <= py < depth:
                            m.set(px, py, vz, rng.choice(VINE_TONES))

    # Spiral vines wrapping around ALL stilt posts
    for sx, sy in stilt_positions:
        dz_top = _deck_z_at_lx(sx)
        if dz_top < 6:
            continue

        # Spiral vine — angle_step varies per z for irregular spacing
        base_step = rng.uniform(0.3, 0.8)
        angle = rng.uniform(0, 2 * math.pi)
        for z in range(1, dz_top):
            angle_step = base_step + rng.uniform(-0.2, 0.2)
            vx_off = int(round(2.0 * math.cos(angle)))
            vy_off = int(round(2.0 * math.sin(angle)))
            px, py = sx + vx_off, sy + vy_off
            if 0 <= px < width and 0 <= py < depth:
                m.set(px, py, z, rng.choice(VINE_TONES))
                if rng.random() < 0.08:
                    for ldx in range(-1, 2):
                        for ldy in range(-1, 2):
                            if rng.random() < 0.5:
                                lpx, lpy = px + ldx, py + ldy
                                if 0 <= lpx < width and 0 <= lpy < depth:
                                    m.set(lpx, lpy, z, rng.choice(
                                        [LEAF_DARK_1, LEAF_DARK_2, LEAF_DARK_3]))
            angle += angle_step

        # Moss covering lower portion of post
        moss_top = min(1 + rng.randint(8, 18), dz_top)
        for z in range(1, moss_top):
            for ddx in range(-1, 3):
                for ddy in range(-1, 3):
                    if rng.random() < 0.35:
                        px, py = sx + ddx, sy + ddy
                        if 0 <= px < width and 0 <= py < depth:
                            m.set(px, py, z, rng.choice(MOSS_TONES))

    # Weather the planks (before splitting so both models benefit)
    _weather_planks(m, rng)

    # Split into prism (>= south_z) and base (< south_z)
    prism_model = VoxelModel()
    base_model = VoxelModel()
    for (lx, ly, lz), c in m._v.items():
        pz = lz - south_z_local
        if pz >= 0:
            prism_model.set(lx, ly, pz, c)
        else:
            base_model.set(lx, ly, lz, c)

    # Force prism model size to advance × depth × rise
    prism_model.set_size(width, depth, rise)

    return prism_model, base_model


def build_platform_model(rng, grid):
    """Build the 6x6 tile elevated platform with massive stilts and rickety deck."""
    r_start, r_end = PLATFORM_R_START, PLATFORM_R_END
    c_start, c_end = PLATFORM_C_START, PLATFORM_C_END
    width = (r_end - r_start + 1) * TILE_SIZE   # 128
    depth = (c_end - c_start + 1) * TILE_SIZE    # 128
    m = VoxelModel()

    def _local_to_world(lx, ly):
        wx = (GRID_SIZE - 1 - r_end) * TILE_SIZE + lx
        wy = (GRID_SIZE - 1 - c_end) * TILE_SIZE + ly
        return wx, wy

    # Find min ground elevation across platform area
    min_elev = 999
    for lx in range(0, width, 4):
        for ly in range(0, depth, 4):
            wx, wy = _local_to_world(lx, ly)
            min_elev = min(min_elev, _hill_elevation(wx, wy))
    base_elev = max(0, min_elev - 2)

    # Fill ground terrain
    for lx in range(width):
        for ly in range(depth):
            wx, wy = _local_to_world(lx, ly)
            elev = max(0, _hill_elevation(wx, wy) - base_elev)
            for z in range(elev + 1):
                m.set(lx, ly, z, rng.choice(EARTH_TONES))

    deck_z_local = PLATFORM_DECK_Z - base_elev

    # Flat deck with wide bearer beams (platform = heavier construction)
    beam_positions = _build_flat_deck(m, 0, 0, deck_z_local, width, depth, rng,
                                      beam_width_range=(4, 8), num_beams=6,
                                      plank_widths=(2, 3, 4, 4, 5, 5, 6, 7, 8),
                                      plank_gap_range=(2, 4),
                                      plank_trim_choices=(0, 0, 2, 4, 6, 8, 10))

    # Stilts: higher probability on visible sides
    stilt_spacing = 28
    all_stilt_candidates = []
    for by in beam_positions:
        for sx in range(8, width - 4, stilt_spacing):
            all_stilt_candidates.append((sx, by))
    for sx in [8, width - 10]:
        for sy in [8, depth - 10]:
            all_stilt_candidates.append((sx, sy))
    stilt_positions = []
    for s in all_stilt_candidates:
        sx, sy = s
        prob = 0.8 if (sx < width // 3 or sy < depth // 3) else 0.4
        if rng.random() < prob:
            stilt_positions.append(s)

    # Plus-shaped 4×4 stilt posts (no corner voxels)
    _plus_offsets = [(dx, dy) for dx in range(4) for dy in range(4)
                     if not ((dx in (0, 3)) and (dy in (0, 3)))]

    for sx, sy in stilt_positions:
        wx, wy = _local_to_world(sx, sy)
        gz = max(0, _hill_elevation(wx, wy) - base_elev)
        dz = deck_z_local - 1
        if dz <= gz:
            continue
        for z in range(gz, dz):
            for ddx, ddy in _plus_offsets:
                px, py = sx - 1 + ddx, sy - 1 + ddy
                if 0 <= px < width and 0 <= py < depth:
                    m.set(px, py, z, rng.choice(BOARDWALK_TONES))

    # Missing plank holes
    for _ in range(12):
        hx = rng.randint(10, width - 10)
        hy = rng.randint(10, depth - 10)
        for dx in range(rng.randint(2, 5)):
            for dy in range(rng.randint(1, 3)):
                m.delete(hx + dx, hy + dy, deck_z_local)
                m.delete(hx + dx, hy + dy, deck_z_local - 1)

    # Ouroboros inscription on the deck surface — burned/carved into the wood
    import os
    from PIL import Image as PILImage
    ouroboros_path = os.path.join(os.path.dirname(__file__), 'ouroboros.png')
    if os.path.exists(ouroboros_path):
        ouro_img = PILImage.open(ouroboros_path)
        # Crop to square
        ouro_w, ouro_h = ouro_img.size
        crop_side = min(ouro_w, ouro_h)
        left = (ouro_w - crop_side) // 2
        top = (ouro_h - crop_side) // 2
        ouro_img = ouro_img.crop((left, top, left + crop_side, top + crop_side))
        # Rotate 270 degrees counter-clockwise (= 90 CW)
        ouro_img = ouro_img.rotate(270, expand=False)
        # Resize ~10% larger than before
        ouro_size = min(width, depth) - 6
        ouro_img = ouro_img.resize((ouro_size, ouro_size), PILImage.NEAREST)
        # Center on platform, shifted right 15 voxels (from player facing screen)
        ox_off = (width - ouro_size) // 2
        oy_off = (depth - ouro_size) // 2 + 14 - 15 + 13
        # Dynamic grey-to-brown mapping using palette indices
        # Dark pixels → deep burn, mid pixels → bark, light pixels → warm wood
        brown_ramp = [
            134,   # 0-19: deepest burn — STAIN_3 (18,12,7)
            133,   # 20-39: dark stain — STAIN_2 (25,18,10)
            132,   # 40-59: stain — STAIN_1 (35,24,14)
            31,    # 60-79: dark bark — BARK_DARK_1 (50,30,15)
            45,    # 80-99: root — ROOT_1 (60,38,20)
            36,    # 100-119: bark mid — BARK_MID_3 (70,48,26)
            38,    # 120-149: trunk — TRUNK_2 (85,58,32)
            44,    # 150-179: boardwalk dark — BOARDWALK_5 (95,70,42)
            42,    # 180-209: boardwalk mid — BOARDWALK_3 (100,75,45)
            40,    # 210-255: boardwalk light — BOARDWALK_1 (120,90,55)
        ]
        for px in range(ouro_size):
            for py in range(ouro_size):
                brightness = ouro_img.getpixel((px, py))
                if brightness < 210:
                    lx = ox_off + px
                    ly = oy_off + py
                    if 0 <= lx < width and 0 <= ly < depth:
                        idx = min(len(brown_ramp) - 1, brightness // 20)
                        m.set(lx, ly, deck_z_local, brown_ramp[idx])

    # Rope bindings at stilt-beam junctions
    for sx, sy in stilt_positions:
        if rng.random() < 0.4:
            for ddx in range(-2, 4):
                for ddy in range(-2, 4):
                    if (ddx in (-2, 3)) or (ddy in (-2, 3)):
                        px, py = sx + ddx, sy + ddy
                        if 0 <= px < width and 0 <= py < depth:
                            m.set(px, py, deck_z_local, TORCH_ROPE)

    # --- Dense jungle undergrowth below the platform ---
    from generate_parts import _build_understory, _build_broad_leaf_plant, _build_giant_fern

    for _ in range(max(80, (width * depth) // 50)):
        ux = rng.randint(3, width - 4)
        uy = rng.randint(3, depth - 4)
        wx, wy = _local_to_world(ux, uy)
        gz = max(0, _hill_elevation(wx, wy) - base_elev)
        headroom = deck_z_local - gz
        if headroom < 5:
            continue
        max_h = max(3, min(headroom - 2, 50))
        under_m = VoxelModel()
        choice = rng.random()
        if choice < 0.4:
            _build_understory(under_m, 16, 16, max_h, rng, max_x=31, max_y=31, max_z=max_h)
        elif choice < 0.7:
            _build_broad_leaf_plant(under_m, 16, 16, rng, max_x=31, max_y=31, max_z=max_h)
        else:
            _build_giant_fern(under_m, 16, 16, rng, max_x=31, max_y=31, max_z=max_h)
        for (vx, vy, vz), c in under_m._v.items():
            px = ux + vx - 16
            py = uy + vy - 16
            pz = gz + vz
            if 0 <= px < width and 0 <= py < depth and pz < deck_z_local - 2:
                m.set(px, py, pz, c)

    # Thick ground cover below platform
    floor_pal = (G_DARK, G_DARK, [LEAF_DARK_1, LEAF_DARK_2, LEAF_DARK_3, LEAF_BLUE_2, LEAF_BLUE_3])
    for _ in range(max(120, (width * depth) // 20)):
        cx = rng.randint(2, width - 3)
        cy = rng.randint(2, depth - 3)
        wx, wy = _local_to_world(cx, cy)
        gz = max(0, _hill_elevation(wx, wy) - base_elev)
        if deck_z_local - gz < 3:
            continue
        r_val = rng.uniform(2.5, 5.5)
        _leaf_cluster(m, cx, cy, gz + 1, r_val, floor_pal, rng,
                     max_x=width - 1, max_y=depth - 1, max_z=deck_z_local - 2)

    # Hanging vines from underside of deck
    for _ in range(max(12, (width * depth) // 200)):
        vx = rng.randint(0, width - 1)
        vy = rng.randint(0, depth - 1)
        wx_v, wy_v = _local_to_world(vx, vy)
        gz_v = max(0, _hill_elevation(wx_v, wy_v) - base_elev)
        headroom_v = deck_z_local - gz_v
        vine_len = rng.randint(max(5, headroom_v // 3), max(6, headroom_v * 2 // 3))
        for dz in range(vine_len):
            vz = deck_z_local - 2 - dz
            if vz < 0:
                break
            sway_x = vx + (rng.choice([-1, 0, 1]) if dz > 3 else 0)
            sway_y = vy + (rng.choice([-1, 0, 1]) if dz > 3 else 0)
            if 0 <= sway_x < width and 0 <= sway_y < depth:
                for vdx in range(2):
                    for vdy in range(2):
                        px, py = sway_x + vdx, sway_y + vdy
                        if 0 <= px < width and 0 <= py < depth:
                            m.set(px, py, vz, rng.choice(VINE_TONES))

    # Spiral vines wrapping around ALL stilt posts
    for sx, sy in stilt_positions:
        wx, wy = _local_to_world(sx, sy)
        gz = max(0, _hill_elevation(wx, wy) - base_elev)
        stilt_h = deck_z_local - 1 - gz
        if stilt_h < 6:
            continue

        # Spiral vine — angle_step varies per z for irregular spacing
        base_step = rng.uniform(0.2, 0.6)
        angle = rng.uniform(0, 2 * math.pi)
        for z in range(gz, deck_z_local - 1):
            angle_step = base_step + rng.uniform(-0.15, 0.15)
            vx_off = int(round(2.5 * math.cos(angle)))
            vy_off = int(round(2.5 * math.sin(angle)))
            px, py = sx + vx_off, sy + vy_off
            if 0 <= px < width and 0 <= py < depth:
                m.set(px, py, z, rng.choice(VINE_TONES))
                if rng.random() < 0.1:
                    for ldx in range(-1, 2):
                        for ldy in range(-1, 2):
                            if rng.random() < 0.5:
                                lpx, lpy = px + ldx, py + ldy
                                if 0 <= lpx < width and 0 <= lpy < depth:
                                    m.set(lpx, lpy, z, rng.choice(
                                        [LEAF_DARK_1, LEAF_DARK_2, LEAF_DARK_3]))
            angle += angle_step

        # Moss covering lower portion
        moss_top = min(gz + rng.randint(10, 25), deck_z_local)
        for z in range(gz, moss_top):
            for ddx in range(-1, 3):
                for ddy in range(-1, 3):
                    if rng.random() < 0.35:
                        px, py = sx + ddx, sy + ddy
                        if 0 <= px < width and 0 <= py < depth:
                            m.set(px, py, z, rng.choice(MOSS_TONES))

    # Weather the planks
    _weather_planks(m, rng)

    return m, base_elev


def build_arcade_on_platform(rng):
    """Build the arcade cabinet as a separate structure centered on the platform."""
    m = build_arcade_cabinet(seed=rng.randint(0, 2**31))
    # Remove bounding box anchor voxels
    m.delete(0, 0, 0)
    m.delete(47, 47, 0)
    # Shift to (0,0) tight fit
    coords = list(m._v.keys())
    min_x = min(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    m.shift(-min_x, -min_y, 0)
    return m, PLATFORM_DECK_Z + 1


# ============================================================
# Scene graph writer (multi-model .vox)
# ============================================================

def write_structured_vox(filepath, all_model_data, structures, palette, materials):
    """Write multi-model .vox with nested scene graph.

    all_model_data: concatenated SIZE+XYZI bytes for all models
    structures: list of structure dicts, each with:
        'name': structure name
        'models': list of (model_index, (tx, ty, tz), (sx, sy, sz))
    """
    next_id = [2]

    def alloc_id():
        nid = next_id[0]
        next_id[0] += 1
        return nid

    scene_children_ids = []
    scene_chunks = b""

    for structure in structures:
        models = structure['models']

        if len(models) == 1:
            model_idx, t, s = models[0]
            trn_id = alloc_id()
            shp_id = alloc_id()
            scene_children_ids.append(trn_id)

            trn = struct.pack("<I", trn_id)
            trn += _write_dict({'_name': structure.get('name', '')} if 'name' in structure else {})
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
            parent_trn_id = alloc_id()
            grp_id = alloc_id()
            scene_children_ids.append(parent_trn_id)

            children_for_parent = [(s, t) for _, t, s in models]
            parent_t = compute_parent_translation(children_for_parent)

            trn = struct.pack("<I", parent_trn_id)
            trn += _write_dict({'_name': structure.get('name', '')} if 'name' in structure else {})
            trn += struct.pack("<I", grp_id)
            trn += struct.pack("<i", -1)
            trn += struct.pack("<i", -1)
            trn += struct.pack("<I", 1)
            trn += _write_dict({"_t": f"{parent_t[0]} {parent_t[1]} {parent_t[2]}"})
            scene_chunks += write_chunk(b"nTRN", trn)

            child_trn_ids = []
            for _ in models:
                child_trn_ids.append(alloc_id())
                alloc_id()

            grp = struct.pack("<I", grp_id)
            grp += _write_dict({})
            grp += struct.pack("<I", len(models))
            for cid in child_trn_ids:
                grp += struct.pack("<I", cid)
            scene_chunks += write_chunk(b"nGRP", grp)

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

    # MATL chunks
    _MATL_DEFAULT = {"_rough": "0.1", "_ior": "0.3", "_ri": "1.3", "_d": "0.05"}
    matl_chunks = b""
    for mat_id in range(1, 257):
        props = materials.get(mat_id, _MATL_DEFAULT)
        matl_content = struct.pack("<I", mat_id) + _write_dict(props)
        matl_chunks += write_chunk(b"MATL", matl_content)

    children = all_model_data + scene_graph + rgba_chunk + matl_chunks
    main_chunk = write_chunk(b"MAIN", b"", children)
    header = b"VOX " + struct.pack("<I", 200)

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(header + main_chunk)

    print(f"  Written: {filepath}")


# ============================================================
# Scene assembly pipeline
# ============================================================

def generate_scene(output_dir):
    rng = random.Random(42)
    palette = make_palette()
    materials = get_materials()

    print("Building grid...")
    grid, boardwalk_tiles = build_grid()

    # Centering
    shift_x = WORLD_SIZE // 2
    shift_y = WORLD_SIZE // 2

    # Collect models and structures
    all_model_bytes = b""
    model_index = 0
    structures = []

    def add_model(model_obj, name, mr_end, mc_end):
        """Serialize a VoxelModel, compute translation, add as single-model structure."""
        nonlocal all_model_bytes, model_index
        result = _voxelmodel_to_serialized(model_obj)
        if result is None:
            return
        all_model_bytes += result['model_data']
        sx, sy, sz = result['size']
        wx, wy = model_world_origin(mr_end, mc_end)
        tx, ty, tz = model_translation(wx, wy, sx, sy, sz, shift_x, shift_y)
        structures.append({
            'name': name,
            'models': [(model_index, (tx, ty, tz), (sx, sy, sz))],
        })
        print(f"    Structure '{name}': model {model_index}, size {sx}x{sy}x{sz}, "
              f"voxels={result['num_voxels']}")
        model_index += 1

    def add_multimodel_structure(name, model_list):
        """Add a structure with multiple models, auto-splitting vertically if >256 z.
        model_list: list of tuples:
          (VoxelModel, mr_end, mc_end)
          (VoxelModel, mr_end, mc_end, z_offset)
          (VoxelModel, mr_end, mc_end, z_offset, (dx, dy))  — voxel offset from tile origin
        """
        nonlocal all_model_bytes, model_index
        model_entries = []
        for entry in model_list:
            if len(entry) == 5:
                model_obj, m_mr_end, m_mc_end, z_off, (dx, dy) = entry
            elif len(entry) == 4:
                model_obj, m_mr_end, m_mc_end, z_off = entry
                dx, dy = 0, 0
            else:
                model_obj, m_mr_end, m_mc_end = entry
                z_off, dx, dy = 0, 0, 0
            # Split into vertical slices for >256 z
            slices = _voxelmodel_to_vertical_slices(model_obj)
            for result, slice_z_base in slices:
                all_model_bytes += result['model_data']
                sx, sy, sz = result['size']
                wx, wy = model_world_origin(m_mr_end, m_mc_end, dx, dy)
                tx, ty, tz = model_translation(wx, wy, sx, sy, sz, shift_x, shift_y)
                tz += z_off + slice_z_base  # hill elevation + vertical slice offset
                model_entries.append((model_index, (tx, ty, tz), (sx, sy, sz)))
                model_index += 1
        if model_entries:
            structures.append({'name': name, 'models': model_entries})
            print(f"    Structure '{name}': {len(model_entries)} models")

    # ---- 1. Forest structures (per-ring, direct write) ----
    print("\nBuilding forest...")
    forest_tiles = set()
    for (r, c), tile_type in grid.items():
        if tile_type == 'forest':
            forest_tiles.add((r, c))

    # Group forest tiles by ring distance
    # Ring 14 stays separate (internal limit=365). Rings 15+ merge (internal limit=384).
    max_ring = 0
    ring_tiles = {}
    for (r, c) in forest_tiles:
        d = min(r, c, GRID_SIZE - 1 - r, GRID_SIZE - 1 - c)
        if d > len(_HEIGHT_TABLE) - 1:
            d = len(_HEIGHT_TABLE)  # all rings past the table merge
        ring_tiles.setdefault(d, set()).add((r, c))
        max_ring = max(max_ring, d)

    # Merge rings whose content fits within the outer ring's Pictoria height limit.
    # Hardcoded from measured max_z values:
    #   Ring 0: alone (max_z=0, limit=1)
    #   Rings 1-6: merged (max_z=35, limit=52)
    #   Rings 7-11: merged (max_z=203, limit=209)
    #   Rings 12-13: merged (max_z=294, limit=339)
    #   Rings 14-15+: merged (max_z=383, limit=384)
    _RING_GROUPS = [
        ([0], 1),
        ([1, 2, 3, 4, 5, 6], 52),
        ([7, 8, 9, 10, 11], 209),
        ([12, 13], 339),
        ([14, 15], 384),
    ]

    # Pre-allocate models per merged ring group.
    tile_to_model = {}
    model_infos = []
    struct_idx = 0
    # Track which group each ring belongs to (for serialization)
    ring_to_group = {}
    group_infos = []  # list of (group_rings, height_limit, group_tiles)

    for group_rings, group_limit in _RING_GROUPS:
        group_tiles = set()
        for d in group_rings:
            group_tiles |= (ring_tiles.get(d, set()) & forest_tiles)
            ring_to_group[d] = len(group_infos)
        # Also include any rings > 15 in the last group
        if 15 in group_rings:
            for d in range(16, max_ring + 1):
                group_tiles |= (ring_tiles.get(d, set()) & forest_tiles)
                ring_to_group[d] = len(group_infos)
        if not group_tiles:
            group_infos.append((group_rings, group_limit, set()))
            continue
        group_infos.append((group_rings, group_limit, group_tiles))

        # Decompose merged tiles into structures (max 16 tiles) → models (max 8 tiles)
        rects = decompose_into_rectangles(group_tiles)
        for r1, c1, r2, c2 in rects:
            for struct_regions in split_into_structures(r1, c1, r2, c2, group_tiles):
                struct_models = []
                for mr, mc, mr_end, mc_end in struct_regions:
                    width = (mr_end - mr + 1) * TILE_SIZE
                    depth = (mc_end - mc + 1) * TILE_SIZE
                    base_wx = (GRID_SIZE - 1 - mr_end) * TILE_SIZE
                    base_wy = (GRID_SIZE - 1 - mc_end) * TILE_SIZE
                    base_wz = 0
                    m = VoxelModel()
                    info = {
                        'model': m, 'mr': mr, 'mc': mc, 'mr_end': mr_end, 'mc_end': mc_end,
                        'base_wx': base_wx, 'base_wy': base_wy, 'base_wz': base_wz,
                        'height_limit': group_limit, 'ring': group_rings[0],
                        'width': width, 'depth': depth,
                    }
                    for ri in range(mr, mr_end + 1):
                        for ci in range(mc, mc_end + 1):
                            if (ri, ci) in group_tiles:
                                tile_to_model[(ri, ci)] = info
                    struct_models.append(info)
                model_infos.extend(struct_models)

    # Buffer for tree voxels that would extend into platform tile space
    platform_tile_set = set()
    for r in range(PLATFORM_R_START, PLATFORM_R_END + 1):
        for c in range(PLATFORM_C_START, PLATFORM_C_END + 1):
            platform_tile_set.add((r, c))
    platform_overgrowth = []  # list of (wx, wy, wz, color)

    def _write_voxel(wx, wy, wz, color):
        """Write a voxel at world coords into the correct pre-allocated model."""
        r = GRID_SIZE - 1 - wx // TILE_SIZE
        c = GRID_SIZE - 1 - wy // TILE_SIZE
        info = tile_to_model.get((r, c))
        if info is None:
            # Stash if it falls in platform tile space
            if (r, c) in platform_tile_set:
                platform_overgrowth.append((wx, wy, wz, color))
            return False
        if wz >= info['height_limit']:
            return False
        lx = wx - info['base_wx']
        ly = wy - info['base_wy']
        lz = wz - info['base_wz']
        if lx < 0 or ly < 0 or lz < 0:
            return False
        info['model'].set(lx, ly, lz, color)
        return True

    def _wv_edge_fade(wx, wy):
        dist = min(wx, wy, WORLD_SIZE - 1 - wx, WORLD_SIZE - 1 - wy)
        return min(1.0, dist / (TILE_SIZE * 3))

    def _wv_ring(wx, wy):
        r = GRID_SIZE - 1 - wx // TILE_SIZE
        c = GRID_SIZE - 1 - wy // TILE_SIZE
        return min(r, c, GRID_SIZE - 1 - r, GRID_SIZE - 1 - c)

    all_tree_info = []  # collected per-tree data for torch placement

    # Pre-distribute trees and understory via Poisson disk sampling
    import time as _time

    def _poisson_disk(rng, min_dist, bounds_min, bounds_max, max_attempts=30):
        """Generate Poisson disk distributed points within [bounds_min, bounds_max]."""
        cell_size = min_dist / 1.414
        grid_w = int((bounds_max - bounds_min) / cell_size) + 1
        grid = {}
        points = []
        active = []

        def _grid_key(wx, wy):
            return (int((wx - bounds_min) / cell_size),
                    int((wy - bounds_min) / cell_size))

        def _check(wx, wy):
            gx, gy = _grid_key(wx, wy)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    key = (gx + dx, gy + dy)
                    if key in grid:
                        ex, ey = points[grid[key]]
                        if (wx - ex) ** 2 + (wy - ey) ** 2 < min_dist * min_dist:
                            return False
            return True

        # Seed point
        sx = rng.randint(bounds_min, bounds_max)
        sy = rng.randint(bounds_min, bounds_max)
        points.append((sx, sy))
        grid[_grid_key(sx, sy)] = 0
        active.append(0)

        while active:
            idx = rng.randint(0, len(active) - 1)
            px, py = points[active[idx]]
            found = False
            for _ in range(max_attempts):
                angle = rng.uniform(0, 6.283)
                dist = rng.uniform(min_dist, min_dist * 2)
                nx = int(px + dist * math.cos(angle))
                ny = int(py + dist * math.sin(angle))
                if bounds_min <= nx <= bounds_max and bounds_min <= ny <= bounds_max:
                    if _check(nx, ny):
                        key = _grid_key(nx, ny)
                        if key not in grid:
                            grid[key] = len(points)
                            points.append((nx, ny))
                            active.append(len(points) - 1)
                            found = True
                            break
            if not found:
                active.pop(idx)
        return points

    print("  Pre-distributing trees...")
    _t_pd = _time.time()
    # Only within forest area (exclude outer 1 tile for edge)
    forest_min = 0
    forest_max = WORLD_SIZE - 1
    tree_points = _poisson_disk(random.Random(rng.randint(0, 2**31)),
                                min_dist=40, bounds_min=forest_min, bounds_max=forest_max)
    # Filter to forest tiles only, exclude ring 15+ (handled by INNER_TREES)
    tree_positions = []
    for (wx, wy) in tree_points:
        r = GRID_SIZE - 1 - wx // TILE_SIZE
        c = GRID_SIZE - 1 - wy // TILE_SIZE
        if (r, c) in forest_tiles:
            d = min(r, c, GRID_SIZE - 1 - r, GRID_SIZE - 1 - c)
            d = min(d, len(_HEIGHT_TABLE))
            if d < len(_HEIGHT_TABLE):  # skip ring 15+
                tree_positions.append((wx, wy, d))

    print(f"  Distributed {len(tree_positions)} trees in {_time.time()-_t_pd:.1f}s")

    # Pre-distribute understory
    under_points = _poisson_disk(random.Random(rng.randint(0, 2**31)),
                                 min_dist=14, bounds_min=forest_min, bounds_max=forest_max)
    under_positions = []
    for (wx, wy) in under_points:
        r = GRID_SIZE - 1 - wx // TILE_SIZE
        c = GRID_SIZE - 1 - wy // TILE_SIZE
        if (r, c) in forest_tiles:
            d = min(r, c, GRID_SIZE - 1 - r, GRID_SIZE - 1 - c)
            d = min(d, len(_HEIGHT_TABLE))
            under_positions.append((wx, wy, d))

    print(f"  Distributed {len(under_positions)} understory in {_time.time()-_t_pd:.1f}s")

    # Pre-distribute stones
    stone_points = _poisson_disk(random.Random(rng.randint(0, 2**31)),
                                 min_dist=60, bounds_min=forest_min, bounds_max=forest_max)
    stone_positions = []
    for (wx, wy) in stone_points:
        r = GRID_SIZE - 1 - wx // TILE_SIZE
        c = GRID_SIZE - 1 - wy // TILE_SIZE
        if (r, c) in forest_tiles:
            d = min(r, c, GRID_SIZE - 1 - r, GRID_SIZE - 1 - c)
            d = min(d, len(_HEIGHT_TABLE))
            stone_positions.append((wx, wy, d))
    print(f"  Distributed {len(stone_positions)} stones in {_time.time()-_t_pd:.1f}s")

    # Pre-distribute ground cover
    cover_points = _poisson_disk(random.Random(rng.randint(0, 2**31)),
                                 min_dist=6, bounds_min=forest_min, bounds_max=forest_max)
    cover_positions = []
    for (wx, wy) in cover_points:
        r = GRID_SIZE - 1 - wx // TILE_SIZE
        c = GRID_SIZE - 1 - wy // TILE_SIZE
        if (r, c) in forest_tiles:
            d = min(r, c, GRID_SIZE - 1 - r, GRID_SIZE - 1 - c)
            d = min(d, len(_HEIGHT_TABLE))
            cover_positions.append((wx, wy, d))
    print(f"  Distributed {len(cover_positions)} ground cover in {_time.time()-_t_pd:.1f}s")

    # Pre-distribute ferns/broad-leaf plants
    fern_points = _poisson_disk(random.Random(rng.randint(0, 2**31)),
                                min_dist=12, bounds_min=forest_min, bounds_max=forest_max)
    fern_positions = []
    for (wx, wy) in fern_points:
        r = GRID_SIZE - 1 - wx // TILE_SIZE
        c = GRID_SIZE - 1 - wy // TILE_SIZE
        if (r, c) in forest_tiles:
            d = min(r, c, GRID_SIZE - 1 - r, GRID_SIZE - 1 - c)
            d = min(d, len(_HEIGHT_TABLE))
            fern_positions.append((wx, wy, d))
    print(f"  Distributed {len(fern_positions)} ferns in {_time.time()-_t_pd:.1f}s")

    # Pre-distribute large understory ferns (cool-toned, different layer)
    lfern_points = _poisson_disk(random.Random(rng.randint(0, 2**31)),
                                 min_dist=20, bounds_min=forest_min, bounds_max=forest_max)
    lfern_positions = []
    for (wx, wy) in lfern_points:
        r = GRID_SIZE - 1 - wx // TILE_SIZE
        c = GRID_SIZE - 1 - wy // TILE_SIZE
        if (r, c) in forest_tiles:
            d = min(r, c, GRID_SIZE - 1 - r, GRID_SIZE - 1 - c)
            d = min(d, len(_HEIGHT_TABLE))
            lfern_positions.append((wx, wy, d))
    print(f"  Distributed {len(lfern_positions)} large ferns in {_time.time()-_t_pd:.1f}s")

    # Group all by ring
    tree_by_ring = {}
    for (wx, wy, d) in tree_positions:
        tree_by_ring.setdefault(d, []).append((wx, wy))
    under_by_ring = {}
    for (wx, wy, d) in under_positions:
        under_by_ring.setdefault(d, []).append((wx, wy))
    stone_by_ring = {}
    for (wx, wy, d) in stone_positions:
        stone_by_ring.setdefault(d, []).append((wx, wy))
    cover_by_ring = {}
    for (wx, wy, d) in cover_positions:
        cover_by_ring.setdefault(d, []).append((wx, wy))
    fern_by_ring = {}
    for (wx, wy, d) in fern_positions:
        fern_by_ring.setdefault(d, []).append((wx, wy))
    lfern_by_ring = {}
    for (wx, wy, d) in lfern_positions:
        lfern_by_ring.setdefault(d, []).append((wx, wy))
    for d in range(max_ring + 1):
        tiles = ring_tiles.get(d, set()) & forest_tiles
        if not tiles:
            continue
        height_limit = _HEIGHT_TABLE[min(d, len(_HEIGHT_TABLE) - 1)]
        # Internal height limit = outer ring's Pictoria limit (safe to bleed outward)
        internal_limit = _HEIGHT_TABLE[max(0, d - 1)]
        # Vegetation zone (controls what spawns, independent of height limit)
        zone_max = min(veg_zone_for_ring(d), internal_limit)
        # Outward XY bound = outer edge of ring d-1
        outer_wx_min = max(0, d - 1) * TILE_SIZE
        outer_wx_max = (GRID_SIZE - max(0, d - 1)) * TILE_SIZE - 1
        outer_wy_min = outer_wx_min
        outer_wy_max = outer_wx_max

        ring_rng = random.Random(rng.randint(0, 2**31))
        ring_canopy_world = []  # pooled canopy positions (world coords)
        _t0 = _time.time()
        _ground_total = 0.0
        _tree_total = 0.0
        _tree_parts = {'trunk': 0.0, 'moss': 0.0, 'epi': 0.0, 'butt': 0.0, 'canopy': 0.0, 'write': 0.0}

        for (r, c) in sorted(tiles):
            tile_wx, tile_wy = tile_world_pos(r, c)
            tile_rng = random.Random(ring_rng.randint(0, 2**31))

            # Get this tile's model for direct writes (no _write_voxel overhead)
            tinfo = tile_to_model.get((r, c))
            if tinfo is None:
                continue
            tm = tinfo['model']
            tm_bwx = tinfo['base_wx']
            tm_bwy = tinfo['base_wy']
            tm_bwz = tinfo['base_wz']

            # ---- Ground fill (direct write) ----
            _tg = _time.time()
            for lx in range(TILE_SIZE):
                for ly in range(TILE_SIZE):
                    wx, wy = tile_wx + lx, tile_wy + ly
                    elev = _hill_elevation(wx, wy)
                    mlx = wx - tm_bwx
                    mly = wy - tm_bwy
                    for z in range(elev + 1):
                        r_val = tile_rng.random()
                        mlz = z - tm_bwz
                        if mlz < 0:
                            continue
                        if z == elev:
                            if r_val < 0.35:
                                tm.set(mlx, mly, mlz, tile_rng.choice(G_DARK))
                            else:
                                tm.set(mlx, mly, mlz, tile_rng.choice(EARTH_TONES))
                        else:
                            tm.set(mlx, mly, mlz, tile_rng.choice(EARTH_TONES))

            _ground_total += _time.time() - _tg

        # ---- Trees from pre-distributed positions ----
        _tt = _time.time()
        center = 128
        tree_max_z = internal_limit - 1

        # Height ranges
        if zone_max >= 235:
            h_lo = max(15, zone_max // 4)
            h_hi = zone_max * 2 // 3
        else:
            h_lo = max(15, zone_max * 2 // 3)
            h_hi = zone_max

        ring_tree_rng = random.Random(ring_rng.randint(0, 2**31))
        # Ring 15+: use locked INNER_TREES instead of Poisson disk
        if d >= len(_HEIGHT_TABLE):
            tree_list = [(tx, ty, seed) for (tx, ty, seed) in INNER_TREES]
        else:
            tree_list = [(tx, ty, ring_tree_rng.randint(0, 2**31))
                         for (tx, ty) in tree_by_ring.get(d, [])]
        for (tx, ty, _tree_seed) in tree_list:
            tile_rng = random.Random(_tree_seed)

            if zone_max < 52:
                continue

            # Select tree tier
            is_hero = False
            if zone_max >= 235:
                roll = tile_rng.random()
                if zone_max >= 384 and roll < 0.15:  # hero — always full height
                    is_hero = True
                    h_range = (zone_max - 140, zone_max - 120)  # headroom for canopy dome
                    w_range = (5, 7)
                    r_range = (14, 20)
                    n_branches = tile_rng.randint(8, 12)
                    n_buttresses = tile_rng.randint(5, 6)
                elif roll < 0.35:  # regular emergent
                    h_range = (h_lo, h_hi)
                    w_range = (4, 6)
                    r_range = (9, 14)
                    n_branches = tile_rng.randint(4, 6)
                    n_buttresses = tile_rng.randint(4, 6)
                else:  # varied canopy
                    h_range = (h_lo, h_hi)
                    w_range = (2, 4)
                    r_range = (7, 10)
                    n_branches = tile_rng.randint(2, 4)
                    n_buttresses = tile_rng.randint(2, 3)
            else:  # >= 52
                h_range = (h_lo, h_hi)
                w_range = (2, 4)
                r_range = (8, 11)
                n_branches = tile_rng.randint(2, 4)
                n_buttresses = tile_rng.randint(2, 3)

            gz = _hill_elevation(tx, ty)
            available_z = tree_max_z - gz
            if available_z < 5:
                continue

            h_max = min(h_range[1], available_z)
            if h_max < h_range[0]:
                h = h_max
            else:
                h = tile_rng.randint(h_range[0], h_max)
            if h < 5:
                continue
            w = tile_rng.randint(w_range[0], w_range[1])

            bark = tile_rng.choice(BARK_PALETTE_OPTIONS)
            canopy_pal = tile_rng.choice(CANOPY_PALETTES)
            has_moss = tile_rng.random() < 0.35
            is_flowering = tile_rng.random() < 0.12
            flower_color = (tile_rng.choices(
                [FLOWER_RED_1, FLOWER_RED_2, FLOWER_WHITE],
                weights=[3, 3, 2], k=1)[0]) if is_flowering else None

            off_x = tx - center
            off_y = ty - center
            t_max_x = 255
            t_max_y = 255

            tree_m = VoxelModel()
            trunk_m = VoxelModel()
            path = _grow_trunk(trunk_m, center, center, h, w, tile_rng,
                              tones=bark, max_x=t_max_x, max_y=t_max_y)
            shifted_path = []
            for (vx, vy, vz), col in trunk_m._v.items():
                tree_m.set(vx, vy, vz + gz, col)
            for (px, py, pz) in path:
                shifted_path.append((px, py, pz + gz))

            if has_moss:
                _moss_on_trunk(tree_m, shifted_path, w, tile_rng,
                              max_x=t_max_x, max_y=t_max_y)
            if tile_rng.random() < 0.4:
                _add_epiphytes(tree_m, shifted_path, w, tile_rng,
                              max_x=t_max_x, max_y=t_max_y,
                              max_z=tree_max_z)

            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]
            tile_rng.shuffle(dirs)
            butt_h = max(5, h // 8)
            for bi in range(min(n_buttresses, len(dirs))):
                ddx, ddy = dirs[bi]
                _grow_buttress(tree_m, center, center, gz, ddx * 0.7, ddy * 0.7,
                              tile_rng, max_x=t_max_x, max_y=t_max_y,
                              height=butt_h)

            tree_canopy = []
            if len(shifted_path) > 10:
                trunk_height = len(shifted_path)
                tree_canopy = _build_canopy_dome(tree_m, shifted_path, trunk_height,
                                                 bark, canopy_pal, r_range, tile_rng,
                                                 t_max_x, t_max_y, tree_max_z)
                if flower_color and tree_canopy:
                    num_flowers = max(5, len(tree_canopy) // 8)
                    for _ in range(num_flowers):
                        pos = tile_rng.choice(tree_canopy)
                        fx = pos[0] + tile_rng.randint(-1, 1)
                        fy = pos[1] + tile_rng.randint(-1, 1)
                        fz = pos[2] + tile_rng.randint(-1, 1)
                        if 0 <= fz <= tree_max_z:
                            tree_m.set(fx, fy, fz, flower_color)

            # Vines
            if tree_canopy:
                vine_count = max(8, min(25, 8 + len(tree_canopy) // 300))
                _grow_vines(tree_m, tree_canopy, tile_rng, count=vine_count,
                           max_x=t_max_x, max_y=t_max_y, max_z=tree_max_z)

            # Track tree info for torch placement
            canopy_world = [(off_x + cx, off_y + cy, cz) for (cx, cy, cz) in tree_canopy]
            if canopy_world:
                all_tree_info.append({
                    'wx': tx, 'wy': ty, 'h': h, 'gz': gz,
                    'is_hero': is_hero, 'is_inner': d >= len(_HEIGHT_TABLE),
                    'ring': d,
                    'canopy': canopy_world,
                })

            # Write tree voxels, filtering outward in world coords
            for (vx, vy, vz), col in tree_m._v.items():
                wwx = off_x + vx
                wwy = off_y + vy
                if outer_wx_min <= wwx <= outer_wx_max and outer_wy_min <= wwy <= outer_wy_max:
                    _write_voxel(wwx, wwy, vz, col)

        _tree_total = _time.time() - _tt

        # ---- Understory from pre-distributed positions ----
        ring_under_rng = random.Random(ring_rng.randint(0, 2**31))
        # Understory fades in from ring 7-9
        if d <= 5:
            under_fade = 0.0
        elif d == 6:
            under_fade = 0.5   # 50% of ring 7
        elif d == 7:
            under_fade = 1.0   # full density, short
        elif d == 8:
            under_fade = 1.0
        else:
            under_fade = 1.0

        for (ux, uy) in (under_by_ring.get(d, []) if under_fade > 0 else []):
            fade = _wv_edge_fade(ux, uy)
            if fade < 0.34:
                continue
            u_rng = random.Random(ring_under_rng.randint(0, 2**31))
            # Density fade: skip some in outer rings
            if u_rng.random() > under_fade:
                continue
            gz = _hill_elevation(ux, uy)
            avail = internal_limit - gz - 1
            if avail < 3:
                continue
            max_h = max(3, min(int(avail * 0.3 * under_fade), zone_max))
            under_m = VoxelModel()
            _build_understory(under_m, TILE_SIZE // 2, TILE_SIZE // 2, max_h, u_rng,
                             max_x=TILE_SIZE - 1, max_y=TILE_SIZE - 1, max_z=avail)
            uoff_x = ux - TILE_SIZE // 2
            uoff_y = uy - TILE_SIZE // 2
            top_wz = 0
            for (vx, vy, vz), col in under_m._v.items():
                wz = vz + gz
                wwx = uoff_x + vx
                wwy = uoff_y + vy
                if wz < internal_limit and outer_wx_min <= wwx <= outer_wx_max and outer_wy_min <= wwy <= outer_wy_max:
                    _write_voxel(wwx, wwy, wz, col)
                    if wz > top_wz:
                        top_wz = wz

            # Add understory tops to canopy pool only in outer rings (7-8)
            if top_wz > gz + 10 and d <= 8:
                ring_canopy_world.append((ux, uy, top_wz))

        # ---- Stones from pre-distributed positions ----
        ring_stone_rng = random.Random(ring_rng.randint(0, 2**31))
        for (sx, sy) in (stone_by_ring.get(d, []) if zone_max > 0 else []):
            fade = _wv_edge_fade(sx, sy)
            s_rng = random.Random(ring_stone_rng.randint(0, 2**31))
            gz = _hill_elevation(sx, sy)
            stone_r = s_rng.randint(1, 8)
            stone_h = s_rng.randint(1, 6)
            if d == 0:
                # Ring 0: flush with ground, can bleed into ring 1 but not outside property
                stone_h = 1
                if (sx - stone_r < 0 or sx + stone_r >= WORLD_SIZE or
                    sy - stone_r < 0 or sy + stone_r >= WORLD_SIZE):
                    continue
            if gz + stone_h >= height_limit:
                stone_h = max(1, height_limit - gz - 1)
            for dx in range(-stone_r, stone_r + 1):
                for dy in range(-stone_r, stone_r + 1):
                    if dx * dx + dy * dy <= stone_r * stone_r:
                        pwx, pwy = sx + dx, sy + dy
                        if not (outer_wx_min <= pwx <= outer_wx_max and outer_wy_min <= pwy <= outer_wy_max):
                            continue
                        # Flatten ring 1 stones that extend into ring 0
                        voxel_ring = _wv_ring(pwx, pwy)
                        if voxel_ring == 0 and d == 1:
                            local_gz = _hill_elevation(pwx, pwy)
                            col = s_rng.choice([STONE_LIGHT, STONE_MID, STONE_DARK])
                            _write_voxel(pwx, pwy, local_gz, col)
                            continue
                        for dz in range(stone_h):
                            pz = gz + dz
                            if pz < height_limit:
                                if dz == stone_h - 1 and s_rng.random() < 0.6:
                                    _write_voxel(pwx, pwy, pz, s_rng.choice(MOSS_TONES))
                                else:
                                    _write_voxel(pwx, pwy, pz,
                                                s_rng.choice([STONE_LIGHT, STONE_MID, STONE_DARK]))

        # ---- Scattered twigs on ground (rings 0-5) ----
        if d <= 5:
            ring_twig_rng = random.Random(ring_rng.randint(0, 2**31))
            twig_tones = ROOT_TONES + TRUNK_TONES[:2]
            # ~4 twigs per tile, fewer in outer rings
            twigs_per_tile = {0: 3, 1: 4, 2: 4, 3: 3, 4: 2, 5: 1}[d]
            for (r_t, c_t) in sorted(tiles):
                tw_wx, tw_wy = tile_world_pos(r_t, c_t)
                for _ in range(twigs_per_tile):
                    t_rng = random.Random(ring_twig_rng.randint(0, 2**31))
                    cx = tw_wx + t_rng.randint(2, TILE_SIZE - 3)
                    cy = tw_wy + t_rng.randint(2, TILE_SIZE - 3)
                    angle = t_rng.uniform(0, math.pi)
                    length = t_rng.randint(3, 8)
                    thick = t_rng.choice([1, 1, 1, 2])  # mostly thin
                    col = t_rng.choice(twig_tones)
                    dx = math.cos(angle)
                    dy = math.sin(angle)
                    for step in range(-length // 2, length // 2 + 1):
                        for w in range(thick):
                            tx = int(round(cx + dx * step - dy * w))
                            ty = int(round(cy + dy * step + dx * w))
                            if not (0 <= tx < WORLD_SIZE and 0 <= ty < WORLD_SIZE):
                                continue
                            if not (outer_wx_min <= tx <= outer_wx_max and outer_wy_min <= ty <= outer_wy_max):
                                continue
                            pz = _hill_elevation(tx, ty)
                            _write_voxel(tx, ty, pz, col)

        # ---- Ground cover from pre-distributed positions ----
        ring_cover_rng = random.Random(ring_rng.randint(0, 2**31))
        floor_pal = [G_DARK[0], G_DARK[1]] + [LEAF_DARK_1, LEAF_DARK_2, LEAF_DARK_3,
                                                LEAF_BLUE_2, LEAF_BLUE_3]
        for (cx, cy) in (cover_by_ring.get(d, []) if zone_max > 0 and d >= 1 else []):
            fade = max(_wv_edge_fade(cx, cy), 1.0 if d <= 2 else 0.0)
            c_rng = random.Random(ring_cover_rng.randint(0, 2**31))
            # Cover density fade for outer rings
            if d == 1 and c_rng.random() > 0.33:
                continue
            if d == 2 and c_rng.random() > 0.66:
                continue
            gz = _hill_elevation(cx, cy)
            if d == 0:
                cover_max_z = gz  # flatten to ground level for ring 0
            elif fade < 0.34:
                cover_max_z = gz
            else:
                cover_max_z = min(gz + 8, height_limit - 1)
            r_val = c_rng.uniform(2.0, 4.0)
            for dx in range(-int(r_val), int(r_val) + 1):
                for dy in range(-int(r_val), int(r_val) + 1):
                    if dx * dx + dy * dy <= r_val * r_val:
                        dz = c_rng.randint(0, max(0, int(r_val) - abs(dx) - abs(dy)))
                        # For ring 0: flatten entire cluster to ground level
                        pz = gz if d == 0 else gz + dz
                        if pz <= cover_max_z:
                            pwx, pwy = cx + dx, cy + dy
                            if outer_wx_min <= pwx <= outer_wx_max and outer_wy_min <= pwy <= outer_wy_max:
                                _write_voxel(pwx, pwy, pz, c_rng.choice(floor_pal))

        # ---- Ferns/broad-leaf plants from pre-distributed positions ----
        from generate_parts import _build_broad_leaf_plant, _build_giant_fern
        ring_fern_rng = random.Random(ring_rng.randint(0, 2**31))
        # Fern density fade for outer rings
        if d <= 1:
            fern_prob = 0.0
        elif d == 2:
            fern_prob = 0.25
        elif d == 3:
            fern_prob = 0.50
        elif d == 4:
            fern_prob = 0.75
        else:
            fern_prob = 1.0
        fern_wx_min = outer_wx_min
        fern_wx_max = outer_wx_max
        fern_wy_min = outer_wy_min
        fern_wy_max = outer_wy_max
        for (bx, by) in (fern_by_ring.get(d, []) if zone_max > 0 and fern_prob > 0 else []):
            if ring_fern_rng.random() > fern_prob:
                continue
            fade = _wv_edge_fade(bx, by)
            if fade < 0.34:
                continue
            f_rng = random.Random(ring_fern_rng.randint(0, 2**31))
            gz = _hill_elevation(bx, by)
            plant_max_z = internal_limit - gz - 1
            if plant_max_z < 3:
                continue
            plant_m = VoxelModel()
            if f_rng.random() < 0.5:
                _build_broad_leaf_plant(plant_m, TILE_SIZE // 2, TILE_SIZE // 2,
                                       f_rng, max_x=TILE_SIZE - 1,
                                       max_y=TILE_SIZE - 1, max_z=plant_max_z)
            else:
                _build_giant_fern(plant_m, TILE_SIZE // 2, TILE_SIZE // 2,
                                 f_rng, max_x=TILE_SIZE - 1,
                                 max_y=TILE_SIZE - 1, max_z=plant_max_z)
            poff_x = bx - TILE_SIZE // 2
            poff_y = by - TILE_SIZE // 2
            for (vx, vy, vz), col in plant_m._v.items():
                wz = vz + gz
                wwx = poff_x + vx
                wwy = poff_y + vy
                if wz < internal_limit and fern_wx_min <= wwx <= fern_wx_max and fern_wy_min <= wwy <= fern_wy_max:
                    _write_voxel(wwx, wwy, wz, col)

        # ---- Large understory ferns (olive/lime, contrasting) ----
        from generate_parts import _build_large_fern
        ring_lfern_rng = random.Random(ring_rng.randint(0, 2**31))
        for (bx, by) in (lfern_by_ring.get(d, []) if zone_max > 0 and fern_prob > 0 else []):
            if ring_lfern_rng.random() > fern_prob:
                continue
            fade = _wv_edge_fade(bx, by)
            if fade < 0.34:
                continue
            lf_rng = random.Random(ring_lfern_rng.randint(0, 2**31))
            gz = _hill_elevation(bx, by)
            plant_max_z = min(25, internal_limit - gz - 1)
            if plant_max_z < 4:
                continue
            plant_m = VoxelModel()
            _build_large_fern(plant_m, TILE_SIZE // 2, TILE_SIZE // 2,
                             lf_rng, max_x=TILE_SIZE - 1,
                             max_y=TILE_SIZE - 1, max_z=plant_max_z)
            poff_x = bx - TILE_SIZE // 2
            poff_y = by - TILE_SIZE // 2
            for (vx, vy, vz), col in plant_m._v.items():
                wz = vz + gz
                wwx = poff_x + vx
                wwy = poff_y + vy
                if wz < internal_limit and fern_wx_min <= wwx <= fern_wx_max and fern_wy_min <= wwy <= fern_wy_max:
                    _write_voxel(wwx, wwy, wz, col)


        _ring_t = _time.time() - _t0
        n_trees = len(tree_by_ring.get(d, []))
        print(f"    Ring {d}: {len(tiles)} tiles, {n_trees} trees, limit={height_limit}, "
              f"ground={_ground_total:.1f}s, trees={_tree_total:.1f}s, total={_ring_t:.1f}s")

    # ---- Torch placement: Poisson disk distribution + all inner heroes ----
    print(f"  Placing torches ({len(all_tree_info)} trees tracked)...")
    torch_rng = random.Random(rng.randint(0, 2**31))

    def _write_voxel_clipped(wx, wy, wz, color, min_ring):
        """Write voxel only if it doesn't extend into a ring lower than min_ring."""
        if _wv_ring(wx, wy) < min_ring:
            return False
        return _write_voxel(wx, wy, wz, color)

    def _pick_torch_spots(canopy, trunk_wx, trunk_wy, count, min_spacing=8):
        """Pick canopy positions at exposed branch tips — top 25% by height,
        furthest from trunk, with minimum spacing between spots."""
        if not canopy:
            return []
        # Filter to top 25% by height
        sorted_by_z = sorted(canopy, key=lambda p: p[2], reverse=True)
        top_quarter = sorted_by_z[:max(10, len(sorted_by_z) // 4)]
        # Sort by XY distance from trunk (furthest = most exposed)
        top_quarter.sort(key=lambda p: (p[0]-trunk_wx)**2 + (p[1]-trunk_wy)**2, reverse=True)
        # Greedily select with minimum spacing
        selected = []
        min_sq = min_spacing * min_spacing
        for (cx, cy, cz) in top_quarter:
            too_close = False
            for (sx, sy, sz) in selected:
                if (cx-sx)**2 + (cy-sy)**2 + (cz-sz)**2 < min_sq:
                    too_close = True
                    break
            if not too_close:
                selected.append((cx, cy, cz))
            if len(selected) >= count * 3:
                break
        return selected

    inner_heroes = []
    poisson_candidates = []
    for ti in all_tree_info:
        if ti['is_inner'] and ti['is_hero']:
            inner_heroes.append(ti)
        else:
            poisson_candidates.append(ti)

    # Poisson disk sample points, find nearest tree for each
    TORCH_MIN_DIST = 96
    torch_points = _poisson_disk(torch_rng, TORCH_MIN_DIST,
                                  TILE_SIZE, WORLD_SIZE - TILE_SIZE, max_attempts=30)

    # For each point, find the closest non-inner tree with canopy
    torch_count = 0
    non_hero_torch_count = 0
    placed_torches = []  # (x, y, z) of all placed torches for spacing check
    TORCH_SPACING = 8
    TORCH_SPACING_SQ = TORCH_SPACING * TORCH_SPACING

    def _too_close(x, y, z):
        for (px, py, pz) in placed_torches:
            if (x-px)**2 + (y-py)**2 + (z-pz)**2 < TORCH_SPACING_SQ:
                return True
        return False

    for (px, py) in torch_points:
        best_tree = None
        best_dist = float('inf')
        for ti in poisson_candidates:
            if not ti['canopy'] or ti['h'] < 30:
                continue
            dist = (ti['wx'] - px) ** 2 + (ti['wy'] - py) ** 2
            if dist < best_dist:
                best_dist = dist
                best_tree = ti
        if best_tree is None or best_dist > (TORCH_MIN_DIST * 0.7) ** 2:
            continue
        canopy = best_tree['canopy']
        tree_ring = best_tree['ring']
        num_torches = torch_rng.randint(10, 12)
        top_canopy = _pick_torch_spots(canopy, best_tree['wx'], best_tree['wy'], num_torches)
        for _ in range(num_torches):
            if not top_canopy:
                break
            twx, twy, twz = torch_rng.choice(top_canopy)
            twx += torch_rng.randint(-2, 2)
            twy += torch_rng.randint(-2, 2)
            if twz <= 15 or _too_close(twx, twy, twz):
                continue
            rope_len = torch_rng.randint(3, 6)
            hang_z = twz - rope_len
            for z in range(twz, hang_z, -1):
                _write_voxel_clipped(twx, twy, z, TORCH_ROPE, tree_ring)
            pole_h = torch_rng.randint(4, 6)
            pole_top = hang_z
            pole_bot = pole_top - pole_h
            for z in range(pole_bot, pole_top):
                if z > 0:
                    _write_voxel_clipped(twx, twy, z, torch_rng.choice([BAMBOO_MID_1, BAMBOO_DARK]), tree_ring)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if dx != 0 or dy != 0:
                        _write_voxel_clipped(twx + dx, twy + dy, pole_top, TORCH_ROPE, tree_ring)
            bowl_z = pole_bot - 1
            if bowl_z > 0:
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        edge = (dx in (-1, 1)) or (dy in (-1, 1))
                        if edge:
                            _write_voxel_clipped(twx + dx, twy + dy, bowl_z, BAMBOO_DARK, tree_ring)
                        else:
                            _write_voxel_clipped(twx + dx, twy + dy, bowl_z,
                                        torch_rng.choice([TORCH_FLAME_1, TORCH_FLAME_2]), tree_ring)
                for dz in range(1, 3):
                    _write_voxel_clipped(twx, twy, bowl_z + dz,
                                torch_rng.choice([TORCH_FLAME_1, TORCH_FLAME_2]), tree_ring)
            placed_torches.append((twx, twy, twz))
            torch_count += 1
            non_hero_torch_count += 1

    # Inner heroes: all get torches (30-35 each)
    for ti in inner_heroes:
        canopy = ti['canopy']
        if not canopy:
            continue
        tree_ring = ti['ring']
        num_torches = torch_rng.randint(30, 35)
        top_canopy = _pick_torch_spots(canopy, ti['wx'], ti['wy'], num_torches)
        for _ in range(num_torches):
            if not top_canopy:
                break
            twx, twy, twz = torch_rng.choice(top_canopy)
            twx += torch_rng.randint(-2, 2)
            twy += torch_rng.randint(-2, 2)
            if twz <= 15 or _too_close(twx, twy, twz):
                continue
            rope_len = torch_rng.randint(3, 6)
            hang_z = twz - rope_len
            for z in range(twz, hang_z, -1):
                _write_voxel_clipped(twx, twy, z, TORCH_ROPE, tree_ring)
            pole_h = torch_rng.randint(4, 6)
            pole_top = hang_z
            pole_bot = pole_top - pole_h
            for z in range(pole_bot, pole_top):
                if z > 0:
                    _write_voxel_clipped(twx, twy, z, torch_rng.choice([BAMBOO_MID_1, BAMBOO_DARK]), tree_ring)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if dx != 0 or dy != 0:
                        _write_voxel_clipped(twx + dx, twy + dy, pole_top, TORCH_ROPE, tree_ring)
            bowl_z = pole_bot - 1
            if bowl_z > 0:
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        edge = (dx in (-1, 1)) or (dy in (-1, 1))
                        if edge:
                            _write_voxel_clipped(twx + dx, twy + dy, bowl_z, BAMBOO_DARK, tree_ring)
                        else:
                            _write_voxel_clipped(twx + dx, twy + dy, bowl_z,
                                        torch_rng.choice([TORCH_FLAME_1, TORCH_FLAME_2]), tree_ring)
                for dz in range(1, 3):
                    _write_voxel_clipped(twx, twy, bowl_z + dz,
                                torch_rng.choice([TORCH_FLAME_1, TORCH_FLAME_2]), tree_ring)
            placed_torches.append((twx, twy, twz))
            torch_count += 1

    hero_torch_count = torch_count - non_hero_torch_count
    print(f"    Placed {torch_count} torches: {non_hero_torch_count} on non-heroes, "
          f"{hero_torch_count} on {len(inner_heroes)} heroes, "
          f"{len(torch_points)} Poisson points")

    # ---- Dirt path from boardwalk to edge ----
    path_tiles = [(r, c) for (r, c), t in grid.items() if t == 'path']
    if path_tiles:
        path_rng = random.Random(rng.randint(0, 2**31))
        path_m = VoxelModel()
        mr_end = max(r for r, c in path_tiles)
        mc_end = max(c for r, c in path_tiles)
        base_wx = (GRID_SIZE - 1 - mr_end) * TILE_SIZE
        base_wy = (GRID_SIZE - 1 - mc_end) * TILE_SIZE

        # Path center line (world y) and half-width
        path_cy = int((GRID_SIZE - 0.5 - (BOARDWALK_COLS[0] + BOARDWALK_COLS[1]) / 2) * TILE_SIZE)
        path_half_w = TILE_SIZE  # 32 voxels = 1 tile each side of center

        # Pre-compute edge wobble per row (smooth noise)
        path_wx_min = min((GRID_SIZE - 1 - r) * TILE_SIZE for r, c in path_tiles)
        path_wx_max = max((GRID_SIZE - 1 - r) * TILE_SIZE + TILE_SIZE - 1 for r, c in path_tiles)
        wobble = {}
        wobble_rng = random.Random(path_rng.randint(0, 2**31))
        prev_w = 0.0
        for wx in range(path_wx_min, path_wx_max + 1):
            prev_w += wobble_rng.uniform(-3.0, 3.0)
            prev_w = max(-16, min(16, prev_w))  # wider drift
            wobble[wx] = prev_w

        # Palettes by zone — cooler browns, less red
        center_pal = [EARTH_HUMUS, EARTH_DARK, EARTH_DARK, EARTH_LITTER_1, EARTH_LITTER_2]
        mid_pal = [EARTH_DARK, EARTH_DARK, EARTH_HUMUS, EARTH_LITTER_1]
        edge_pal = [EARTH_DARK, EARTH_DARK, EARTH_HUMUS]
        grass_pal = G_DARK

        for (r, c) in sorted(path_tiles):
            twx, twy = tile_world_pos(r, c)
            for lx in range(TILE_SIZE):
                for ly in range(TILE_SIZE):
                    wx, wy = twx + lx, twy + ly
                    elev = 0  # single-layer flat ground under boardwalk path
                    mlx = wx - base_wx
                    mly = wy - base_wy

                    # Distance from path center with wobble
                    w = wobble.get(wx, 0)
                    dist = abs(wy - path_cy + w)
                    # Normalize: 0 = center, 1 = nominal edge
                    t = dist / path_half_w

                    # Per-voxel noise for edge breakup
                    edge_noise = path_rng.uniform(-0.25, 0.25)
                    t += edge_noise

                    for z in range(elev + 1):
                        if z < elev:
                            path_m.set(mlx, mly, z, path_rng.choice(EARTH_TONES))
                        elif t < 0.5:
                            # Center: worn packed earth
                            path_m.set(mlx, mly, z, path_rng.choice(center_pal))
                        elif t < 0.75:
                            # Mid: darker trampled earth
                            path_m.set(mlx, mly, z, path_rng.choice(mid_pal))
                        elif t < 1.0:
                            # Edge: dark mud, grass starting to encroach
                            if path_rng.random() < 0.3:
                                path_m.set(mlx, mly, z, path_rng.choice(grass_pal))
                            else:
                                path_m.set(mlx, mly, z, path_rng.choice(edge_pal))
                        else:
                            # Outside path: normal ground (earth + dark green)
                            if path_rng.random() < 0.35:
                                path_m.set(mlx, mly, z, path_rng.choice(G_DARK))
                            else:
                                path_m.set(mlx, mly, z, path_rng.choice(EARTH_TONES))

        # Scatter embedded stones on path surface
        stone_rng = random.Random(path_rng.randint(0, 2**31))
        for (r, c) in path_tiles:
            twx, twy = tile_world_pos(r, c)
            for _ in range(stone_rng.randint(0, 2)):
                sx = twx + stone_rng.randint(4, TILE_SIZE - 5)
                sy = twy + stone_rng.randint(4, TILE_SIZE - 5)
                sr = stone_rng.randint(1, 2)
                for ddx in range(-sr, sr + 1):
                    for ddy in range(-sr, sr + 1):
                        if ddx * ddx + ddy * ddy <= sr * sr:
                            px, py = sx + ddx, sy + ddy
                            path_m.set(px - base_wx, py - base_wy, 0,
                                      stone_rng.choice([STONE_MID, STONE_DARK]))

        # Scatter twigs across path
        twig_rng = random.Random(path_rng.randint(0, 2**31))
        twig_tones = ROOT_TONES + TRUNK_TONES[:2]
        for (r, c) in path_tiles:
            twx, twy = tile_world_pos(r, c)
            for _ in range(twig_rng.randint(1, 3)):
                tx = twx + twig_rng.randint(2, TILE_SIZE - 3)
                ty = twy + twig_rng.randint(2, TILE_SIZE - 3)
                angle = twig_rng.uniform(0, math.pi)
                tlen = twig_rng.randint(2, 5)
                col = twig_rng.choice(twig_tones)
                ddx = math.cos(angle)
                ddy = math.sin(angle)
                for step in range(-tlen // 2, tlen // 2 + 1):
                    px = int(round(tx + ddx * step))
                    py = int(round(ty + ddy * step))
                    if 0 <= px - base_wx < 256 and 0 <= py - base_wy < 256:
                        path_m.set(px - base_wx, py - base_wy, 0, col)

        if path_m._v:
            add_multimodel_structure("path", [(path_m, mr_end, mc_end, 0)])

    # Serialize forest structures (models already pre-allocated per merged group)
    print("  Serializing forest structures...")
    seen_models = set()
    for group_rings, group_limit, group_tiles in group_infos:
        if not group_tiles:
            continue
        rects = decompose_into_rectangles(group_tiles)
        for r1, c1, r2, c2 in rects:
            for struct_regions in split_into_structures(r1, c1, r2, c2, group_tiles):
                model_list = []
                for mr, mc, mr_end, mc_end in struct_regions:
                    sample_tile = None
                    for ri in range(mr, mr_end + 1):
                        for ci in range(mc, mc_end + 1):
                            if (ri, ci) in tile_to_model:
                                sample_tile = (ri, ci)
                                break
                        if sample_tile:
                            break
                    if sample_tile is None:
                        continue
                    info = tile_to_model[sample_tile]
                    mid = id(info['model'])
                    if mid in seen_models:
                        continue
                    seen_models.add(mid)
                    m = info['model']
                    if m._v:
                        model_list.append((m, mr_end, mc_end, info['base_wz']))
                if model_list:
                    add_multimodel_structure(f"forest_{struct_idx}", model_list)
                    struct_idx += 1

    # ---- 2. Boardwalk structures (consolidated prism groups) ----
    print("\nBuilding boardwalk structures...")
    bw_boundaries = compute_boardwalk_boundaries(random.Random(rng.randint(0, 2**31)))
    rows = list(range(BOARDWALK_ROW_START, BOARDWALK_ROW_END - 1, -1))
    n_segments = len(rows)

    # Consolidate: max 8 tiles per group (8*32=256 MagicaVoxel limit)
    max_per_group = 8
    groups = []
    for g_start in range(0, n_segments, max_per_group):
        g_end = min(g_start + max_per_group, n_segments)
        groups.append((g_start, g_end))

    for g_idx, (g_start, g_end) in enumerate(groups):
        n_tiles = g_end - g_start
        group_south_z = bw_boundaries[g_start]
        group_north_z = bw_boundaries[g_end]
        south_row = rows[g_start]  # southernmost row of group

        bw_rng = random.Random(rng.randint(0, 2**31))
        prism_model, base_model = build_boardwalk_segment(
            south_row, group_south_z, group_north_z, bw_rng, n_tiles=n_tiles,
            include_transition_step=(g_idx > 0))

        add_multimodel_structure(f"boardwalk_g{g_idx}_MinusZPrism",
                                 [(prism_model, south_row, BOARDWALK_COLS[1], group_south_z)])
        if base_model._v:
            add_multimodel_structure(f"boardwalk_g{g_idx}_base",
                                     [(base_model, south_row, BOARDWALK_COLS[1], 0)])

    # ---- 3. Platform structure (4x4 tiles) ----
    print("\nBuilding platform structure...")
    plat_rng = random.Random(rng.randint(0, 2**31))
    plat_model, plat_base = build_platform_model(plat_rng, grid)
    # Platform is a single large model covering tiles (14,14)-(17,17)
    # mr_end=17, mc_end=17 for world origin calculation
    # Inject tree overgrowth into platform model (below deck) and new structure (above deck)
    if platform_overgrowth:
        plat_bwx = (GRID_SIZE - 1 - PLATFORM_R_END) * TILE_SIZE
        plat_bwy = (GRID_SIZE - 1 - PLATFORM_C_END) * TILE_SIZE
        plat_width = (PLATFORM_R_END - PLATFORM_R_START + 1) * TILE_SIZE
        plat_depth = (PLATFORM_C_END - PLATFORM_C_START + 1) * TILE_SIZE
        above_deck = VoxelModel()
        below_count = 0
        above_count = 0
        for (wx, wy, wz, color) in platform_overgrowth:
            lx = wx - plat_bwx
            ly = wy - plat_bwy
            if not (0 <= lx < plat_width and 0 <= ly < plat_depth):
                continue
            if wz <= PLATFORM_DECK_Z:
                # At or below deck: write into platform model
                lz = wz - plat_base
                if lz >= 0:
                    plat_model.set(lx, ly, lz, color)
                    below_count += 1
            else:
                # Strictly above deck
                above_deck.set(lx, ly, wz - PLATFORM_DECK_Z - 1, color)
                above_count += 1
        print(f"    Platform overgrowth: {below_count} below deck, {above_count} above deck")

    plat_model_list = [(plat_model, PLATFORM_R_END, PLATFORM_C_END, plat_base)]
    add_multimodel_structure("platform", plat_model_list)

    if platform_overgrowth and above_deck._v:
        # Decompose above-deck voxels into connected components (26-connected flood fill)
        voxel_set = set(above_deck._v.keys())
        visited = set()
        clusters = []

        for v in voxel_set:
            if v in visited:
                continue
            # Flood fill from this voxel
            stack = [v]
            component = []
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                component.append(cur)
                cx, cy, cz = cur
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            if dx == 0 and dy == 0 and dz == 0:
                                continue
                            n = (cx + dx, cy + dy, cz + dz)
                            if n in voxel_set and n not in visited:
                                stack.append(n)
            clusters.append(component)

        def _bbox(cluster):
            xs = [v[0] for v in cluster]
            ys = [v[1] for v in cluster]
            zs = [v[2] for v in cluster]
            return (min(xs), min(ys), min(zs), max(xs)+1, max(ys)+1, max(zs)+1)

        # Remove clusters whose bbox is fully contained within another cluster's bbox
        def _bbox(cluster):
            xs = [v[0] for v in cluster]
            ys = [v[1] for v in cluster]
            zs = [v[2] for v in cluster]
            return (min(xs), min(ys), min(zs), max(xs)+1, max(ys)+1, max(zs)+1)

        def _contains(outer, inner):
            """True if outer bbox fully contains inner bbox."""
            return (outer[0] <= inner[0] and outer[3] >= inner[3] and
                    outer[1] <= inner[1] and outer[4] >= inner[4] and
                    outer[2] <= inner[2] and outer[5] >= inner[5])

        bboxes = [_bbox(c) for c in clusters]
        keep = []
        for i, cluster in enumerate(clusters):
            contained = False
            for j, other in enumerate(clusters):
                if i == j:
                    continue
                if _contains(bboxes[j], bboxes[i]) and len(other) > len(cluster):
                    contained = True
                    break
            if not contained:
                keep.append(cluster)
        print(f"    Removed {len(clusters) - len(keep)} contained clusters")
        clusters = keep

        # Merge adjacent clusters where the merged bbox doesn't add too much empty space
        def _bbox_vol(bb):
            return (bb[3]-bb[0]) * (bb[4]-bb[1]) * (bb[5]-bb[2])

        def _merged_bbox(a, b):
            return (min(a[0],b[0]), min(a[1],b[1]), min(a[2],b[2]),
                    max(a[3],b[3]), max(a[4],b[4]), max(a[5],b[5]))

        def _adjacent(a, b, gap=8):
            """True if bboxes overlap or are within gap voxels."""
            return (a[0] - gap < b[3] and a[3] + gap > b[0] and
                    a[1] - gap < b[4] and a[4] + gap > b[1] and
                    a[2] - gap < b[5] and a[5] + gap > b[2])

        MERGE_THRESHOLD = 4.0  # added volume <= 4.0x the smaller bbox volume
        changed = True
        while changed:
            changed = False
            bboxes = [_bbox(c) for c in clusters]
            best_score = float('inf')
            best_pair = None
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    if not _adjacent(bboxes[i], bboxes[j]):
                        continue
                    vol_i = _bbox_vol(bboxes[i])
                    vol_j = _bbox_vol(bboxes[j])
                    vol_smaller = min(vol_i, vol_j)
                    vol_larger = max(vol_i, vol_j)
                    mb = _merged_bbox(bboxes[i], bboxes[j])
                    vol_merged = _bbox_vol(mb)
                    vol_added = vol_merged - vol_larger
                    if vol_added <= MERGE_THRESHOLD * vol_smaller:
                        # Score: ratio of added volume to smaller (lower = tighter)
                        score = vol_added / max(vol_smaller, 1)
                        if score < best_score:
                            best_score = score
                            best_pair = (i, j)
            if best_pair:
                i, j = best_pair
                clusters[i] = clusters[i] + clusters[j]
                clusters.pop(j)
                changed = True

        print(f"    After merging: {len(clusters)} clusters")

        # Resolve overlapping bboxes: subtract larger bbox from smaller cluster
        bboxes = [_bbox(c) for c in clusters]
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                bi, bj = bboxes[i], bboxes[j]
                if not (bi[0] < bj[3] and bi[3] > bj[0] and
                        bi[1] < bj[4] and bi[4] > bj[1] and
                        bi[2] < bj[5] and bi[5] > bj[2]):
                    continue
                if _bbox_vol(bi) >= _bbox_vol(bj):
                    large_bb, small_idx = bi, j
                else:
                    large_bb, small_idx = bj, i
                clusters[small_idx] = [(x, y, z) for (x, y, z) in clusters[small_idx]
                                       if not (large_bb[0] <= x < large_bb[3] and
                                               large_bb[1] <= y < large_bb[4] and
                                               large_bb[2] <= z < large_bb[5])]
        clusters = [c for c in clusters if c]
        print(f"    After overlap resolution: {len(clusters)} clusters")

        # Delete small clusters by bbox volume
        MIN_BBOX_VOL = 4096
        before = len(clusters)
        clusters = [c for c in clusters if _bbox_vol(_bbox(c)) >= MIN_BBOX_VOL]
        print(f"    Deleted {before - len(clusters)} small clusters (vol < {MIN_BBOX_VOL}), {len(clusters)} remain")

        # Create a tight structure for each cluster
        for ci, cluster in enumerate(clusters):
            min_x = min(v[0] for v in cluster)
            min_y = min(v[1] for v in cluster)
            min_z = min(v[2] for v in cluster)
            bb = _bbox(cluster)
            sz = (bb[3]-bb[0], bb[4]-bb[1], bb[5]-bb[2])
            cm = VoxelModel()
            for (vx, vy, vz) in cluster:
                cm.set(vx - min_x, vy - min_y, vz - min_z, above_deck._v[(vx, vy, vz)])
            # z offset: PLATFORM_DECK_Z + 1 (strictly above deck) + min_z
            wz_off = PLATFORM_DECK_Z + 1 + min_z
            cm_model_list = [(cm, PLATFORM_R_END, PLATFORM_C_END, wz_off, (min_x, min_y))]
            add_multimodel_structure(f"overgrowth_{ci}", cm_model_list)
            print(f"      cluster {ci}: {len(cluster)} voxels, bbox {sz[0]}x{sz[1]}x{sz[2]}")
        print(f"    Above-deck overgrowth: {len(clusters)} clusters")

    # ---- 4. Arcade structure (centered on platform) ----
    print("\nBuilding arcade structure...")
    arc_rng = random.Random(rng.randint(0, 2**31))
    arc_model, arc_base = build_arcade_on_platform(arc_rng)
    # Platform center in world coords
    plat_wx = (GRID_SIZE - 1 - PLATFORM_R_END) * TILE_SIZE
    plat_wy = (GRID_SIZE - 1 - PLATFORM_C_END) * TILE_SIZE
    plat_w = (PLATFORM_R_END - PLATFORM_R_START + 1) * TILE_SIZE
    plat_d = (PLATFORM_C_END - PLATFORM_C_START + 1) * TILE_SIZE
    plat_cx = plat_wx + plat_w // 2
    plat_cy = plat_wy + plat_d // 2
    # Place cabinet centered on platform
    arc_size = arc_model.get_size()
    arc_wx = plat_cx - arc_size[0] // 2
    arc_wy = plat_cy - arc_size[1] // 2
    arc_tx, arc_ty, arc_tz = model_translation(arc_wx, arc_wy,
                                                arc_size[0], arc_size[1], arc_size[2],
                                                shift_x, shift_y)
    arc_tz += arc_base
    result = _voxelmodel_to_serialized(arc_model)
    if result:
        all_model_bytes += result['model_data']
        structures.append({
            'name': 'arcade',
            'models': [(model_index, (arc_tx, arc_ty, arc_tz), (arc_size[0], arc_size[1], arc_size[2]))],
        })
        print(f"    Structure 'arcade': 1 models")
        model_index += 1

    # ---- Write output ----
    print(f"\nTotal structures: {len(structures)}")
    print(f"Total models: {model_index}")

    filepath = os.path.join(output_dir, "snake_arcade.vox")
    write_structured_vox(filepath, all_model_bytes, structures, palette, materials)
    print(f"\nScene written to: {filepath}")


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    output_dir = os.path.join(os.path.dirname(__file__), "generated")
    os.makedirs(output_dir, exist_ok=True)
    generate_scene(output_dir)
