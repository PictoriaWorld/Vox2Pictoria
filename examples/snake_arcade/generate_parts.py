"""Snake Arcade Rainforest — Individual part generator.

Generates palette and standalone .vox files for each part:
  1. Palette PNG
  2. Forest ground tile
  3. Clearing ground tile
  4. Boardwalk segment
  5. Tiki torch
  6. Low jungle patch (128x128x52)
  7. Mid jungle patch (128x128x130)
  8. Tall jungle patch (128x128x235)
  9. Snake skull (128x96x160)
  10. Arcade machine (32x32x70)
  11. Abandoned camp (32x32x20)
  12. Snake skin on drying rack (32x32x10)
  13. Stone tablet with ouroboros (16x8x20)
  14. HIGH SCORE sign (24x8x24)
"""

import struct
import os
import random
import math
import zlib


# ============================================================
# .vox binary format writer
# ============================================================

def write_chunk(chunk_id: bytes, content: bytes, children: bytes = b"") -> bytes:
    return (
        chunk_id
        + struct.pack("<I", len(content))
        + struct.pack("<I", len(children))
        + content
        + children
    )


def _write_dict(pairs: dict[str, str]) -> bytes:
    data = struct.pack("<I", len(pairs))
    for key, value in pairs.items():
        kb = key.encode("utf-8")
        vb = value.encode("utf-8")
        data += struct.pack("<I", len(kb)) + kb
        data += struct.pack("<I", len(vb)) + vb
    return data


def _write_scene_graph(name: str = "structure0",
                       translation: tuple[int, int, int] | None = None) -> bytes:
    trn = struct.pack("<I", 0)
    trn += _write_dict({"_name": name})
    trn += struct.pack("<I", 1)
    trn += struct.pack("<i", -1)
    trn += struct.pack("<i", -1)
    trn += struct.pack("<I", 1)
    if translation is not None:
        trn += _write_dict({"_t": f"{translation[0]} {translation[1]} {translation[2]}"})
    else:
        trn += _write_dict({})
    ntrn_chunk = write_chunk(b"nTRN", trn)

    shp = struct.pack("<I", 1)
    shp += _write_dict({})
    shp += struct.pack("<I", 1)
    shp += struct.pack("<I", 0)
    shp += _write_dict({})
    nshp_chunk = write_chunk(b"nSHP", shp)

    return ntrn_chunk + nshp_chunk


def write_vox_file(filepath: str, size: tuple[int, int, int],
                    voxels: list[tuple[int, int, int, int]],
                    palette: list[tuple[int, int, int, int]],
                    materials: dict[int, dict[str, str]] | None = None,
                    translation: tuple[int, int, int] | None = None):
    size_content = struct.pack("<III", size[0], size[1], size[2])
    size_chunk = write_chunk(b"SIZE", size_content)

    xyzi_content = struct.pack("<I", len(voxels))
    for x, y, z, c in voxels:
        xyzi_content += struct.pack("<BBBB", x, y, z, c)
    xyzi_chunk = write_chunk(b"XYZI", xyzi_content)

    rgba_content = b""
    for i in range(1, 256):
        r, g, b, a = palette[i] if i < len(palette) else (0, 0, 0, 255)
        rgba_content += struct.pack("<BBBB", r, g, b, a)
    rgba_content += struct.pack("<BBBB", 0, 0, 0, 0)
    rgba_chunk = write_chunk(b"RGBA", rgba_content)

    scene_graph = _write_scene_graph(translation=translation)

    _MATL_DIFFUSE_DEFAULT = {"_rough": "0.1", "_ior": "0.3", "_ri": "1.3", "_d": "0.05"}
    matl_chunks = b""
    for mat_id in range(1, 257):
        props = materials.get(mat_id, _MATL_DIFFUSE_DEFAULT) if materials else _MATL_DIFFUSE_DEFAULT
        matl_content = struct.pack("<I", mat_id) + _write_dict(props)
        matl_chunks += write_chunk(b"MATL", matl_content)

    children = size_chunk + xyzi_chunk + scene_graph + rgba_chunk + matl_chunks
    main_chunk = write_chunk(b"MAIN", b"", children)
    header = b"VOX " + struct.pack("<I", 200)

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(header + main_chunk)

    print(f"  Written: {filepath}  ({len(voxels)} voxels, size {size[0]}x{size[1]}x{size[2]})")


def save_palette_png(palette, filepath):
    width, height = 256, 1
    raw = b'\x00'
    for i in range(1, 257):
        r, g, b, a = palette[i] if i < len(palette) else (0, 0, 0, 255)
        raw += struct.pack('BBBB', r, g, b, a)
    def _png_chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw)
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(_png_chunk(b'IHDR', ihdr))
        f.write(_png_chunk(b'IDAT', idat))
        f.write(_png_chunk(b'IEND', b''))
    print(f"  Palette saved: {filepath}")


# ============================================================
# VoxelModel helper
# ============================================================

class VoxelModel:
    def __init__(self):
        self._v = {}
        self._materials = {}

    def set(self, x, y, z, color):
        self._v[(x, y, z)] = color

    def delete(self, x, y, z):
        self._v.pop((x, y, z), None)

    def get(self, x, y, z):
        return self._v.get((x, y, z), 0)

    def has(self, x, y, z):
        return (x, y, z) in self._v

    def fill(self, x_range, y_range, z_range, color):
        for x in x_range:
            for y in y_range:
                for z in z_range:
                    self._v[(x, y, z)] = color

    def to_list(self):
        return [(x, y, z, c) for (x, y, z), c in self._v.items()]

    def get_size(self):
        if not self._v:
            return (1, 1, 1)
        coords = list(self._v.keys())
        return (
            max(c[0] for c in coords) + 1,
            max(c[1] for c in coords) + 1,
            max(c[2] for c in coords) + 1,
        )

    def set_material(self, palette_index: int, props: dict[str, str]):
        self._materials[palette_index] = props

    def shift(self, dx, dy, dz):
        """Shift all voxels by (dx, dy, dz)."""
        new_v = {}
        for (x, y, z), c in self._v.items():
            new_v[(x + dx, y + dy, z + dz)] = c
        self._v = new_v

    def get_min(self):
        """Return (minX, minY, minZ) of placed voxels."""
        if not self._v:
            return (0, 0, 0)
        coords = list(self._v.keys())
        return (
            min(c[0] for c in coords),
            min(c[1] for c in coords),
            min(c[2] for c in coords),
        )

    def save(self, filepath, palette, size=None, translation=None):
        write_vox_file(filepath, size or self.get_size(), self.to_list(), palette,
                       self._materials if self._materials else None,
                       translation=translation)


# ============================================================
# Color palette
# ============================================================

# Leaf greens (1-22)
LEAF_BRIGHT_1   = 1;  LEAF_BRIGHT_2   = 2;  LEAF_BRIGHT_3   = 3
LEAF_MID_1      = 4;  LEAF_MID_2      = 5;  LEAF_MID_3      = 6;  LEAF_MID_4 = 7
LEAF_DARK_1     = 8;  LEAF_DARK_2     = 9;  LEAF_DARK_3     = 10
LEAF_YELLOW_1   = 11; LEAF_YELLOW_2   = 12; LEAF_YELLOW_3   = 13
LEAF_BLUE_1     = 14; LEAF_BLUE_2     = 15; LEAF_BLUE_3     = 16
LEAF_CANOPY_1   = 17; LEAF_CANOPY_2   = 18; LEAF_CANOPY_3   = 19
LEAF_FRESH_1    = 20; LEAF_FRESH_2    = 21; LEAF_FRESH_3    = 22

# Moss greens (23-30)
MOSS_1 = 23; MOSS_2 = 24; MOSS_3 = 25; MOSS_4 = 26
MOSS_5 = 27; MOSS_6 = 28; MOSS_7 = 29; MOSS_8 = 30

# Browns (31-48)
BARK_DARK_1     = 31; BARK_DARK_2     = 32; BARK_DARK_3     = 33
BARK_MID_1      = 34; BARK_MID_2      = 35; BARK_MID_3      = 36
TRUNK_1         = 37; TRUNK_2         = 38; TRUNK_3         = 39
BOARDWALK_1     = 40; BOARDWALK_2     = 41; BOARDWALK_3     = 42
BOARDWALK_4     = 43; BOARDWALK_5     = 44
ROOT_1          = 45; ROOT_2          = 46; ROOT_3          = 47; ROOT_4 = 48

# Bone/ivory (49-60)
BONE_BASE       = 49; BONE_LIGHT      = 50; BONE_MID        = 51
BONE_DARK       = 52; BONE_SHADOW     = 53; BONE_CRACK      = 54
FANG_TIP        = 55; FANG_MID        = 56; FANG_BASE       = 57
BONE_AGED_1     = 58; BONE_AGED_2     = 59; BONE_AGED_3     = 60

# Earth/soil (61-70)
EARTH_HUMUS     = 61; EARTH_DARK      = 62; EARTH_MUD       = 63
EARTH_LITTER_1  = 64; EARTH_LITTER_2  = 65; EARTH_PACKED    = 66
EARTH_LIGHT     = 67; EARTH_RED       = 68; EARTH_CLAY      = 69
EARTH_GRAVEL    = 70

# Arcade cabinet (71-78)
ARCADE_BODY     = 71; ARCADE_BODY_2   = 72; ARCADE_TRIM     = 73
ARCADE_TRIM_2   = 74; ARCADE_BTN_RED  = 75; ARCADE_BTN_BLUE = 76
ARCADE_BTN_YEL  = 77; ARCADE_COIN     = 78

# Screen (79-82)
SCREEN_BRIGHT   = 79; SCREEN_DARK     = 80; SCREEN_PIXEL    = 81; SCREEN_BG = 82

# Tiki torch (83-86)
TORCH_BAMBOO    = 83; TORCH_ROPE      = 84; TORCH_FLAME_1   = 85; TORCH_FLAME_2 = 86

# Stone/gray (87-92)
STONE_LIGHT     = 87; STONE_MID       = 88; STONE_DARK      = 89
STONE_SHADOW    = 90; CAMPFIRE_ASH    = 91; CAMPFIRE_CHAR   = 92

# Fabric/misc (93-97)
CANVAS_1        = 93; CANVAS_2        = 94; LEATHER         = 95
ROPE_1          = 96; ROPE_2          = 97

# Snake skin (98-102)
SKIN_OLIVE      = 98; SKIN_GOLD       = 99; SKIN_DARK       = 100
SKIN_CREAM      = 101; SKIN_ACCENT    = 102

# Vine/hanging (103-108)
VINE_BRIGHT     = 103; VINE_MID       = 104; VINE_DARK      = 105
VINE_TENDRIL    = 106; AERIAL_ROOT_1  = 107; AERIAL_ROOT_2  = 108

# Bamboo tones (109-115)
BAMBOO_LIGHT    = 109; BAMBOO_MID_1   = 110; BAMBOO_MID_2   = 111
BAMBOO_DARK     = 112; BAMBOO_NODE    = 113; BAMBOO_SHADOW  = 114; BAMBOO_PALE = 115

# Large fern palette (135-138)
LFERN_BRIGHT    = 135; LFERN_MID      = 136; LFERN_DARK     = 137; LFERN_HIGHLIGHT = 138

# Flower/color accent (116-125)
FLOWER_RED_1    = 116; FLOWER_RED_2    = 117; FLOWER_ORANGE   = 118
FLOWER_YELLOW   = 119; FLOWER_PINK     = 120; FLOWER_PURPLE   = 121
FLOWER_WHITE    = 122; FLOWER_MAGENTA  = 123; FLOWER_CORAL    = 124
FLOWER_BLUE     = 125

# Alternate bark tones for tree variety (126-131)
BARK_GREY_1  = 126; BARK_GREY_2  = 127; BARK_GREY_3  = 128  # pale/grey bark (like eucalyptus)
BARK_RED_1   = 129; BARK_RED_2   = 130; BARK_RED_3   = 131  # reddish bark (like mahogany)

# Ouroboros stain tones (132-134) — slightly darker than boardwalk for subtle inscription
STAIN_1 = 132; STAIN_2 = 133; STAIN_3 = 134
STAIN_TONES = [STAIN_1, STAIN_2, STAIN_3]

# Tone groups for eden coloring (bright top, mid middle, dark bottom)
G_BRIGHT = [LEAF_BRIGHT_1, LEAF_BRIGHT_2, LEAF_BRIGHT_3, LEAF_CANOPY_1, LEAF_FRESH_1, LEAF_YELLOW_1]
G_MID    = [LEAF_MID_1, LEAF_MID_2, LEAF_MID_3, LEAF_MID_4, LEAF_CANOPY_2, LEAF_BLUE_1, LEAF_FRESH_2]
G_DARK   = [LEAF_DARK_1, LEAF_DARK_2, LEAF_DARK_3, LEAF_BLUE_2, LEAF_CANOPY_3, LEAF_FRESH_3]

# Alternative canopy hue sets — visually distinct per-tree color
# Warm: dominated by yellow-greens
G_BRIGHT_WARM = [LEAF_YELLOW_1, LEAF_YELLOW_2, LEAF_BRIGHT_3, LEAF_FRESH_1]
G_MID_WARM    = [LEAF_YELLOW_2, LEAF_YELLOW_3, LEAF_MID_1, LEAF_MID_4]
G_DARK_WARM   = [LEAF_DARK_1, LEAF_CANOPY_3, LEAF_FRESH_3]

# Cool: dominated by blue-greens
G_BRIGHT_COOL = [LEAF_BLUE_1, LEAF_CANOPY_1, LEAF_MID_1]
G_MID_COOL    = [LEAF_BLUE_1, LEAF_BLUE_2, LEAF_CANOPY_2, LEAF_MID_3]
G_DARK_COOL   = [LEAF_BLUE_2, LEAF_BLUE_3, LEAF_DARK_2, LEAF_DARK_3]

# Deep/dark: for trees that look darker overall
G_BRIGHT_DEEP = [LEAF_MID_1, LEAF_MID_2, LEAF_CANOPY_2]
G_MID_DEEP    = [LEAF_DARK_1, LEAF_DARK_2, LEAF_CANOPY_3, LEAF_BLUE_2]
G_DARK_DEEP   = [LEAF_DARK_2, LEAF_DARK_3, LEAF_BLUE_3]

# List of canopy palettes — each tree picks one for its entire canopy
CANOPY_PALETTES = [
    (G_BRIGHT, G_MID, G_DARK),          # standard vivid green
    (G_BRIGHT_WARM, G_MID_WARM, G_DARK_WARM),  # yellow-green
    (G_BRIGHT_COOL, G_MID_COOL, G_DARK_COOL),  # blue-green
    (G_BRIGHT_DEEP, G_MID_DEEP, G_DARK_DEEP),  # dark/deep
]

MOSS_TONES = [MOSS_1, MOSS_2, MOSS_3, MOSS_4, MOSS_5, MOSS_6, MOSS_7, MOSS_8]

BARK_TONES  = [BARK_DARK_1, BARK_DARK_2, BARK_DARK_3, BARK_MID_1, BARK_MID_2, BARK_MID_3]
TRUNK_TONES = [TRUNK_1, TRUNK_2, TRUNK_3, BARK_MID_1, BARK_MID_2]
ROOT_TONES  = [ROOT_1, ROOT_2, ROOT_3, ROOT_4, BARK_DARK_1]

# Alternate bark tone sets for tree variety (no grey — looks unnatural)
BARK_RED_TONES  = [BARK_RED_1, BARK_RED_2, BARK_RED_3]
BARK_PALETTE_OPTIONS = [BARK_TONES, BARK_TONES, BARK_RED_TONES]  # weighted toward standard brown

BOARDWALK_TONES = [BOARDWALK_1, BOARDWALK_2, BOARDWALK_3, BOARDWALK_4, BOARDWALK_5]
BONE_TONES  = [BONE_BASE, BONE_LIGHT, BONE_MID, BONE_AGED_1, BONE_AGED_2]
EARTH_TONES = [EARTH_HUMUS, EARTH_DARK, EARTH_LITTER_1, EARTH_LITTER_2, EARTH_RED]
CLEARING_TONES = [EARTH_PACKED, EARTH_LIGHT, EARTH_CLAY, EARTH_GRAVEL]

VINE_TONES  = [VINE_BRIGHT, VINE_MID, VINE_DARK, VINE_TENDRIL]
BAMBOO_TONES_ALL = [BAMBOO_LIGHT, BAMBOO_MID_1, BAMBOO_MID_2, BAMBOO_DARK, BAMBOO_NODE]

FLOWER_TONES = [FLOWER_RED_1, FLOWER_RED_2, FLOWER_ORANGE, FLOWER_YELLOW,
                FLOWER_PINK, FLOWER_PURPLE, FLOWER_WHITE, FLOWER_MAGENTA,
                FLOWER_CORAL, FLOWER_BLUE]

# 26-connected neighbor offsets
_NBRS_26 = [(dx, dy, dz)
            for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
            if (dx, dy, dz) != (0, 0, 0)]


def make_palette() -> list[tuple[int, int, int, int]]:
    pal = [(0, 0, 0, 255)] * 256

    # Leaf greens (1-22)
    pal[1]  = (100, 190, 60, 255)   # bright 1
    pal[2]  = (85, 175, 50, 255)    # bright 2
    pal[3]  = (115, 200, 70, 255)   # bright 3
    pal[4]  = (60, 140, 45, 255)    # mid 1
    pal[5]  = (55, 130, 40, 255)    # mid 2
    pal[6]  = (50, 120, 35, 255)    # mid 3
    pal[7]  = (65, 145, 50, 255)    # mid 4
    pal[8]  = (30, 80, 25, 255)     # dark 1
    pal[9]  = (25, 70, 20, 255)     # dark 2
    pal[10] = (20, 60, 18, 255)     # dark 3
    pal[11] = (140, 180, 50, 255)   # yellow-green 1
    pal[12] = (130, 170, 45, 255)   # yellow-green 2
    pal[13] = (120, 160, 40, 255)   # yellow-green 3
    pal[14] = (40, 120, 80, 255)    # blue-green 1
    pal[15] = (35, 105, 70, 255)    # blue-green 2
    pal[16] = (30, 90, 60, 255)     # blue-green 3
    pal[17] = (75, 155, 55, 255)    # canopy 1
    pal[18] = (65, 135, 45, 255)    # canopy 2
    pal[19] = (45, 100, 35, 255)    # canopy 3
    pal[20] = (90, 185, 65, 255)    # fresh 1
    pal[21] = (70, 150, 50, 255)    # fresh 2
    pal[22] = (40, 95, 30, 255)     # fresh 3

    # Moss greens (23-30)
    pal[23] = (95, 130, 45, 255)
    pal[24] = (85, 120, 40, 255)
    pal[25] = (75, 110, 35, 255)
    pal[26] = (65, 100, 30, 255)
    pal[27] = (105, 140, 50, 255)
    pal[28] = (55, 90, 28, 255)
    pal[29] = (110, 145, 55, 255)
    pal[30] = (80, 115, 38, 255)

    # Browns (31-48)
    pal[31] = (50, 30, 15, 255)     # bark dark 1
    pal[32] = (55, 35, 18, 255)     # bark dark 2
    pal[33] = (45, 28, 14, 255)     # bark dark 3
    pal[34] = (75, 50, 28, 255)     # bark mid 1
    pal[35] = (80, 55, 30, 255)     # bark mid 2
    pal[36] = (70, 48, 26, 255)     # bark mid 3
    pal[37] = (90, 62, 35, 255)     # trunk 1
    pal[38] = (85, 58, 32, 255)     # trunk 2
    pal[39] = (95, 65, 38, 255)     # trunk 3
    pal[40] = (120, 90, 55, 255)    # boardwalk 1 (weathered)
    pal[41] = (110, 82, 50, 255)    # boardwalk 2
    pal[42] = (100, 75, 45, 255)    # boardwalk 3
    pal[43] = (130, 98, 60, 255)    # boardwalk 4
    pal[44] = (95, 70, 42, 255)     # boardwalk 5
    pal[45] = (60, 38, 20, 255)     # root 1
    pal[46] = (65, 42, 22, 255)     # root 2
    pal[47] = (55, 35, 18, 255)     # root 3
    pal[48] = (70, 45, 25, 255)     # root 4

    # Bone/ivory (49-60)
    pal[49] = (235, 225, 200, 255)  # bone base
    pal[50] = (245, 238, 215, 255)  # bone light
    pal[51] = (220, 210, 185, 255)  # bone mid
    pal[52] = (200, 190, 165, 255)  # bone dark
    pal[53] = (170, 158, 135, 255)  # bone shadow
    pal[54] = (130, 115, 95, 255)   # bone crack
    pal[55] = (250, 245, 230, 255)  # fang tip
    pal[56] = (240, 232, 210, 255)  # fang mid
    pal[57] = (225, 215, 190, 255)  # fang base
    pal[58] = (210, 200, 178, 255)  # aged 1
    pal[59] = (195, 185, 162, 255)  # aged 2
    pal[60] = (180, 168, 148, 255)  # aged 3

    # Earth/soil (61-70) — cool neutral browns
    pal[61] = (58, 48, 35, 255)     # humus
    pal[62] = (42, 36, 26, 255)     # dark
    pal[63] = (65, 55, 40, 255)     # mud
    pal[64] = (72, 62, 45, 255)     # litter 1
    pal[65] = (62, 52, 38, 255)     # litter 2
    pal[66] = (82, 72, 55, 255)     # packed
    pal[67] = (92, 82, 62, 255)     # light
    pal[68] = (70, 52, 35, 255)     # red (now neutral)
    pal[69] = (78, 65, 48, 255)     # clay
    pal[70] = (115, 110, 100, 255)  # gravel

    # Arcade cabinet (71-78) — Nokia 3310 style
    pal[71] = (35, 45, 70, 255)     # body dark navy blue
    pal[72] = (45, 55, 80, 255)     # body 2 slightly lighter navy
    pal[73] = (170, 175, 180, 255)  # trim silver
    pal[74] = (145, 150, 155, 255)  # trim 2 darker silver
    pal[75] = (200, 45, 40, 255)    # button red
    pal[76] = (40, 80, 200, 255)    # button blue
    pal[77] = (220, 200, 40, 255)   # button yellow
    pal[78] = (155, 160, 165, 255)  # coin slot silver

    # Screen (79-82) — Nokia LCD yellow-green
    pal[79] = (170, 175, 180, 255)  # marquee text — Nokia silver (emissive)
    pal[80] = (43, 56, 10, 255)     # snake body dark olive
    pal[81] = (43, 56, 10, 255)     # food dots dark olive
    pal[82] = (167, 186, 80, 255)   # LCD background yellow-green

    # Tiki torch (83-86)
    pal[83] = (140, 120, 70, 255)   # bamboo pole
    pal[84] = (110, 85, 50, 255)    # rope binding
    pal[85] = (255, 180, 50, 255)   # flame amber (emissive)
    pal[86] = (255, 130, 30, 255)   # flame orange (emissive)

    # Stone/gray (87-92)
    pal[87] = (150, 145, 135, 255)  # light
    pal[88] = (120, 115, 108, 255)  # mid
    pal[89] = (90, 85, 80, 255)     # dark
    pal[90] = (65, 60, 55, 255)     # shadow
    pal[91] = (100, 95, 88, 255)    # ash
    pal[92] = (40, 35, 30, 255)     # charcoal

    # Fabric/misc (93-97)
    pal[93] = (165, 145, 110, 255)  # canvas 1
    pal[94] = (150, 132, 100, 255)  # canvas 2
    pal[95] = (100, 65, 35, 255)    # leather
    pal[96] = (140, 120, 80, 255)   # rope 1
    pal[97] = (125, 105, 70, 255)   # rope 2

    # Snake skin (98-102)
    pal[98]  = (90, 100, 50, 255)   # olive
    pal[99]  = (175, 155, 65, 255)  # gold
    pal[100] = (60, 45, 25, 255)    # dark brown
    pal[101] = (210, 195, 160, 255) # cream
    pal[102] = (130, 120, 55, 255)  # accent

    # Vine/hanging (103-108)
    pal[103] = (80, 150, 55, 255)   # bright
    pal[104] = (60, 120, 42, 255)   # mid
    pal[105] = (40, 85, 30, 255)    # dark
    pal[106] = (70, 135, 48, 255)   # tendril
    pal[107] = (75, 52, 30, 255)    # aerial root 1
    pal[108] = (65, 45, 25, 255)    # aerial root 2

    # Bamboo tones (109-115)
    pal[109] = (175, 160, 100, 255) # light
    pal[110] = (155, 140, 85, 255)  # mid 1
    pal[111] = (140, 125, 75, 255)  # mid 2
    pal[112] = (115, 100, 60, 255)  # dark
    pal[113] = (100, 88, 52, 255)   # node
    pal[114] = (85, 72, 42, 255)    # shadow
    pal[115] = (185, 170, 110, 255) # pale

    # Flower/color accents (116-125) — bright tropical pops
    pal[116] = (220, 40, 30, 255)   # red 1 (bromeliad)
    pal[117] = (190, 30, 25, 255)   # red 2
    pal[118] = (240, 130, 20, 255)  # orange (heliconia)
    pal[119] = (245, 220, 40, 255)  # yellow
    pal[120] = (230, 100, 140, 255) # pink
    pal[121] = (140, 50, 180, 255)  # purple (orchid)
    pal[122] = (245, 240, 235, 255) # white
    pal[123] = (210, 50, 120, 255)  # magenta
    pal[124] = (240, 110, 80, 255)  # coral
    pal[125] = (60, 80, 210, 255)   # blue (rare)

    # Alternate bark: grey/pale (126-128)
    pal[126] = (140, 135, 125, 255) # grey bark light
    pal[127] = (115, 110, 102, 255) # grey bark mid
    pal[128] = (90, 86, 80, 255)    # grey bark dark

    # Ouroboros stain tones (132-134) — noticeably darker than boardwalk
    pal[132] = (55, 38, 22, 255)    # stain light
    pal[133] = (45, 30, 18, 255)    # stain mid
    pal[134] = (35, 24, 14, 255)    # stain dark

    # Large fern palette — rich saturated green, between G_DARK and G_MID
    pal[135] = (40, 115, 30, 255)    # large fern bright
    pal[136] = (32, 100, 25, 255)    # large fern mid
    pal[137] = (25, 85, 20, 255)     # large fern dark
    pal[138] = (48, 125, 35, 255)    # large fern highlight

    # Alternate bark: reddish (129-131)
    pal[129] = (110, 55, 30, 255)   # red bark light
    pal[130] = (90, 42, 22, 255)    # red bark mid
    pal[131] = (70, 32, 16, 255)    # red bark dark

    return pal


def get_materials() -> dict[int, dict[str, str]]:
    _DEFAULT = {"_rough": "0.1", "_ior": "0.3", "_ri": "1.3", "_d": "0.05"}
    mats = {}
    for i in range(1, 257):
        mats[i] = _DEFAULT
    # Screen emissive — Nokia LCD style
    # Marquee text: bright green glow
    mats[SCREEN_BRIGHT] = {"_type": "_emit", "_emit": "0.8", "_flux": "3"}
    # Snake body + food: dark olive, non-emissive (pixels on LCD)
    mats[SCREEN_DARK] = _DEFAULT
    mats[SCREEN_PIXEL] = _DEFAULT
    # LCD background: yellow-green glow (the backlight)
    mats[SCREEN_BG] = {"_type": "_emit", "_emit": "0.5", "_flux": "2"}
    # Torch flame emissive
    mats[TORCH_FLAME_1] = {"_type": "_emit", "_emit": "0.8", "_flux": "3"}
    mats[TORCH_FLAME_2] = {"_type": "_emit", "_emit": "0.7", "_flux": "3"}
    # Arcade trim metallic
    mats[ARCADE_TRIM] = {"_rough": "0.8", "_ior": "0.3"}  # matte silver, not reflective
    mats[ARCADE_TRIM_2] = {"_rough": "0.8", "_ior": "0.3"}
    mats[ARCADE_COIN] = {"_rough": "0.7", "_ior": "0.3"}
    return mats


# ============================================================
# Wood grain helper
# ============================================================

def streak(tones, length, rng):
    pat, cur = [], rng.choice(tones)
    left = rng.randint(1, 12)
    for _ in range(length):
        if left <= 0:
            cur = rng.choice(tones)
            left = rng.randint(5, 12)
        pat.append(cur)
        left -= 1
    return pat


# ============================================================
# Shared vegetation functions
# ============================================================

def _leaf_cluster(model, cx, cy, cz, r, tones, rng, max_x=255, max_y=255, max_z=255):
    """Grow an organic leaf cluster using Eden growth (26-connected)."""
    target = max(8, int((4.0 / 3.0) * math.pi * r**3 * 0.14))
    r_sq = r * r

    def _in_bounds(x, y, z):
        return 0 <= x <= max_x and 0 <= y <= max_y and 0 <= z <= max_z

    placed = {(cx, cy, cz)}
    frontier = []
    for nd in _NBRS_26:
        frontier.append((cx + nd[0], cy + nd[1], cz + nd[2]))

    while len(placed) < target and frontier:
        idx = rng.randint(0, len(frontier) - 1)
        pos = frontier[idx]
        frontier[idx] = frontier[-1]
        frontier.pop()

        if pos in placed:
            continue
        if not _in_bounds(pos[0], pos[1], pos[2]):
            continue

        dx, dy, dz = pos[0] - cx, pos[1] - cy, pos[2] - cz
        dist_sq = dx * dx + dy * dy + dz * dz
        if dist_sq > r_sq * 3.0:
            continue
        if dist_sq > r_sq * 0.7 and rng.random() < 0.10:
            continue

        placed.add(pos)
        dist_from_seed = math.sqrt(dist_sq)
        frac_r = dist_from_seed / max(r, 0.1)
        for nd in _NBRS_26:
            np = (pos[0] + nd[0], pos[1] + nd[1], pos[2] + nd[2])
            if np not in placed:
                frontier.append(np)
                if frac_r < 0.4 and nd[2] > 0:
                    frontier.append(np)
                    frontier.append(np)
                elif frac_r > 0.5 and nd[2] < 0:
                    for _ in range(6):
                        frontier.append(np)

    # Color by z-position
    min_z = min(p[2] for p in placed)
    max_z_v = max(p[2] for p in placed)
    z_range = max(1, max_z_v - min_z)
    for px, py, pz in placed:
        z_frac = (pz - min_z) / z_range
        if z_frac > 0.6:
            c = rng.choice(tones[0])
        elif z_frac > 0.3:
            c = rng.choice(tones[1])
        else:
            c = rng.choice(tones[2])
        model.set(px, py, pz, c)

    return placed


def _grow_trunk(model, x, y, max_height, width, rng, tones=None, max_x=255, max_y=255):
    """Grow a tree trunk upward. Gradually widens toward the base over the
    bottom 40% of the trunk — like a real tree, not a telephone pole."""
    if tones is None:
        tones = BARK_TONES
    path = []
    fx, fy = float(x), float(y)
    half = width // 2

    # How much extra radius at z=0 (scales with trunk size)
    flare_extra = max(2, width)
    # The widening happens over the bottom 40% of the trunk
    flare_height = max(6, int(max_height * 0.4))

    lean_dx = rng.uniform(-0.15, 0.15)
    lean_dy = rng.uniform(-0.15, 0.15)

    for z in range(max_height):
        ix, iy = int(round(fx)), int(round(fy))
        path.append((ix, iy, z))

        # Radius: normal trunk width at top, gradually wider toward ground
        if z < flare_height:
            # Smooth curve: wide at ground, easing into trunk width
            t = z / flare_height  # 0=ground, 1=end of flare
            extra = flare_extra * (1.0 - t) * (1.0 - t)  # quadratic ease
            eff_half = half + extra
        else:
            eff_half = half

        eff_half_sq = (eff_half + 0.5) * (eff_half + 0.5)
        r_int = int(math.ceil(eff_half))
        for dx in range(-r_int, r_int + 1):
            for dy in range(-r_int, r_int + 1):
                if dx * dx + dy * dy <= eff_half_sq:
                    px, py = ix + dx, iy + dy
                    if 0 <= px <= max_x and 0 <= py <= max_y:
                        model.set(px, py, z, rng.choice(tones))

        fx += lean_dx + rng.uniform(-0.06, 0.06)
        fy += lean_dy + rng.uniform(-0.06, 0.06)
        fx = max(r_int, min(max_x - r_int, fx))
        fy = max(r_int, min(max_y - r_int, fy))

    return path


def _moss_on_trunk(model, trunk_path, width, rng, max_x=255, max_y=255):
    """Cover a trunk's surface with moss patches."""
    half = width // 2
    for ix, iy, iz in trunk_path:
        if rng.random() > 0.35:
            continue
        # Place moss on the outer surface of the trunk
        for dx in range(-half - 1, half + 2):
            for dy in range(-half - 1, half + 2):
                dist_sq = dx * dx + dy * dy
                inner = (half - 0.5) * (half - 0.5)
                outer = (half + 1.5) * (half + 1.5)
                if inner < dist_sq <= outer:
                    px, py = ix + dx, iy + dy
                    if 0 <= px <= max_x and 0 <= py <= max_y:
                        if rng.random() < 0.5:
                            model.set(px, py, iz, rng.choice(MOSS_TONES))


def _grow_buttress(model, base_x, base_y, base_z, dx, dy, rng, tones=None,
                    max_x=255, max_y=255, height=None):
    """Large triangular buttress root fin extending outward from trunk base.
    Fills a solid triangle: tall at trunk, tapering to ground at the tip.
    Thick (3 voxels perpendicular) so they're visible from isometric view."""
    if tones is None:
        tones = ROOT_TONES
    if height is None:
        height = rng.randint(8, 18)
    # Length scales with height — taller fins spread further
    length = max(8, int(height * 1.2) + rng.randint(0, 4))

    # Perpendicular direction for fin thickness
    mag = math.sqrt(dx * dx + dy * dy) or 1.0
    perp_x = -dy / mag
    perp_y = dx / mag

    for step in range(length):
        t = step / max(length - 1, 1)
        # Position along the root direction
        rx = base_x + dx * step * 1.5
        ry = base_y + dy * step * 1.5
        # Height tapers linearly from full at trunk to 1 at tip
        fin_h = max(1, int(height * (1.0 - t)))
        # Thickness tapers: 3 at base, 1 at tip
        thickness = max(1, int(3 * (1.0 - t * 0.7)))

        for z in range(fin_h):
            for th in range(-thickness // 2, thickness // 2 + 1):
                px = int(round(rx + perp_x * th))
                py = int(round(ry + perp_y * th))
                if 0 <= px <= max_x and 0 <= py <= max_y and z >= 0:
                    model.set(px, py, z, rng.choice(tones))


def _grow_branch(model, start, lean_dx, lean_dy, rng, tones=None,
                  max_x=255, max_y=255, max_z=255, length=None, dz_trend=None):
    """Grow a branch from a trunk point. dz_trend controls upward angle."""
    if tones is None:
        tones = TRUNK_TONES
    path = []
    if length is None:
        length = rng.randint(12, 35)
    if dz_trend is None:
        dz_trend = rng.uniform(0.02, 0.18)
    fx, fy, fz = float(start[0]), float(start[1]), float(start[2])
    for step in range(length):
        ix, iy, iz = int(round(fx)), int(round(fy)), int(round(fz))
        if not (0 <= ix <= max_x and 0 <= iy <= max_y and 0 <= iz <= max_z):
            break
        path.append((ix, iy, iz))
        model.set(ix, iy, iz, rng.choice(tones))
        if step < length * 0.4:
            for adj in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                ax, ay = ix + adj[0], iy + adj[1]
                if 0 <= ax <= max_x and 0 <= ay <= max_y:
                    model.set(ax, ay, iz, rng.choice(tones))
        fx += lean_dx + rng.uniform(-0.15, 0.15)
        fy += lean_dy + rng.uniform(-0.15, 0.15)
        fz += dz_trend + rng.uniform(-0.08, 0.12)
    return path


def _build_canopy_dome(model, trunk_path, trunk_height, bark_tones, canopy_pal,
                        r_range, rng, max_x, max_y, max_z):
    """Build a dome-shaped canopy from many small clusters.

    Key: branch angle and length vary by height on trunk.
    - Lower branches: nearly horizontal, long reach → wide dome base
    - Upper branches: steep (45°+), shorter → dome top
    This creates a natural umbrella/dome silhouette.
    """
    all_canopy = []
    branch_start_idx = max(1, int(len(trunk_path) * 0.65))
    branch_zone = len(trunk_path) - branch_start_idx

    spread = max(15, trunk_height // 3)
    small_r_min = max(3.7, r_range[0] * 0.35)
    small_r_max = max(6.0, r_range[1] * 0.4)
    n_primary = max(18, trunk_height * 3 // 8)

    def _add_cluster(tip, r_min, r_max):
        cr = rng.uniform(r_min, r_max)
        c = _leaf_cluster(model, tip[0], tip[1], tip[2], cr,
                         canopy_pal, rng,
                         max_x=max_x, max_y=max_y, max_z=max_z)
        all_canopy.extend(c)

    for _ in range(n_primary):
        angle = rng.uniform(0, 2 * math.pi)
        bi = rng.randint(branch_start_idx, len(trunk_path) - 1)
        start = trunk_path[bi]

        # How high is this branch relative to the branching zone?
        # 0.0 = lowest branch, 1.0 = top of trunk
        height_frac = (bi - branch_start_idx) / max(1, branch_zone)

        # Fan shape: lower branches ~70° from vertical (nearly horizontal), long
        # Upper branches nearly vertical, short → semicircle dome
        dz = 0.25 + height_frac * 0.65 + rng.uniform(-0.05, 0.05)
        lean_strength = (1.0 - height_frac * 0.5) * rng.uniform(0.7, 1.0)
        br_len_factor = 1.4 - height_frac * 1.0  # lower=much longer
        br_len = int(rng.uniform(0.8, 1.0) * spread * br_len_factor)
        br_len = max(5, br_len)

        ldx = math.cos(angle) * lean_strength
        ldy = math.sin(angle) * lean_strength
        br_path = _grow_branch(model, start, ldx, ldy, rng, tones=bark_tones,
                              max_x=max_x, max_y=max_y, max_z=max_z,
                              length=br_len, dz_trend=dz)
        if not br_path:
            continue

        _add_cluster(br_path[-1], small_r_min, small_r_max)

        # Sub-branches
        n_secondary = rng.randint(2, 4)
        for _ in range(n_secondary):
            if len(br_path) < 4:
                break
            si = rng.randint(max(1, len(br_path) // 3), len(br_path) - 1)
            sub_start = br_path[si]
            sub_angle = angle + rng.uniform(-1.5, 1.5)
            sub_lean = rng.uniform(0.3, 0.7)
            sub_len = rng.randint(4, max(6, br_len // 2))
            sub_dz = dz + rng.uniform(-0.1, 0.15)
            sub_path = _grow_branch(
                model, sub_start,
                math.cos(sub_angle) * sub_lean,
                math.sin(sub_angle) * sub_lean,
                rng, tones=bark_tones,
                max_x=max_x, max_y=max_y, max_z=max_z,
                length=sub_len, dz_trend=sub_dz)
            if sub_path:
                _add_cluster(sub_path[-1], small_r_min, small_r_max)

                # Tertiary twigs
                for _ in range(rng.randint(1, 2)):
                    if len(sub_path) < 3:
                        break
                    ti = rng.randint(len(sub_path) // 2, len(sub_path) - 1)
                    t_angle = sub_angle + rng.uniform(-1.0, 1.0)
                    t_len = rng.randint(3, max(4, sub_len // 2))
                    t_path = _grow_branch(
                        model, sub_path[ti],
                        math.cos(t_angle) * rng.uniform(0.3, 0.5),
                        math.sin(t_angle) * rng.uniform(0.3, 0.5),
                        rng, tones=bark_tones,
                        max_x=max_x, max_y=max_y, max_z=max_z,
                        length=t_len, dz_trend=sub_dz + 0.1)
                    if t_path:
                        _add_cluster(t_path[-1], small_r_min * 0.8, small_r_max * 0.9)

    # Crown at top
    _add_cluster(trunk_path[-1], small_r_min + 1, small_r_max + 1)

    return all_canopy


def _grow_vines(model, canopy_positions, rng, count=5, max_x=255, max_y=255, max_z=255):
    """Grow hanging vines downward from canopy.
    Two types:
      1. Aerial roots — brown, thin (1px), from any canopy position
      2. Green vines — thick (2×2), from high branches, matching boardwalk vine style
    """
    if not canopy_positions:
        return
    sorted_by_z = sorted(canopy_positions, key=lambda p: p[2], reverse=True)
    high_positions = sorted_by_z[:max(20, len(sorted_by_z) * 35 // 100)]
    all_positions = list(canopy_positions)
    # Use max canopy z for vine length (how far they can hang)
    max_z_canopy = max(p[2] for p in canopy_positions)

    for i in range(count):
        if rng.random() < 0.25:
            # --- Aerial root: thin brown, from any canopy position ---
            pool = all_positions if all_positions else high_positions
            if not pool:
                continue
            start = rng.choice(pool)
            sx, sy, sz = start
            vine_tone = rng.choice([AERIAL_ROOT_1, AERIAL_ROOT_2, VINE_DARK])
            sx += rng.randint(-2, 2)
            sy += rng.randint(-2, 2)
            for z in range(sz, 0, -1):
                if 0 <= sx <= max_x and 0 <= sy <= max_y:
                    model.set(sx, sy, z, vine_tone)
                    if rng.random() < 0.05:
                        sx += rng.choice([-1, 0, 1])
                        sy += rng.choice([-1, 0, 1])
                        sx = max(0, min(max_x, sx))
                        sy = max(0, min(max_y, sy))
        else:
            # --- Green vine: thick 2×2, from high branches ---
            if not high_positions:
                continue
            start = rng.choice(high_positions)
            sx, sy, sz = start
            sx += rng.randint(-2, 2)
            sy += rng.randint(-2, 2)
            vine_len = rng.randint(max(36, max_z_canopy * 3 // 5), max(48, max_z_canopy))

            origin_x, origin_y = sx, sy
            for dz in range(vine_len):
                vz = sz - dz
                if vz <= 0:
                    break
                sway_x = origin_x + (rng.choice([-1, 0, 1]) if dz > 3 else 0)
                sway_y = origin_y + (rng.choice([-1, 0, 1]) if dz > 3 else 0)
                for vdx in range(2):
                    for vdy in range(2):
                        px, py = sway_x + vdx, sway_y + vdy
                        if 0 <= px <= max_x and 0 <= py <= max_y:
                            model.set(px, py, vz, rng.choice(VINE_TONES))


def _add_epiphytes(model, trunk_path, width, rng, max_x=255, max_y=255, max_z=255):
    """Add bromeliads, ferns, and small plants growing on the trunk surface."""
    half = width // 2
    # Place 3-8 epiphyte clusters on the trunk
    num = rng.randint(3, 8)
    for _ in range(num):
        if not trunk_path:
            break
        # Pick a random point on the trunk (upper 70%)
        pi = rng.randint(max(0, len(trunk_path) // 3), len(trunk_path) - 1)
        tx, ty, tz = trunk_path[pi]
        # Place on a random side of the trunk
        side_dx = rng.choice([-1, 1]) * (half + 1)
        side_dy = rng.choice([-1, 1]) * (half + 1)
        if rng.random() < 0.5:
            side_dy = 0
        else:
            side_dx = 0
        ex, ey = tx + side_dx, ty + side_dy
        if not (0 <= ex <= max_x and 0 <= ey <= max_y):
            continue
        # Small cluster of leaves
        for dz in range(-1, 2):
            for ddx in range(-1, 2):
                for ddy in range(-1, 2):
                    px, py, pz = ex + ddx, ey + ddy, tz + dz
                    if 0 <= px <= max_x and 0 <= py <= max_y and 0 <= pz <= max_z:
                        if rng.random() < 0.4:
                            model.set(px, py, pz, rng.choice(G_DARK + G_MID[:2]))
        # Occasional flower/bright center
        if rng.random() < 0.3:
            model.set(ex, ey, tz, rng.choice(FLOWER_TONES))


def _build_palm(model, x, y, max_h, rng, max_x=255, max_y=255, max_z=255):
    """Build a palm tree: trunk width scales with height, branches near top for tall ones."""
    if max_h < 25:
        return
    height = rng.randint(15, min(50, max_h - 8))
    if height < 10:
        return

    # Palm trunk: 2x2 for tall, 1x1 for short
    use_2x2 = height >= 25

    # Leaning trunk
    lean_dx = rng.uniform(-0.12, 0.12)
    lean_dy = rng.uniform(-0.12, 0.12)
    fx, fy = float(x), float(y)
    trunk_path = []
    for z in range(height):
        ix, iy = int(round(fx)), int(round(fy))
        trunk_path.append((ix, iy, z))
        if use_2x2:
            for ddx in range(2):
                for ddy in range(2):
                    px, py = ix + ddx, iy + ddy
                    if 0 <= px <= max_x and 0 <= py <= max_y:
                        model.set(px, py, z, rng.choice(TRUNK_TONES))
        else:
            if 0 <= ix <= max_x and 0 <= iy <= max_y:
                model.set(ix, iy, z, rng.choice(TRUNK_TONES))
        fx += lean_dx + rng.uniform(-0.05, 0.05)
        fy += lean_dy + rng.uniform(-0.05, 0.05)

    crown_x, crown_y = int(round(fx)), int(round(fy))

    def _place_fronds(cx, cy, cz, num, flen_range):
        for _ in range(num):
            angle = rng.uniform(0, 2 * math.pi)
            frond_len = rng.randint(flen_range[0], flen_range[1])
            ffx, ffy, ffz = float(cx), float(cy), float(cz)
            fdx = math.cos(angle) * 0.7
            fdy = math.sin(angle) * 0.7
            for step in range(frond_len):
                ix, iy, iz = int(round(ffx)), int(round(ffy)), int(round(ffz))
                if 0 <= ix <= max_x and 0 <= iy <= max_y and 0 <= iz <= max_z:
                    model.set(ix, iy, iz, rng.choice(G_BRIGHT + G_MID[:2]))
                    for perp in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        px, py = ix + perp[0], iy + perp[1]
                        if 0 <= px <= max_x and 0 <= py <= max_y and rng.random() < 0.3:
                            model.set(px, py, iz, rng.choice(G_MID + G_DARK[:2]))
                ffx += fdx
                ffy += fdy
                if step < frond_len // 3:
                    ffz += 0.3
                else:
                    ffz -= 0.4

    # Main crown fronds at top
    _place_fronds(crown_x, crown_y, height, rng.randint(5, 8), (8, 16))

    # Taller palms get 1-2 side branches with smaller frond clusters
    if height >= 28 and trunk_path:
        num_branches = rng.randint(1, 2)
        for _ in range(num_branches):
            # Branch point in upper third of trunk
            bp_idx = rng.randint(height * 2 // 3, height - 3)
            bx, by, bz = trunk_path[bp_idx]
            _place_fronds(bx, by, bz, rng.randint(3, 5), (5, 10))


def _build_giant_fern(model, x, y, rng, max_x=255, max_y=255, max_z=255):
    """Build a giant tree fern: short stalk with arching fronds like a fountain."""
    stalk_h = rng.randint(4, 10)
    # Short thick stalk
    for z in range(stalk_h):
        if 0 <= x <= max_x and 0 <= y <= max_y:
            model.set(x, y, z, rng.choice(TRUNK_TONES))
    # 6-10 fronds arching outward and downward
    num_fronds = rng.randint(6, 10)
    for _ in range(num_fronds):
        angle = rng.uniform(0, 2 * math.pi)
        frond_len = rng.randint(6, 12)
        fdx = math.cos(angle) * 0.8
        fdy = math.sin(angle) * 0.8
        ffx, ffy, ffz = float(x), float(y), float(stalk_h)
        for step in range(frond_len):
            ix, iy, iz = int(round(ffx)), int(round(ffy)), int(round(ffz))
            if 0 <= ix <= max_x and 0 <= iy <= max_y and 0 <= iz <= max_z:
                # Main frond voxel
                c = rng.choice(G_MID + G_DARK[:2])
                model.set(ix, iy, iz, c)
                # Leaf width: alternating sides for pinnate look
                side = 1 if step % 2 == 0 else -1
                lx = ix + int(round(-fdy * side))
                ly = iy + int(round(fdx * side))
                if 0 <= lx <= max_x and 0 <= ly <= max_y:
                    model.set(lx, ly, iz, rng.choice(G_BRIGHT + G_MID[:2]))
            ffx += fdx
            ffy += fdy
            # Fountain curve: rise briefly then droop
            if step < frond_len // 4:
                ffz += 0.5
            else:
                ffz -= 0.35


def _build_large_fern(model, x, y, rng, max_x=255, max_y=255, max_z=255):
    """Large understory fern: same structure as giant fern but bigger,
    more upward angle, and warm olive/lime colors for contrast."""
    stalk_h = rng.randint(6, 14)
    for z in range(stalk_h):
        # 2x2 stalk
        for ddx in range(2):
            for ddy in range(2):
                px, py = x + ddx, y + ddy
                if 0 <= px <= max_x and 0 <= py <= max_y:
                    model.set(px, py, z, rng.choice(TRUNK_TONES))
    # 8-12 fronds, longer, more upward
    num_fronds = rng.randint(8, 12)
    for _ in range(num_fronds):
        angle = rng.uniform(0, 2 * math.pi)
        frond_len = rng.randint(12, 20)
        fdx = math.cos(angle) * 0.8
        fdy = math.sin(angle) * 0.8
        ffx, ffy, ffz = float(x), float(y), float(stalk_h)
        for step in range(frond_len):
            ix, iy, iz = int(round(ffx)), int(round(ffy)), int(round(ffz))
            if 0 <= ix <= max_x and 0 <= iy <= max_y and 0 <= iz <= max_z:
                # Main frond spine — dark emerald
                model.set(ix, iy, iz, rng.choice([LFERN_MID, LFERN_DARK]))
                # Pinnate leaves — 2 voxels per side, alternating
                side = 1 if step % 2 == 0 else -1
                for w in range(1, 3):  # 2 voxels wide per side
                    lx = ix + int(round(-fdy * side * w))
                    ly = iy + int(round(fdx * side * w))
                    if 0 <= lx <= max_x and 0 <= ly <= max_y:
                        model.set(lx, ly, iz, rng.choice([LFERN_BRIGHT, LFERN_HIGHLIGHT]))
            ffx += fdx
            ffy += fdy
            # More upward: rise for first half, gentle droop after
            if step < frond_len // 2:
                ffz += 0.45
            else:
                ffz -= 0.2


def _build_broad_leaf_plant(model, x, y, rng, max_x=255, max_y=255, max_z=255):
    """Build a broad-leafed plant (elephant ear / monstera) at ground level.
    Flat planes of green angled upward from a central stem."""
    stem_h = rng.randint(2, 5)
    for z in range(stem_h):
        if 0 <= x <= max_x and 0 <= y <= max_y:
            model.set(x, y, z, rng.choice(TRUNK_TONES))

    # 3-5 large flat leaves radiating outward
    num_leaves = rng.randint(3, 5)
    for _ in range(num_leaves):
        angle = rng.uniform(0, 2 * math.pi)
        leaf_len = rng.randint(4, 8)
        leaf_width = rng.randint(2, 4)
        fdx = math.cos(angle)
        fdy = math.sin(angle)
        # Perpendicular for leaf width
        pdx, pdy = -fdy, fdx

        for step in range(leaf_len):
            # Leaf rises gently
            lz = stem_h + max(0, step // 2 - 1)
            cx = int(round(x + fdx * (step + 1)))
            cy = int(round(y + fdy * (step + 1)))
            # Draw leaf width
            half_w = leaf_width // 2
            # Wider in the middle, narrower at tip
            w = half_w if step < leaf_len * 0.7 else max(0, half_w - 1)
            for pw in range(-w, w + 1):
                lx = int(round(cx + pdx * pw))
                ly = int(round(cy + pdy * pw))
                if 0 <= lx <= max_x and 0 <= ly <= max_y and 0 <= lz <= max_z:
                    c = rng.choice(G_BRIGHT if step < leaf_len // 2 else G_MID)
                    model.set(lx, ly, lz, c)


def _build_understory(model, x, y, max_h, rng, max_x=255, max_y=255, max_z=255):
    """Build understory plant — randomly picks from several types to fill vertical space."""
    if max_h < 3:
        return
    choice = rng.random()
    if choice < 0.15:
        # Palm tree — tall, distinct silhouette
        _build_palm(model, x, y, max_h, rng, max_x, max_y, max_z)
        return
    elif choice < 0.30:
        # Giant tree fern — fountain shape, fills mid-height
        _build_giant_fern(model, x, y, rng, max_x, max_y, max_z)
        return
    elif choice < 0.42:
        _build_broad_leaf_plant(model, x, y, rng, max_x, max_y, max_z)
        return
    elif choice < 0.55:
        # Low bush
        bush_max = min(12, max_h - 2)
        if bush_max < 3:
            bush_max = 3
        height = rng.randint(3, bush_max)
        if height < 3:
            return
        pal = rng.choice(CANOPY_PALETTES)
        r = rng.uniform(3, 6)
        _leaf_cluster(model, x, y, height, r, pal, rng,
                      max_x=max_x, max_y=max_y, max_z=max_z)
        return

    # Standard understory tree — trunk width scales with height
    if max_h < 18:
        # Too short for a tree, just make a bush
        r = rng.uniform(2, min(4, max_h - 1))
        _leaf_cluster(model, x, y, 1, r, rng.choice(CANOPY_PALETTES), rng,
                      max_x=max_x, max_y=max_y, max_z=max_z)
        return
    height = rng.randint(max(5, max_h // 6), max_h - 3)
    if height < 5:
        return

    # 2x2 trunk for tall, 1x1 for short
    use_2x2 = height >= 25
    lean_dx = rng.uniform(-0.1, 0.1)
    lean_dy = rng.uniform(-0.1, 0.1)
    fx, fy = float(x), float(y)
    for z in range(height):
        ix, iy = int(round(fx)), int(round(fy))
        if use_2x2:
            for ddx in range(2):
                for ddy in range(2):
                    px, py = ix + ddx, iy + ddy
                    if 0 <= px <= max_x and 0 <= py <= max_y:
                        model.set(px, py, z, rng.choice(TRUNK_TONES))
        else:
            if 0 <= ix <= max_x and 0 <= iy <= max_y:
                model.set(ix, iy, z, rng.choice(TRUNK_TONES))
        fx += lean_dx + rng.uniform(-0.04, 0.04)
        fy += lean_dy + rng.uniform(-0.04, 0.04)
    # Yellow-green palette for understory contrast
    pal = ([LEAF_YELLOW_1, LEAF_FRESH_1, LEAF_BRIGHT_1],
           [LEAF_YELLOW_2, LEAF_FRESH_2, LEAF_BRIGHT_2],
           [LEAF_YELLOW_1, LEAF_FRESH_1, LEAF_BRIGHT_3])
    r = rng.uniform(3, 6)
    tip_x, tip_y = int(round(fx)), int(round(fy))
    _leaf_cluster(model, tip_x, tip_y, height, r, pal, rng,
                  max_x=max_x, max_y=max_y, max_z=max_z)


def _scatter_flowers(model, width, depth, rng, max_z=6):
    """Scatter red flower clusters — larger, obvious pops of color."""
    count = (width * depth) // 500
    red_tones = [FLOWER_RED_1, FLOWER_RED_2]
    for _ in range(count):
        fx = rng.randint(3, width - 4)
        fy = rng.randint(3, depth - 4)
        fz = rng.randint(1, min(4, max_z))
        # 3-6 red blooms in a cluster for a visible pop
        num_blooms = rng.randint(3, 6)
        for _ in range(num_blooms):
            bx = fx + rng.randint(-2, 2)
            by = fy + rng.randint(-2, 2)
            bz = fz + rng.randint(0, 2)
            if 0 <= bx < width and 0 <= by < depth and 0 <= bz <= max_z:
                model.set(bx, by, bz, rng.choice(red_tones))
        # Dark green leaves surrounding the cluster
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                lx, ly = fx + dx, fy + dy
                if 0 <= lx < width and 0 <= ly < depth:
                    if rng.random() < 0.3 and not model.has(lx, ly, fz):
                        model.set(lx, ly, fz, rng.choice(G_DARK))


def _fill_ground_cover(model, width, depth, rng, max_z=3):
    """Dense ground cover: eden clusters, broad-leaf plants, giant ferns, flowers."""
    # Floor shade palette — darker blue-greens for understory shadow
    floor_pal = (G_DARK, G_DARK, [LEAF_DARK_1, LEAF_DARK_2, LEAF_DARK_3, LEAF_BLUE_2, LEAF_BLUE_3])
    # Eden clusters for base layer — use dark shade tones
    count = (width * depth) // 20
    for _ in range(count):
        cx = rng.randint(2, width - 3)
        cy = rng.randint(2, depth - 3)
        cz = rng.randint(1, min(4, max_z))
        r = rng.uniform(2.0, 4.0)
        _leaf_cluster(model, cx, cy, cz, r, floor_pal, rng,
                      max_x=width - 1, max_y=depth - 1, max_z=max_z)
    # Broad-leaf plants (elephant ears, monstera) — break up the uniform texture
    num_broad = (width * depth) // 300
    for _ in range(num_broad):
        bx = rng.randint(3, width - 4)
        by = rng.randint(3, depth - 4)
        _build_broad_leaf_plant(model, bx, by, rng,
                               max_x=width - 1, max_y=depth - 1, max_z=max_z)
    # Small ground ferns
    num_ferns = (width * depth) // 500
    for _ in range(num_ferns):
        fx = rng.randint(3, width - 4)
        fy = rng.randint(3, depth - 4)
        _build_giant_fern(model, fx, fy, rng,
                         max_x=width - 1, max_y=depth - 1, max_z=max_z)
    # Flowers
    _scatter_flowers(model, width, depth, rng, max_z=max_z)


def _fill_ground_layer(model, width, depth, rng, tones=None, hill_height=0,
                        hill_cx=None, hill_cy=None, hill_radius=None):
    """Fill ground with leaf litter. If hill_height > 0, creates elevated terrain."""
    if tones is None:
        tones = EARTH_TONES
    if hill_cx is None:
        hill_cx = width / 2
    if hill_cy is None:
        hill_cy = depth / 2
    if hill_radius is None:
        hill_radius = max(width, depth) / 2

    for x in range(width):
        for y in range(depth):
            # Hill elevation
            if hill_height > 0:
                dist = math.sqrt((x - hill_cx) ** 2 + (y - hill_cy) ** 2)
                t = max(0.0, 1.0 - dist / hill_radius)
                elevation = int(hill_height * t * t)  # quadratic mound
            else:
                elevation = 0

            # Fill from z=0 to elevation with earth
            for z in range(elevation + 1):
                r = rng.random()
                if z == elevation:
                    # Top surface: dark leaf litter (no bright moss)
                    if r < 0.35:
                        model.set(x, y, z, rng.choice(G_DARK))
                    elif r < 0.45:
                        model.set(x, y, z, rng.choice(G_DARK))
                    else:
                        model.set(x, y, z, rng.choice(tones))
                else:
                    model.set(x, y, z, rng.choice(tones))


# ============================================================
# Part 2: Ground tiles
# ============================================================

def build_ground_forest(seed=100):
    rng = random.Random(seed)
    m = VoxelModel()
    for x in range(32):
        for y in range(32):
            c = rng.choice(EARTH_TONES)
            if rng.random() < 0.08:
                c = rng.choice(MOSS_TONES)
            m.set(x, y, 0, c)
    return m


def build_ground_clearing(seed=200):
    rng = random.Random(seed)
    m = VoxelModel()
    for x in range(32):
        for y in range(32):
            c = rng.choice(CLEARING_TONES)
            if rng.random() < 0.05:
                c = rng.choice([LEAF_DARK_1, LEAF_DARK_2, MOSS_5])
            m.set(x, y, 0, c)
    return m


# ============================================================
# Part 3: Boardwalk segment
# ============================================================

def build_boardwalk(seed=300):
    rng = random.Random(seed)
    m = VoxelModel()

    # Support posts (z=0-2): 4 posts at corners and center
    post_positions = [(2, 2), (2, 29), (29, 2), (29, 29), (15, 15), (16, 16)]
    for px, py in post_positions:
        for z in range(3):
            m.set(px, py, z, rng.choice(BOARDWALK_TONES))
            m.set(px + 1, py, z, rng.choice(BOARDWALK_TONES))

    # Deck planks at z=3-4
    # Planks run along x-axis, with joints every 4 voxels along y
    for y in range(32):
        plank_tones = streak(BOARDWALK_TONES, 32, rng)
        is_joint = (y % 4 == 0)
        for x in range(32):
            # Random missing plank for rickety feel
            if rng.random() < 0.02:
                continue
            if is_joint:
                c = rng.choice([BARK_DARK_1, BARK_DARK_2])
            else:
                c = plank_tones[x]
            # Slight z variation for rickety feel
            z_base = 3
            if rng.random() < 0.08:
                z_base = 4
            m.set(x, y, z_base, c)
            if z_base == 3:
                m.set(x, y, 4, c)

    return m


# ============================================================
# Part 4: Tiki torch
# ============================================================

def build_tiki_torch(seed=400):
    rng = random.Random(seed)
    m = VoxelModel()
    materials = get_materials()
    for mat_id, props in materials.items():
        m.set_material(mat_id, props)

    pole_height = 22

    # Bamboo pole: 2x2, with ring bands
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
                m.set(2 + dx, 2 + dy, z, tone)

    # Rope binding near top
    for z in [pole_height - 4, pole_height - 3]:
        for dx in range(-1, 3):
            for dy in range(-1, 3):
                if (dx in (-1, 2)) or (dy in (-1, 2)):
                    if 0 <= 2 + dx <= 5 and 0 <= 2 + dy <= 5:
                        m.set(2 + dx, 2 + dy, z, TORCH_ROPE)

    # Fire bowl at top: 4x4 open cup
    bowl_z = pole_height
    for dx in range(4):
        for dy in range(4):
            edge = (dx == 0 or dx == 3 or dy == 0 or dy == 3)
            if edge:
                m.set(1 + dx, 1 + dy, bowl_z, BAMBOO_DARK)
            else:
                # Emissive flame
                m.set(1 + dx, 1 + dy, bowl_z, rng.choice([TORCH_FLAME_1, TORCH_FLAME_2]))
    # Flame above bowl
    for dz in range(1, 3):
        for dx in range(1, 3):
            for dy in range(1, 3):
                m.set(1 + dx, 1 + dy, bowl_z + dz, rng.choice([TORCH_FLAME_1, TORCH_FLAME_2]))

    return m


# ============================================================
# Part 5: Jungle patches
# ============================================================

def _build_jungle_common(width, depth, max_z, seed,
                          num_tall_trees, tall_h_range, tall_w_range, tall_r_range,
                          num_mid_trees, mid_h_range, mid_w_range, mid_r_range,
                          num_understory, num_vines, num_ground_cover):
    """Shared jungle builder for all three density zones."""
    rng = random.Random(seed)
    m = VoxelModel()
    max_xi = width - 1
    max_yi = depth - 1

    # Ground layer
    _fill_ground_layer(m, width, depth, rng)

    all_canopy_positions = []
    trunk_positions = set()  # track xy to enforce spacing

    def _try_place_tree(h_range, w_range, r_range, num_branches, num_buttresses):
        for attempt in range(50):
            tx = rng.randint(8, max_xi - 8)
            ty = rng.randint(8, max_yi - 8)
            too_close = False
            for ex, ey in trunk_positions:
                if abs(tx - ex) + abs(ty - ey) < 14:
                    too_close = True
                    break
            if too_close:
                continue

            trunk_positions.add((tx, ty))
            h = rng.randint(h_range[0], h_range[1])
            h = min(h, max_z - 15)
            w = rng.randint(w_range[0], w_range[1])

            # Pick random bark/canopy palette for this tree
            bark = rng.choice(BARK_PALETTE_OPTIONS)
            canopy_pal = rng.choice(CANOPY_PALETTES)
            has_moss = rng.random() < 0.35  # ~35% of trees have mossy trunks

            path = _grow_trunk(m, tx, ty, h, w, rng, tones=bark,
                              max_x=max_xi, max_y=max_yi)

            # Moss on trunk
            if has_moss:
                _moss_on_trunk(m, path, w, rng, max_x=max_xi, max_y=max_yi)

            # Epiphytes (bromeliads, ferns on trunk) — ~40% of trees
            if rng.random() < 0.4:
                _add_epiphytes(m, path, w, rng,
                              max_x=max_xi, max_y=max_yi, max_z=max_z)

            # Buttress roots — bigger for taller trees
            directions = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)]
            rng.shuffle(directions)
            butt_h = max(5, h // 8)  # scale with tree height
            for bi in range(min(num_buttresses, len(directions))):
                ddx, ddy = directions[bi]
                _grow_buttress(m, tx, ty, 2, ddx * 0.7, ddy * 0.7, rng,
                              max_x=max_xi, max_y=max_yi, height=butt_h)

            # Build dome-shaped canopy from many small clusters
            if len(path) > 10:
                trunk_height = len(path)
                all_canopy_positions.extend(
                    _build_canopy_dome(m, path, trunk_height, bark, canopy_pal,
                                      r_range, rng, max_xi, max_yi, max_z)
                )

            return True
        return False

    # Tall/emergent trees
    for _ in range(num_tall_trees):
        _try_place_tree(tall_h_range, tall_w_range, tall_r_range,
                        rng.randint(3, 5), rng.randint(4, 6))

    # Medium canopy trees
    for _ in range(num_mid_trees):
        _try_place_tree(mid_h_range, mid_w_range, mid_r_range,
                        rng.randint(2, 4), rng.randint(2, 3))

    # Understory — fills the mid-air gap between canopy and floor
    for _ in range(num_understory):
        ux = rng.randint(3, max_xi - 3)
        uy = rng.randint(3, max_yi - 3)
        # Understory can be up to 60% of max height (fills the gap)
        _build_understory(m, ux, uy, min(60, int(max_z * 0.6)), rng,
                         max_x=max_xi, max_y=max_yi, max_z=max_z)

    # Vines
    _grow_vines(m, all_canopy_positions, rng, count=num_vines,
                max_x=max_xi, max_y=max_yi, max_z=max_z)

    # Ground cover
    _fill_ground_cover(m, width, depth, rng, max_z=min(5, max_z))

    return m


def build_jungle_low(seed=500):
    return _build_jungle_common(
        width=128, depth=128, max_z=52, seed=seed,
        num_tall_trees=0, tall_h_range=(0, 0), tall_w_range=(0, 0), tall_r_range=(0, 0),
        num_mid_trees=0, mid_h_range=(0, 0), mid_w_range=(0, 0), mid_r_range=(0, 0),
        num_understory=60, num_vines=0, num_ground_cover=80,
    )


def build_jungle_mid(seed=600):
    return _build_jungle_common(
        width=128, depth=128, max_z=130, seed=seed,
        num_tall_trees=0, tall_h_range=(0, 0), tall_w_range=(0, 0), tall_r_range=(0, 0),
        num_mid_trees=12, mid_h_range=(30, 100), mid_w_range=(2, 4), mid_r_range=(7, 10),
        num_understory=50, num_vines=12, num_ground_cover=60,
    )


def build_jungle_tall(seed=700):
    return _build_jungle_common(
        width=128, depth=128, max_z=235, seed=seed,
        num_tall_trees=3, tall_h_range=(160, 220), tall_w_range=(4, 6), tall_r_range=(9, 14),
        num_mid_trees=15, mid_h_range=(30, 120), mid_w_range=(2, 4), mid_r_range=(7, 10),
        num_understory=50, num_vines=20, num_ground_cover=70,
    )


# ============================================================
# Part 6: Snake skull
# ============================================================

def _sdf_ellipsoid(px, py, pz, cx, cy, cz, rx, ry, rz):
    """Signed distance to ellipsoid surface (approximate)."""
    dx = (px - cx) / max(rx, 0.01)
    dy = (py - cy) / max(ry, 0.01)
    dz = (pz - cz) / max(rz, 0.01)
    d = math.sqrt(dx * dx + dy * dy + dz * dz)
    # Approximate SDF
    r_min = min(rx, ry, rz)
    return (d - 1.0) * r_min


def _sdf_smooth_union(a, b, k=4.0):
    h = max(0.0, min(1.0, 0.5 + 0.5 * (b - a) / k))
    return a * h + b * (1 - h) - k * h * (1 - h)


def _bone_color(px, py, pz, rng, skull_bottom):
    """Choose bone color with aging gradient and cracks."""
    # Darker toward bottom
    height_frac = max(0, min(1, (pz - skull_bottom) / 80))
    if rng.random() < 0.04:
        return BONE_CRACK
    if height_frac < 0.2:
        return rng.choice([BONE_SHADOW, BONE_DARK, BONE_AGED_3])
    elif height_frac < 0.5:
        return rng.choice([BONE_MID, BONE_DARK, BONE_AGED_1, BONE_AGED_2])
    else:
        return rng.choice([BONE_BASE, BONE_LIGHT, BONE_MID, BONE_AGED_1])


def build_skull(seed=800):
    """Build a giant snake skull using cross-section lofting for a recognizable shape.

    Snake skulls are: very flat (low z), elongated (+x), triangular from above
    (wide at back, narrow at snout), with clearly separated upper/lower jaws,
    large eye sockets on the sides, and prominent fangs.

    Orientation: snout points toward +x (toward isometric camera).
    """
    rng = random.Random(seed)
    m = VoxelModel()

    # Ground layer under skull
    for x in range(128):
        for y in range(96):
            m.set(x, y, 0, rng.choice(EARTH_TONES))

    skull_bottom = 30  # elevated so skull is visible above surrounding forest

    # --- Cross-section lofting approach ---
    # Define skull as a series of cross-sections along x-axis.
    # Each section: (x_pos, half_width_y, height_z, z_center_offset, is_jaw_open)
    # x=0 is back of cranium, x increases toward snout tip.
    # Build upper skull and lower jaw separately.

    skull_length = 105  # total length along x
    cranium_length = 40  # back portion (rounded braincase)
    snout_length = 65   # front portion (narrows to tip)

    def _upper_profile(x_local):
        """Returns (half_width_y, half_height_z, z_center) for upper skull at x."""
        if x_local < 0 or x_local > skull_length:
            return (0, 0, 0)
        t = x_local / skull_length  # 0=back, 1=tip

        if x_local <= cranium_length:
            # Braincase: wide, tall dome
            ct = x_local / cranium_length  # 0=very back, 1=front of cranium
            # Width: oval, widest at ct=0.5
            half_w = int(28 * math.sin(ct * math.pi) + 2) if ct < 1 else 18
            # Height: dome profile
            half_h = int(18 * math.sin(ct * math.pi * 0.8) + 3)
            z_c = skull_bottom + half_h + 8
        else:
            # Snout: triangular taper
            st = (x_local - cranium_length) / snout_length  # 0=cranium junction, 1=tip
            half_w = int(18 * (1 - st * 0.85) + 2)
            half_h = int(10 * (1 - st * 0.5) + 2)
            # Snout slopes downward slightly toward front
            z_c = skull_bottom + half_h + 8 - int(st * 8)

        return (half_w, half_h, z_c)

    def _lower_jaw_profile(x_local):
        """Returns (half_width_y, half_height_z, z_center) for lower jaw at x.
        Lower jaw starts at cranium front, extends forward, hangs open."""
        jaw_start = cranium_length - 5
        jaw_length = 70
        if x_local < jaw_start or x_local > jaw_start + jaw_length:
            return (0, 0, 0)
        jt = (x_local - jaw_start) / jaw_length  # 0=back, 1=front

        half_w = int(16 * (1 - jt * 0.8) + 2)
        half_h = max(2, int(5 * (1 - jt * 0.5)))
        # Jaw hangs down and forward — drops more toward back, less toward tip
        # The gap between upper and lower jaw creates the "open mouth"
        z_c = skull_bottom + 4 - int((1 - jt) * 3)

        return (half_w, half_h, z_c)

    # Shell thickness
    shell = 2

    # Voxelize upper skull
    for x_local in range(skull_length + 1):
        x = 10 + x_local  # offset in model space
        hw, hh, zc = _upper_profile(x_local)
        if hw <= 0 or hh <= 0:
            continue

        cy = 48  # center y in model
        for dy in range(-hw, hw + 1):
            for dz in range(-hh, hh + 1):
                y = cy + dy
                z = zc + dz
                if not (0 <= y < 96 and 0 <= z < 160):
                    continue
                # Ellipse test
                ey = (dy / max(hw, 1)) ** 2
                ez = (dz / max(hh, 1)) ** 2
                dist = ey + ez
                if dist <= 1.0:
                    # Shell: only place if near surface
                    inner_hw = max(0, hw - shell)
                    inner_hh = max(0, hh - shell)
                    if inner_hw > 0 and inner_hh > 0:
                        inner_ey = (dy / inner_hw) ** 2
                        inner_ez = (dz / inner_hh) ** 2
                        if inner_ey + inner_ez < 1.0:
                            continue  # hollow interior
                    m.set(x, y, z, _bone_color(x, y, z, rng, skull_bottom))

    # Voxelize lower jaw
    for x_local in range(skull_length + 1):
        x = 10 + x_local
        hw, hh, zc = _lower_jaw_profile(x_local)
        if hw <= 0 or hh <= 0:
            continue

        cy = 48
        for dy in range(-hw, hw + 1):
            for dz in range(-hh, hh + 1):
                y = cy + dy
                z = zc + dz
                if not (0 <= y < 96 and 0 <= z < 160):
                    continue
                ey = (dy / max(hw, 1)) ** 2
                ez = (dz / max(hh, 1)) ** 2
                dist = ey + ez
                if dist <= 1.0:
                    inner_hw = max(0, hw - shell)
                    inner_hh = max(0, hh - shell)
                    if inner_hw > 0 and inner_hh > 0:
                        inner_ey = (dy / inner_hw) ** 2
                        inner_ez = (dz / inner_hh) ** 2
                        if inner_ey + inner_ez < 1.0:
                            continue
                    m.set(x, y, z, _bone_color(x, y, z, rng, skull_bottom))

    # --- Eye sockets: large holes on sides of cranium ---
    eye_x = 10 + cranium_length - 10  # near front of cranium
    eye_r_y = 10  # radius of socket
    eye_r_z = 8
    for side in [-1, 1]:
        eye_cy = 48 + side * 22
        eye_cz = skull_bottom + 18
        for dx in range(-eye_r_y, eye_r_y + 1):
            for dy in range(-eye_r_y, eye_r_y + 1):
                for dz in range(-eye_r_z, eye_r_z + 1):
                    ex = eye_x + dx
                    ey = eye_cy + dy
                    ez = eye_cz + dz
                    ed = (dx / max(eye_r_y, 1)) ** 2 + (dy / max(eye_r_y, 1)) ** 2 + (dz / max(eye_r_z, 1)) ** 2
                    if ed < 0.85:
                        m.delete(ex, ey, ez)

    # --- Nasal openings: two smaller holes at snout front ---
    nasal_x = 10 + skull_length - 10
    nasal_r = 4
    for side in [-1, 1]:
        nasal_cy = 48 + side * 5
        nasal_cz = skull_bottom + 6
        for dx in range(-nasal_r, nasal_r + 1):
            for dy in range(-nasal_r, nasal_r + 1):
                for dz in range(-nasal_r, nasal_r + 1):
                    ed = (dx / nasal_r) ** 2 + (dy / nasal_r) ** 2 + (dz / nasal_r) ** 2
                    if ed < 0.8:
                        m.delete(nasal_x + dx, nasal_cy + dy, nasal_cz + dz)

    # --- Temporal fenestrae: elongated holes on sides of cranium ---
    fen_x = 10 + cranium_length // 2
    fen_rx, fen_ry, fen_rz = 8, 4, 5
    for side in [-1, 1]:
        fen_cy = 48 + side * 25
        fen_cz = skull_bottom + 22
        for dx in range(-fen_rx, fen_rx + 1):
            for dy in range(-fen_ry, fen_ry + 1):
                for dz in range(-fen_rz, fen_rz + 1):
                    ed = (dx / fen_rx) ** 2 + (dy / fen_ry) ** 2 + (dz / fen_rz) ** 2
                    if ed < 0.8:
                        m.delete(fen_x + dx, fen_cy + dy, fen_cz + dz)

    # --- Fangs: large curved teeth hanging from upper jaw ---
    for side in [-1, 1]:
        fang_x = 10 + skull_length - 25
        fang_y = 48 + side * 8
        fang_base_z = skull_bottom + 3
        fang_len = 25
        for fz in range(fang_len):
            z = fang_base_z - fz
            if z < 1:
                break
            # Curve forward as it descends
            fx_offset = int(fz * 0.15)
            # Taper from 3x3 at base to 1x1 at tip
            progress = fz / fang_len
            if progress < 0.3:
                half = 1
            elif progress < 0.7:
                half = 1
            else:
                half = 0
            for dx in range(-half, half + 1):
                for dy in range(-half, half + 1):
                    px = fang_x + fx_offset + dx
                    py = fang_y + dy
                    if 0 <= px < 128 and 0 <= py < 96:
                        tone = FANG_TIP if progress > 0.7 else (FANG_MID if progress > 0.3 else FANG_BASE)
                        m.set(px, py, z, tone)

    # --- Smaller teeth along jaw edges ---
    for side in [-1, 1]:
        for tooth_i in range(6):
            tooth_x = 10 + cranium_length + tooth_i * 8
            tooth_y = 48 + side * int(16 * (1 - tooth_i * 0.1))
            tooth_base_z = skull_bottom + 3
            tooth_len = rng.randint(6, 10)
            for tz in range(tooth_len):
                z = tooth_base_z - tz
                if z < 1:
                    break
                tone = FANG_TIP if tz > tooth_len * 0.6 else FANG_MID
                m.set(tooth_x, tooth_y, z, tone)
                if tz < tooth_len // 2:
                    m.set(tooth_x, tooth_y + side, z, tone)

    # --- Moss overgrowth on skull surface ---
    skull_voxels = [p for p in m._v.keys() if p[2] > skull_bottom + 10]
    top_voxels = sorted(skull_voxels, key=lambda p: p[2], reverse=True)[:200]
    for _ in range(12):
        if not top_voxels:
            break
        seed_pos = rng.choice(top_voxels)
        r = rng.uniform(3, 6)
        _leaf_cluster(m, seed_pos[0], seed_pos[1], seed_pos[2] + 1, r,
                      ([MOSS_1, MOSS_2, MOSS_3], [MOSS_4, MOSS_5, MOSS_6], [MOSS_7, MOSS_8, LEAF_DARK_3]),
                      rng, max_x=127, max_y=95, max_z=159)

    # --- Vine drapes from cranium top ---
    for _ in range(6):
        vx = rng.randint(15, 10 + cranium_length)
        vy = rng.choice([48 - 20, 48 + 20])
        vz_start = skull_bottom + 25
        # Find actual top at this position
        for check_z in range(40, skull_bottom, -1):
            if m.has(vx, vy, check_z):
                vz_start = check_z
                break
        vine_len = rng.randint(15, 30)
        fx, fy, fz = float(vx), float(vy), float(vz_start)
        for _ in range(vine_len):
            ix, iy, iz = int(round(fx)), int(round(fy)), int(round(fz))
            if 0 <= ix < 128 and 0 <= iy < 96 and iz > 0:
                m.set(ix, iy, iz, rng.choice(VINE_TONES))
            fx += rng.uniform(-0.3, 0.3)
            fy += rng.uniform(-0.2, 0.2)
            fz -= 1.0

    return m


# ============================================================
# Part 7: Arcade machine
# ============================================================

def build_arcade(seed=900):
    rng = random.Random(seed)
    m = VoxelModel()
    materials = get_materials()
    for mat_id, props in materials.items():
        m.set_material(mat_id, props)

    # Ground
    for x in range(32):
        for y in range(32):
            m.set(x, y, 0, rng.choice(EARTH_TONES))

    cx, cy = 16, 16  # center

    # Base platform (wider): 24x24x4 — concrete pad in the jungle
    for x in range(cx - 12, cx + 12):
        for y in range(cy - 12, cy + 12):
            for z in range(1, 5):
                edge = (x == cx - 12 or x == cx + 11 or y == cy - 12 or y == cy + 11)
                m.set(x, y, z, STONE_MID if edge else STONE_LIGHT)

    # Cabinet body: 18x18x52 — bigger and more imposing
    body_z_start = 5
    body_z_end = 57
    for x in range(cx - 9, cx + 9):
        for y in range(cy - 9, cy + 9):
            for z in range(body_z_start, body_z_end):
                edge = (x == cx - 9 or x == cx + 8 or y == cy - 9 or y == cy + 8)
                if edge:
                    m.set(x, y, z, ARCADE_TRIM if z % 10 == 0 else ARCADE_BODY)
                else:
                    m.set(x, y, z, ARCADE_BODY_2)

    # Trim strips top and bottom
    for x in range(cx - 9, cx + 9):
        for y in range(cy - 9, cy + 9):
            m.set(x, y, body_z_start, ARCADE_TRIM)
            m.set(x, y, body_z_start + 1, ARCADE_TRIM_2)
            m.set(x, y, body_z_end - 1, ARCADE_TRIM)
            m.set(x, y, body_z_end - 2, ARCADE_TRIM_2)

    # Screen face (on the +x side, facing isometric camera)
    screen_z_bot = 32
    screen_z_top = 54
    screen_x = cx + 8
    # Screen bezel
    for y in range(cy - 8, cy + 8):
        for z in range(screen_z_bot - 1, screen_z_top + 1):
            m.set(screen_x, y, z, ARCADE_BODY)
    # Screen area
    for y in range(cy - 7, cy + 7):
        for z in range(screen_z_bot, screen_z_top):
            m.set(screen_x, y, z, SCREEN_BG)

    # Snake body on screen: zigzag pattern (thicker, 2 voxels)
    snake_positions = list(range(cy - 6, cy + 6))
    sz = screen_z_bot + 5
    direction = 1
    for i, sy in enumerate(snake_positions):
        m.set(screen_x, sy, sz, SCREEN_BRIGHT)
        m.set(screen_x, sy, sz + 1, SCREEN_BRIGHT)
        if i % 3 == 2:
            sz += direction * 3
            direction *= -1
            sz = max(screen_z_bot + 3, min(screen_z_top - 4, sz))

    # Food dots
    m.set(screen_x, cy + 4, screen_z_bot + 10, SCREEN_PIXEL)
    m.set(screen_x, cy - 3, screen_z_bot + 6, SCREEN_PIXEL)

    # Score text area at top of screen
    for y in range(cy - 6, cy + 6):
        m.set(screen_x, y, screen_z_top - 2, SCREEN_DARK)
        m.set(screen_x, y, screen_z_top - 3, SCREEN_DARK)
    # Score digits
    for y in range(cy - 4, cy + 4, 2):
        m.set(screen_x, y, screen_z_top - 2, SCREEN_BRIGHT)

    # Control panel (z=26-31)
    panel_z = 26
    for x in range(cx - 7, cx + 7):
        for y in range(cy - 7, cy + 7):
            for dz in range(3):
                m.set(x, y, panel_z + dz, ARCADE_BODY_2)
    # Panel top surface
    for x in range(cx - 6, cx + 6):
        for y in range(cy - 6, cy + 6):
            m.set(x, y, panel_z + 3, ARCADE_BODY)

    # Joystick (taller)
    for dz in range(1, 5):
        m.set(cx + 4, cy, panel_z + 3 + dz, ARCADE_TRIM)
    m.set(cx + 4, cy, panel_z + 8, ARCADE_TRIM_2)  # ball top
    m.set(cx + 4, cy + 1, panel_z + 8, ARCADE_TRIM_2)

    # Buttons (bigger)
    btn_y_offsets = [-4, 0, 4]
    btn_colors = [ARCADE_BTN_RED, ARCADE_BTN_BLUE, ARCADE_BTN_YEL]
    for dy, bc in zip(btn_y_offsets, btn_colors):
        bx = cx + 1
        by = cy + dy
        for ddx in range(3):
            for ddy in range(3):
                if ddx * ddx + ddy * ddy <= 2:
                    m.set(bx + ddx, by + ddy, panel_z + 4, bc)

    # Coin slot on side
    slot_y = cy - 9
    for z in range(20, 26):
        m.set(cx, slot_y, z, ARCADE_COIN)
        m.set(cx + 1, slot_y, z, ARCADE_COIN)

    # Marquee at top — wider overhang, emissive
    marquee_z = body_z_end
    for x in range(cx - 10, cx + 10):
        for y in range(cy - 10, cy + 10):
            for z in range(marquee_z, marquee_z + 7):
                edge = (x == cx - 10 or x == cx + 9 or y == cy - 10 or y == cy + 9)
                if z == marquee_z or z == marquee_z + 6:
                    m.set(x, y, z, ARCADE_TRIM)
                elif edge:
                    m.set(x, y, z, ARCADE_TRIM_2)
                else:
                    m.set(x, y, z, ARCADE_BODY)

    # Marquee lettering on both visible faces (+x and +y for isometric visibility)
    for face_x, face_y_range in [(cx + 9, range(cy - 5, cy + 6)),
                                  (cx + 9, range(cy - 5, cy + 6))]:
        for y in face_y_range:
            m.set(face_x, y, marquee_z + 3, SCREEN_BRIGHT)
            m.set(face_x, y, marquee_z + 4, SCREEN_BRIGHT)

    # Also on the +y face
    for x in range(cx - 5, cx + 6):
        m.set(x, cy + 9, marquee_z + 3, SCREEN_BRIGHT)
        m.set(x, cy + 9, marquee_z + 4, SCREEN_BRIGHT)

    return m


def build_arcade_cabinet(seed=950, include_floor=True):
    """Build a 48x48x96 jungle-themed Snake arcade cabinet.

    Classic Polybius-style upright cabinet: tall, narrow.
    The cabinet body is ~24 deep (x) x 24 wide (y), centered at (24,24).
    Screen faces -x and -y for isometric visibility.

    Vertical layout (z):
      0-1   stone floor pad (48x48)  [z=0 omitted when include_floor=False]
      2-3   plinth / base trim
      4-34  lower body (coin door area)
      35-36 trim band
      37-44 control panel zone (shelf juts forward)
      45-76 upper body (screen area, slightly recessed back)
      77-78 trim band (top of body)
      79-90 marquee header (overhangs front and sides)
    """
    rng = random.Random(seed)
    m = VoxelModel()
    materials = get_materials()
    for mat_id, props in materials.items():
        m.set_material(mat_id, props)

    cx, cy = 24, 24

    # Cabinet footprint — 41 deep (x) x 40 wide (y), shifted back 1 for sign
    cab_hx, cab_hy = 19, 20
    x1 = cx - cab_hx + 2      # 7 (back 2 from original)
    x2 = cx + cab_hx + 4      # 47
    y1, y2 = cy - cab_hy, cy + cab_hy   # 4..44

    # Ensure equal x/y bounding box
    m.set(0, 0, 0, ARCADE_BODY)
    m.set(47, 47, 0, ARCADE_BODY)

    # ------------------------------------------------------------------
    # CABINET BODY — three pieces to create a recessed screen area
    # ------------------------------------------------------------------
    screen_recess = 6
    panel_top_z = 37  # where the lower cuboid ends

    # 1. Lower cuboid: z=0 to panel_top_z-1, full depth
    for z in range(0, panel_top_z):
        for x in range(x1, x2):
            for y in range(y1, y2):
                edge = (x == x1 or x == x2 - 1 or y == y1 or y == y2 - 1)
                m.set(x, y, z, ARCADE_BODY if edge else ARCADE_BODY_2)

    # 2. Side boards: z=panel_top_z to 78, full depth, 1 voxel thick on each side
    board_w = 1
    for z in range(panel_top_z, 79):
        for x in range(x1, x2):
            m.set(x, y1, z, ARCADE_BODY)
            m.set(x, y2 - 1, z, ARCADE_BODY)

    # 3. Upper cuboid: z=panel_top_z to 78, recessed from front
    for z in range(panel_top_z, 79):
        for x in range(x1 + screen_recess, x2):
            for y in range(y1 + board_w, y2 - board_w):
                edge = (x == x1 + screen_recess or x == x2 - 1 or
                        y == y1 + board_w or y == y2 - board_w - 1)
                m.set(x, y, z, ARCADE_BODY if edge else ARCADE_BODY_2)


    # ------------------------------------------------------------------
    # RIM — 1-voxel protrusion at left/right edges of each face
    # ------------------------------------------------------------------
    def _add_rim_to_box(bx1, bx2, by1, by2, bz1, bz2, z_top=None):
        """Add 1-voxel rim protrusions on forward-facing (-x) face and top only.

        -x face: left/right edges protrude 1 voxel forward (-x).
        Top face: left/right edges protrude 1 voxel upward (+z).
        Vertical rims run from bz1 to bz2 (can extend beyond for convex corners).
        z_top overrides where horizontal top rim goes (defaults to surface level).
        """
        def _s(x, y, z, c):
            if 0 <= x <= 47 and 0 <= y <= 47 and 0 <= z <= 255:
                m.set(x, y, z, c)

        rim_color = ARCADE_TRIM
        for z in range(bz1, bz2):
            _s(bx1 - 1, by1, z, rim_color)
            _s(bx1 - 1, by2 - 1, z, rim_color)
            _s(bx2, by1, z, rim_color)
            _s(bx2, by2 - 1, z, rim_color)
        if z_top is not None:
            for x in range(bx1, bx2):
                _s(x, by1, z_top, rim_color)
                _s(x, by2 - 1, z_top, rim_color)

    # Rim on main body
    _add_rim_to_box(x1, x2, y1, y2, 0, 80, z_top=79)

    # ------------------------------------------------------------------
    # COIN DOOR  z=8-32 on -x face
    # ------------------------------------------------------------------
    coin_x = x1  # front face surface
    coin_y1, coin_y2 = y1 + 3, y2 - 3
    # Recessed panel background (inset behind the rim)
    for y in range(coin_y1, coin_y2):
        for z in range(8, 33):
            m.set(coin_x, y, z, ARCADE_BODY_2)
    # Trim border
    for y in range(coin_y1, coin_y2):
        m.set(coin_x, y, 8, ARCADE_TRIM)
        m.set(coin_x, y, 32, ARCADE_TRIM)
    for z in range(8, 33):
        m.set(coin_x, coin_y1, z, ARCADE_TRIM)
        m.set(coin_x, coin_y2 - 1, z, ARCADE_TRIM)
    # Coin slot — vertical metallic rectangle with dark entry/exit
    slot_y1, slot_y2 = cy - 3, cy + 3
    slot_z1, slot_z2 = 14, 26
    for y in range(slot_y1, slot_y2):
        for z in range(slot_z1, slot_z2):
            m.set(coin_x, y, z, ARCADE_COIN)
    # Dark coin entry slit (top)
    for y in range(cy - 1, cy + 1):
        for z in range(slot_z2 - 3, slot_z2 - 1):
            m.set(coin_x, y, z, ARCADE_BODY)
    # Dark coin exit slit (bottom)
    for y in range(cy - 1, cy + 1):
        for z in range(slot_z1 + 1, slot_z1 + 3):
            m.set(coin_x, y, z, ARCADE_BODY)
    # Red coin-return button — 2 wide × 3 tall (rotated 90°)
    for dy in range(0, 2):
        for dz in range(0, 3):
            m.set(coin_x, cy + dy - 1, 28 + dz, ARCADE_BTN_RED)

    # ------------------------------------------------------------------
    # CONTROL PANEL  z=37-42, flat shelf jutting forward from -x face
    # ------------------------------------------------------------------
    cp_depth = 14  # extended 6 more toward screen
    cp_x1 = max(1, x1 - cp_depth)  # leave 1 voxel for rim
    cp_y1, cp_y2 = y1, y2

    # Solid shelf block — extends from cp_x1 through the recess to x1+screen_recess
    cp_x2 = x1 + screen_recess  # inner edge of shelf
    for x in range(cp_x1, cp_x2):
        for y in range(cp_y1, cp_y2):
            for z in range(37, 42):
                edge = (x == cp_x1 or y == cp_y1 or y == cp_y2 - 1 or z == 37)
                m.set(x, y, z, ARCADE_TRIM if (z == 37) else
                      (ARCADE_BODY if edge else ARCADE_BODY_2))
    # Flat top surface
    panel_z = 42
    for x in range(cp_x1, cp_x2):
        for y in range(cp_y1, cp_y2):
            m.set(x, y, panel_z, ARCADE_BODY)

    # Rim on control panel shelf (vertical extends 1 beyond for convex corners)
    _add_rim_to_box(cp_x1, cp_x2, cp_y1, cp_y2, 36, 44, z_top=43)

    # Rim on underside of control panel — left/right edges protrude 1 voxel down
    for x in range(cp_x1, cp_x2):
        m.set(x, cp_y1, 36, ARCADE_TRIM)
        m.set(x, cp_y2 - 1, 36, ARCADE_TRIM)

    # Joystick on right side (high y) — red ball top on metallic shaft
    jx, jy = cp_x1 + 3, cy + 5
    for dz in range(1, 5):
        m.set(jx, jy, panel_z + dz, ARCADE_TRIM)
    # Red ball top — plus shape (5 voxels)
    m.set(jx, jy, panel_z + 5, ARCADE_BTN_RED)
    m.set(jx + 1, jy, panel_z + 5, ARCADE_BTN_RED)
    m.set(jx - 1, jy, panel_z + 5, ARCADE_BTN_RED)
    m.set(jx, jy + 1, panel_z + 5, ARCADE_BTN_RED)
    m.set(jx, jy - 1, panel_z + 5, ARCADE_BTN_RED)
    # 1 more pixel on top
    m.set(jx, jy, panel_z + 6, ARCADE_BTN_RED)

    # Two red buttons on left side (low y)
    for dy in [-6, -2]:
        bx, by = cp_x1 + 3, cy + dy
        for ddx in range(-1, 2):
            for ddy in range(-1, 2):
                if ddx * ddx + ddy * ddy <= 1:
                    m.set(bx + ddx, by + ddy, panel_z + 1, ARCADE_BTN_RED)

    # ------------------------------------------------------------------
    # SCREEN BEZEL + SCREEN on -x face  z=49-75
    # ------------------------------------------------------------------
    scr_x = x1 + screen_recess  # on the recessed face
    scr_z_bot, scr_z_top = 49, 75
    scr_y1, scr_y2 = y1 + board_w + 1, y2 - board_w - 1

    # Bezel (dark border, 1 voxel thick)
    for y in range(scr_y1 - 1, scr_y2 + 1):
        for z in range(scr_z_bot - 1, scr_z_top + 1):
            m.set(scr_x, y, z, ARCADE_BODY)
    # Trim ring around bezel
    for y in range(scr_y1 - 1, scr_y2 + 1):
        m.set(scr_x, y, scr_z_bot - 1, ARCADE_TRIM_2)
        m.set(scr_x, y, scr_z_top, ARCADE_TRIM_2)
    for z in range(scr_z_bot - 1, scr_z_top + 1):
        m.set(scr_x, scr_y1 - 1, z, ARCADE_TRIM_2)
        m.set(scr_x, scr_y2, z, ARCADE_TRIM_2)

    # Screen background (emissive dark green)
    for y in range(scr_y1, scr_y2):
        for z in range(scr_z_bot, scr_z_top):
            m.set(scr_x, y, z, SCREEN_BG)

    # Classic Nokia snake game snapshot
    # Border: 2 voxels in from screen edge
    border_inset = 2
    b_y1 = scr_y1 + border_inset
    b_y2 = scr_y2 - border_inset
    b_z1 = scr_z_bot + border_inset
    b_z2 = scr_z_top - border_inset

    # Draw border (1 pixel thick)
    for y in range(b_y1, b_y2):
        m.set(scr_x, y, b_z1, SCREEN_DARK)
        m.set(scr_x, y, b_z2 - 1, SCREEN_DARK)
    for z in range(b_z1, b_z2):
        m.set(scr_x, b_y1, z, SCREEN_DARK)
        m.set(scr_x, b_y2 - 1, z, SCREEN_DARK)

    # Play area inside border + 2 voxel gap
    gap_from_border = 2
    py1 = b_y1 + 1 + gap_from_border
    py2 = b_y2 - 1 - gap_from_border
    pz1 = b_z1 + 1 + gap_from_border
    pw = py2 - py1

    # Snake: 2 voxels thick, zigzag 2.25 times (2 full rows + quarter)
    row_h = 2
    row_gap = 1
    stride = row_h + row_gap
    snake_pixels = set()
    z_cursor = pz1

    # Row 1: right
    for y in range(py1, py2):
        for dz in range(row_h):
            snake_pixels.add((y, z_cursor + dz))
    # Turn up on right
    for dz in range(row_h, stride + row_h):
        for dy in range(row_h):
            snake_pixels.add((py2 - 1 - dy, z_cursor + dz))
    z_cursor += stride

    # Row 2: left
    for y in range(py1, py2):
        for dz in range(row_h):
            snake_pixels.add((y, z_cursor + dz))
    # Turn up on left
    for dz in range(row_h, stride + row_h):
        for dy in range(row_h):
            snake_pixels.add((py1 + dy, z_cursor + dz))
    z_cursor += stride

    # Row 3: right
    for y in range(py1, py2):
        for dz in range(row_h):
            snake_pixels.add((y, z_cursor + dz))
    # Turn up on right
    for dz in range(row_h, stride + row_h):
        for dy in range(row_h):
            snake_pixels.add((py2 - 1 - dy, z_cursor + dz))
    z_cursor += stride

    # Row 4 (quarter + head): left, partway
    head_len = pw // 4
    for y in range(py2 - 1, py2 - 1 - head_len, -1):
        for dz in range(row_h):
            snake_pixels.add((y, z_cursor + dz))
    # Head extends up a few voxels so it's visible in isometric
    head_y = py2 - 1 - head_len
    for dz in range(row_h, row_h + 3):
        for dy in range(row_h):
            snake_pixels.add((head_y + dy, z_cursor + dz))

    # Draw snake
    for sy, sz in snake_pixels:
        m.set(scr_x, sy, sz, SCREEN_DARK)

    # Food dot (2x2) just ahead of the head
    food_y = head_y - 3
    food_z = z_cursor + 2
    for dy in range(2):
        for dz in range(2):
            m.set(scr_x, food_y + dy, food_z + dz, SCREEN_DARK)

    # Score at top of screen
    score_z = scr_z_top - 3
    for dy in [3, 4, 7, 8, 11, 12, 15, 16]:
        m.set(scr_x, scr_y1 + dy, score_z, SCREEN_DARK)

    # ------------------------------------------------------------------
    # MARQUEE  z=79-90  (overhangs FRONT only, flush on back/sides)
    # ------------------------------------------------------------------
    mq_x1 = max(2, x1 - 5)  # overhang forward, leave space for sign
    mq_x2 = x2              # flush with back
    mq_y1 = y1              # flush with sides
    mq_y2 = y2
    for z in range(79, 91):
        for x in range(mq_x1, mq_x2):
            for y in range(mq_y1, mq_y2):
                edge = (x == mq_x1 or x == mq_x2 - 1 or
                        y == mq_y1 or y == mq_y2 - 1)
                if z == 79:
                    m.set(x, y, z, ARCADE_TRIM)
                else:
                    m.set(x, y, z, ARCADE_BODY)

    # Rim on marquee (vertical extends 1 beyond for convex corners)
    _add_rim_to_box(mq_x1, mq_x2, mq_y1, mq_y2, 78, 92, z_top=91)

    # Rim on underside of marquee overhang — left/right edges protrude 1 voxel down
    for x in range(mq_x1, x1):  # only the overhang portion
        m.set(x, mq_y1, 78, ARCADE_TRIM)
        m.set(x, mq_y2 - 1, 78, ARCADE_TRIM)

    # "SNAKE" LED sign on top of marquee — freestanding emissive letters
    import os
    from PIL import Image, ImageFont, ImageDraw
    font_path = os.path.expanduser('~/AppData/Local/Microsoft/Windows/Fonts/Silkscreen-Regular.ttf')
    font_size = 12
    font = ImageFont.truetype(font_path, font_size)
    text = "SNAKE"
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    img = Image.new('1', (text_w, text_h), 0)
    draw = ImageDraw.Draw(img)
    draw.text((-bbox[0], -bbox[1]), text, fill=1, font=font)
    # Letters stand on top of marquee in a fitted casing
    # Emissive front face, solid backing + border around each letter
    sign_z_base = 81  # up 1
    sign_y_start = cy - text_w // 2
    sign_x = 0  # flush with front edge of bounding box

    # Collect letter pixels as a set for border detection
    letter_pixels = set()
    for col in range(img.width):
        for row in range(img.height):
            if img.getpixel((col, row)):
                letter_pixels.add((col, row))

    # Expand by 1 pixel in all directions for the casing border
    border_pixels = set()
    for (c, r) in letter_pixels:
        for dc in range(-1, 2):
            for dr in range(-1, 2):
                nb = (c + dc, r + dr)
                if nb not in letter_pixels:
                    border_pixels.add(nb)

    for col, row in letter_pixels:
        py = sign_y_start + (text_w - 1 - col)
        pz = sign_z_base + (text_h - 1 - row)
        if 0 <= py <= 47:
            m.set(sign_x, py, pz, SCREEN_BRIGHT)
            m.set(sign_x + 1, py, pz, ARCADE_BODY)

    for col, row in border_pixels:
        py = sign_y_start + (text_w - 1 - col)
        pz = sign_z_base + (text_h - 1 - row)
        if 0 <= py <= 47 and pz >= sign_z_base - 1:
            m.set(sign_x, py, pz, ARCADE_BODY)
            m.set(sign_x + 1, py, pz, ARCADE_BODY)

    # ------------------------------------------------------------------
    # MATERIAL WEATHERING — color variation on surfaces
    # ------------------------------------------------------------------
    # Weathered blue palette (darker/greener variants of navy)
    BLUE_WORN = [
        ARCADE_BODY, ARCADE_BODY_2,  # original
        ARCADE_BODY, ARCADE_BODY,    # weighted toward original
    ]
    # Weathered silver palette
    SILVER_WORN = [
        ARCADE_TRIM, ARCADE_TRIM_2,
        ARCADE_TRIM, ARCADE_TRIM,
    ]

    # Randomize body + marquee surface colors for worn look
    for (vx, vy, vz), c in list(m._v.items()):
        if c == ARCADE_BODY and rng.random() < 0.15:
            m.set(vx, vy, vz, ARCADE_BODY_2)
        elif c == ARCADE_BODY_2 and rng.random() < 0.1:
            m.set(vx, vy, vz, ARCADE_BODY)

    # Randomize trim/silver colors
    for (vx, vy, vz), c in list(m._v.items()):
        if c == ARCADE_TRIM and rng.random() < 0.2:
            m.set(vx, vy, vz, ARCADE_TRIM_2)
        elif c == ARCADE_TRIM_2 and rng.random() < 0.15:
            m.set(vx, vy, vz, ARCADE_TRIM)

    # ------------------------------------------------------------------
    # ORGANIC WEATHERING — protruding moss on sides, front, top, marquee
    # Same density as before (~15%), but voxels protrude outward.
    # No back face. No control panel. No screen.
    # ------------------------------------------------------------------
    total_h = 91

    # Iterate all surface voxels, place protruding moss at ~15%
    for (vx, vy, vz), c in list(m._v.items()):
        # Skip screen area
        if vx == scr_x and scr_z_bot - 1 <= vz <= scr_z_top and scr_y1 - 1 <= vy <= scr_y2:
            continue
        # Skip control panel
        if 37 <= vz <= 48 and vx < x1:
            continue
        # Skip back face (+x)
        if vx == x2 - 1 and y1 < vy < y2 - 1:
            continue
        # Skip sign text area on marquee front
        if vx <= sign_x + 1 and sign_z_base - 1 <= vz <= sign_z_base + 10:
            continue

        # Determine which face this is on and the outward direction
        out_dx, out_dy, out_dz = 0, 0, 0
        if vx == x1 and y1 < vy < y2 - 1:  # front -x
            out_dx = -1
        elif vy == y1 and x1 < vx < x2 - 1:  # side -y
            out_dy = -1
        elif vy == y2 - 1 and x1 < vx < x2 - 1:  # side +y
            out_dy = 1
        elif vz == 90 and 79 <= vz:  # marquee top
            out_dz = 1
        elif vx == mq_x1 and 79 <= vz <= 90 and mq_y1 <= vy <= mq_y2:  # marquee front
            out_dx = -1
        elif vy == mq_y1 and 79 <= vz <= 90:  # marquee -y
            out_dy = -1
        elif vy == mq_y2 - 1 and 79 <= vz <= 90:  # marquee +y
            out_dy = 1
        else:
            continue

        # Front face gets gradient, others uniform
        if out_dx == -1 and vz < 79:
            t = vz / 79
            base_prob = 0.10 * (1.0 - t) ** 1.5
        else:
            base_prob = 0.10

        if rng.random() < base_prob:
            # Painted moss only — no protrusion
            m.set(vx, vy, vz, rng.choice(MOSS_TONES))

    # Dirt staining at the base
    for x in range(x1, x2):
        for y in range(y1, y2):
            for z in range(0, 4):
                is_surface = (x == x1 or x == x2 - 1 or y == y1 or y == y2 - 1)
                if is_surface and rng.random() < 0.15:
                    m.set(x, y, z, rng.choice(EARTH_TONES))

    return m


# ============================================================
# Part 8: Story tidbits
# ============================================================

def build_camp(seed=1000):
    rng = random.Random(seed)
    m = VoxelModel()

    # Ground
    for x in range(32):
        for y in range(32):
            m.set(x, y, 0, rng.choice(EARTH_TONES))

    # A-frame tent: two angled planes meeting at ridge
    tent_cx, tent_cy = 10, 16
    tent_w, tent_d, tent_h = 10, 8, 10
    for dy in range(tent_d):
        for dz in range(tent_h):
            # Left slope
            dx_left = dz
            if dx_left < tent_w:
                m.set(tent_cx - tent_w // 2 + dx_left, tent_cy - tent_d // 2 + dy, dz + 1,
                      rng.choice([CANVAS_1, CANVAS_2]))
            # Right slope
            dx_right = tent_w - 1 - dz
            if dx_right >= 0:
                m.set(tent_cx + tent_w // 2 - dx_right, tent_cy - tent_d // 2 + dy, dz + 1,
                      rng.choice([CANVAS_1, CANVAS_2]))

    # Campfire ring
    fire_cx, fire_cy = 22, 16
    for angle_i in range(12):
        angle = angle_i * (2 * math.pi / 12)
        sx = fire_cx + int(round(3.5 * math.cos(angle)))
        sy = fire_cy + int(round(3.5 * math.sin(angle)))
        m.set(sx, sy, 1, rng.choice([STONE_MID, STONE_DARK, STONE_LIGHT]))
    # Ash/charcoal inside
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if dx * dx + dy * dy <= 4:
                m.set(fire_cx + dx, fire_cy + dy, 1, rng.choice([CAMPFIRE_ASH, CAMPFIRE_CHAR]))

    # Supply boxes
    for bx, by in [(28, 8), (26, 12), (29, 14)]:
        for dx in range(3):
            for dy in range(3):
                for dz in range(2):
                    m.set(bx + dx, by + dy, 1 + dz, rng.choice(BOARDWALK_TONES))

    # Bedroll
    for dx in range(4):
        for dy in range(8):
            m.set(14 + dx, 24 + dy, 1, rng.choice([LEATHER, CANVAS_1]))

    return m


def build_snakeskin(seed=1100):
    rng = random.Random(seed)
    m = VoxelModel()

    # Ground
    for x in range(32):
        for y in range(32):
            m.set(x, y, 0, rng.choice(EARTH_TONES))

    # Low drying rack: two posts + crossbar
    post_h = 6
    for z in range(1, post_h + 1):
        m.set(5, 10, z, rng.choice(BOARDWALK_TONES))
        m.set(5, 22, z, rng.choice(BOARDWALK_TONES))
    # Crossbar
    for y in range(10, 23):
        m.set(5, y, post_h, rng.choice(BOARDWALK_TONES))

    # Snake skin draped over rack with diamond pattern
    skin_colors = [SKIN_OLIVE, SKIN_GOLD, SKIN_DARK, SKIN_CREAM, SKIN_ACCENT]
    for y in range(10, 23):
        # Over the bar
        m.set(5, y, post_h + 1, _diamond_color(5, y, rng, skin_colors))
        # Draping down one side
        for dz in range(min(5, post_h)):
            m.set(6, y, post_h - dz, _diamond_color(6, y - dz, rng, skin_colors))

    return m


def _diamond_color(x, y, rng, skin_colors):
    """Diamond pattern for snake skin."""
    # 3x3 diamond pattern
    phase_x = x % 6
    phase_y = y % 6
    center = (phase_x in (2, 3)) and (phase_y in (2, 3))
    border = ((phase_x in (1, 4)) and (phase_y in (1, 2, 3, 4))) or \
             ((phase_y in (1, 4)) and (phase_x in (1, 2, 3, 4)))
    if center:
        return rng.choice([SKIN_GOLD, SKIN_CREAM])
    elif border:
        return SKIN_DARK
    else:
        return rng.choice([SKIN_OLIVE, SKIN_ACCENT])


def build_tablet(seed=1200):
    rng = random.Random(seed)
    m = VoxelModel()

    # Stone slab
    for x in range(16):
        for y in range(8):
            for z in range(20):
                edge = (x == 0 or x == 15 or y == 0 or y == 7)
                if edge or z == 0 or z == 19:
                    m.set(x, y, z, rng.choice([STONE_MID, STONE_DARK]))
                else:
                    m.set(x, y, z, rng.choice([STONE_LIGHT, STONE_MID]))

    # Weathered surface speckles
    for _ in range(30):
        sx = rng.randint(1, 14)
        sy = rng.randint(1, 6)
        sz = rng.randint(1, 18)
        m.set(sx, sy, sz, STONE_SHADOW)

    # Ouroboros carving on front face (+x side)
    carve_x = 15
    center_y, center_z = 4, 10
    radius = 5
    for angle_i in range(32):
        angle = angle_i * (2 * math.pi / 32)
        cy = center_y + int(round(radius * 0.6 * math.cos(angle)))
        cz = center_z + int(round(radius * math.sin(angle)))
        if 0 <= cy < 8 and 0 <= cz < 20:
            m.delete(carve_x, cy, cz)  # carve into surface

    return m


def build_sign(seed=1300):
    rng = random.Random(seed)
    m = VoxelModel()

    # Two wood posts
    for z in range(20):
        for dx in range(2):
            for dy in range(2):
                m.set(dx, dy, z, rng.choice(BOARDWALK_TONES))
                m.set(20 + dx, dy, z, rng.choice(BOARDWALK_TONES))

    # Sign board between posts
    board_z = 12
    for x in range(2, 22):
        for dz in range(8):
            for dy in range(2):
                m.set(x, dy, board_z + dz, rng.choice(BOARDWALK_TONES))

    # "HI SCORE" text in lighter wood (simplified 3x5 pixel font on face)
    text_y = 0  # front face
    text_z = board_z + 2
    # H
    _draw_letter_H(m, 3, text_y, text_z, BONE_LIGHT)
    # I
    _draw_letter_I(m, 7, text_y, text_z, BONE_LIGHT)
    # S
    _draw_letter_S(m, 10, text_y, text_z, BONE_LIGHT)
    # C
    _draw_letter_C(m, 14, text_y, text_z, BONE_LIGHT)
    # Arrow ->
    for x in range(17, 21):
        m.set(x, text_y, text_z + 2, BONE_LIGHT)
    m.set(20, text_y, text_z + 3, BONE_LIGHT)
    m.set(20, text_y, text_z + 1, BONE_LIGHT)

    return m


def _draw_letter_H(m, x0, y, z0, c):
    for dz in range(5):
        m.set(x0, y, z0 + dz, c)
        m.set(x0 + 2, y, z0 + dz, c)
    m.set(x0 + 1, y, z0 + 2, c)

def _draw_letter_I(m, x0, y, z0, c):
    for dz in range(5):
        m.set(x0, y, z0 + dz, c)

def _draw_letter_S(m, x0, y, z0, c):
    m.set(x0, y, z0, c); m.set(x0+1, y, z0, c); m.set(x0+2, y, z0, c)
    m.set(x0, y, z0+1, c)
    m.set(x0, y, z0+2, c); m.set(x0+1, y, z0+2, c); m.set(x0+2, y, z0+2, c)
    m.set(x0+2, y, z0+3, c)
    m.set(x0, y, z0+4, c); m.set(x0+1, y, z0+4, c); m.set(x0+2, y, z0+4, c)

def _draw_letter_C(m, x0, y, z0, c):
    m.set(x0, y, z0, c); m.set(x0+1, y, z0, c); m.set(x0+2, y, z0, c)
    m.set(x0, y, z0+1, c)
    m.set(x0, y, z0+2, c)
    m.set(x0, y, z0+3, c)
    m.set(x0, y, z0+4, c); m.set(x0+1, y, z0+4, c); m.set(x0+2, y, z0+4, c)


# ============================================================
# Main entry point
# ============================================================

if __name__ == '__main__':
    output_dir = os.path.join(os.path.dirname(__file__), "generated", "parts")
    os.makedirs(output_dir, exist_ok=True)

    palette = make_palette()
    materials = get_materials()

    print("Generating Snake Arcade parts...")

    # 1. Palette
    save_palette_png(palette, os.path.join(output_dir, "palette.png"))

    # 2. Ground tiles
    print("\n  Ground tiles:")
    m = build_ground_forest()
    m.save(os.path.join(output_dir, "ground_forest.vox"), palette)

    m = build_ground_clearing()
    m.save(os.path.join(output_dir, "ground_clearing.vox"), palette)

    # 3. Boardwalk
    print("\n  Boardwalk:")
    m = build_boardwalk()
    m.save(os.path.join(output_dir, "boardwalk.vox"), palette)

    # 4. Tiki torch
    print("\n  Tiki torch:")
    m = build_tiki_torch()
    m.save(os.path.join(output_dir, "tiki_torch.vox"), palette)

    # 5. Jungle patches
    print("\n  Jungle low:")
    m = build_jungle_low()
    m.save(os.path.join(output_dir, "jungle_low.vox"), palette)

    print("\n  Jungle mid:")
    m = build_jungle_mid()
    m.save(os.path.join(output_dir, "jungle_mid.vox"), palette)

    print("\n  Jungle tall:")
    m = build_jungle_tall()
    m.save(os.path.join(output_dir, "jungle_tall.vox"), palette)

    # 6. Snake skull
    print("\n  Snake skull:")
    m = build_skull()
    m.save(os.path.join(output_dir, "skull.vox"), palette)

    # 7. Arcade machine
    print("\n  Arcade machine:")
    m = build_arcade()
    m.save(os.path.join(output_dir, "arcade.vox"), palette)

    # 8. Story tidbits
    print("\n  Camp:")
    m = build_camp()
    m.save(os.path.join(output_dir, "camp.vox"), palette)

    print("\n  Snake skin:")
    m = build_snakeskin()
    m.save(os.path.join(output_dir, "snakeskin.vox"), palette)

    print("\n  Tablet:")
    m = build_tablet()
    m.save(os.path.join(output_dir, "tablet.vox"), palette)

    print("\n  Sign:")
    m = build_sign()
    m.save(os.path.join(output_dir, "sign.vox"), palette)

    print("\nDone! All parts in:", output_dir)
