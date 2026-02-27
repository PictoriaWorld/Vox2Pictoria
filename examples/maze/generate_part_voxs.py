"""TODO: This file is unoptimized and disorganized. It works but needs cleaning up.

MagicaVoxel .vox file generator for the library maze project.
Generates palette and individual part .vox files.

Parts list:
  1. Small books x 5
  2. Large books x 5
  3. 3-connections shelf (T-junction)
  4. 2-connections shelf (straight line)
  5. 2-connections shelf (right angle, with planter)
  6. 1-connection shelf (dead end, with lamp)
  7. Tiles x 5
  8. Semi-circle planter
  9. Square planter (for top of shelf)
  10. Lamp
  11. Steps
  12. Bridge
"""

import struct
import os
import random
import math
import zlib
from PIL import Image, ImageFont, ImageDraw

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
    """Write a VOX DICT structure (used in scene graph chunks)."""
    data = struct.pack("<I", len(pairs))
    for key, value in pairs.items():
        kb = key.encode("utf-8")
        vb = value.encode("utf-8")
        data += struct.pack("<I", len(kb)) + kb
        data += struct.pack("<I", len(vb)) + vb
    return data


def _write_scene_graph(name: str = "structure0") -> bytes:
    """
    Write minimal scene graph for a single model.
    nTRN(id=0) -> nSHP(id=1, model=0)
    This makes the file compatible with Vox2Pictoria.
    """
    # nTRN: transform node (root)
    trn = struct.pack("<I", 0)           # node_id = 0
    trn += _write_dict({"_name": name})  # node attributes
    trn += struct.pack("<I", 1)          # child_node_id = 1
    trn += struct.pack("<i", -1)         # reserved_id
    trn += struct.pack("<i", -1)         # layer_id
    trn += struct.pack("<I", 1)          # num_frames
    trn += _write_dict({})               # frame attributes (no transform)
    ntrn_chunk = write_chunk(b"nTRN", trn)

    # nSHP: shape node
    shp = struct.pack("<I", 1)           # node_id = 1
    shp += _write_dict({})               # node attributes
    shp += struct.pack("<I", 1)          # num_models
    shp += struct.pack("<I", 0)          # model_id = 0
    shp += _write_dict({})               # model attributes
    nshp_chunk = write_chunk(b"nSHP", shp)

    return ntrn_chunk + nshp_chunk


def write_vox_file(filepath: str, size: tuple[int, int, int],
                    voxels: list[tuple[int, int, int, int]],
                    palette: list[tuple[int, int, int, int]],
                    materials: dict[int, dict[str, str]] | None = None):
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

    scene_graph = _write_scene_graph()

    # MATL chunks — one per palette ID (1-256), matching MagicaVoxel convention
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


# ============================================================
# Color palette
# ============================================================

def make_palette() -> list[tuple[int, int, int, int]]:
    pal = [(0, 0, 0, 255)] * 256

    # Wood tones (1-20) — darkened 40% for rich library wood (+15% red, except 7/14/17)
    pal[1]  = (181, 140, 113, 255)
    pal[2]  = (162, 124, 97, 255)
    pal[3]  = (154, 114, 86, 255)
    pal[4]  = (143, 101, 73, 255)
    pal[5]  = (131, 90, 64, 255)
    pal[6]  = (118, 80, 51, 255)
    pal[7]  = (97, 67, 42, 255)
    pal[8]  = (85, 54, 31, 255)
    pal[9]  = (67, 44, 26, 255)
    pal[10] = (53, 32, 19, 255)
    pal[11] = (145, 105, 73, 255)
    pal[12] = (137, 94, 64, 255)
    pal[13] = (124, 82, 54, 255)
    pal[14] = (102, 70, 45, 255)
    pal[15] = (151, 111, 82, 255)
    pal[16] = (127, 88, 61, 255)
    pal[17] = (105, 75, 49, 255)
    pal[18] = (92, 61, 38, 255)
    pal[19] = (74, 48, 30, 255)
    pal[20] = (59, 37, 23, 255)

    # Book spine colors (21-90)
    pal[21] = (180, 50, 50, 255);   pal[22] = (200, 65, 55, 255)
    pal[23] = (150, 35, 35, 255);   pal[24] = (120, 25, 30, 255)
    pal[25] = (165, 55, 48, 255);   pal[26] = (140, 40, 40, 255)
    pal[27] = (210, 85, 75, 255);   pal[28] = (185, 70, 60, 255)
    pal[29] = (55, 80, 140, 255);   pal[30] = (70, 100, 165, 255)
    pal[31] = (40, 60, 110, 255);   pal[32] = (30, 45, 85, 255)
    pal[33] = (85, 120, 180, 255);  pal[34] = (65, 90, 150, 255)
    pal[35] = (50, 70, 125, 255);   pal[36] = (100, 135, 190, 255)
    pal[37] = (50, 105, 60, 255);   pal[38] = (65, 125, 75, 255)
    pal[39] = (40, 80, 45, 255);    pal[40] = (80, 140, 85, 255)
    pal[41] = (55, 95, 65, 255);    pal[42] = (70, 115, 70, 255)
    pal[43] = (90, 150, 95, 255);   pal[44] = (45, 88, 55, 255)
    pal[45] = (130, 90, 55, 255);   pal[46] = (110, 75, 45, 255)
    pal[47] = (90, 60, 35, 255);    pal[48] = (70, 45, 25, 255)
    pal[49] = (150, 105, 65, 255);  pal[50] = (115, 82, 50, 255)
    pal[51] = (85, 55, 32, 255)
    pal[52] = (95, 55, 120, 255);   pal[53] = (115, 70, 140, 255)
    pal[54] = (75, 40, 100, 255);   pal[55] = (130, 85, 155, 255)
    pal[56] = (85, 50, 110, 255)
    pal[57] = (200, 130, 50, 255);  pal[58] = (185, 115, 40, 255)
    pal[59] = (215, 150, 65, 255);  pal[60] = (190, 110, 35, 255)
    pal[61] = (170, 100, 30, 255);  pal[62] = (210, 140, 55, 255)
    pal[63] = (220, 165, 80, 255);  pal[64] = (195, 125, 45, 255)
    pal[65] = (50, 110, 115, 255);  pal[66] = (40, 90, 95, 255)
    pal[67] = (65, 130, 135, 255);  pal[68] = (55, 100, 105, 255)
    pal[69] = (235, 225, 200, 255); pal[70] = (220, 210, 185, 255)
    pal[71] = (245, 238, 215, 255); pal[72] = (205, 195, 170, 255)
    pal[73] = (230, 218, 190, 255)
    pal[74] = (60, 58, 55, 255);    pal[75] = (85, 82, 78, 255)
    pal[76] = (110, 106, 100, 255); pal[77] = (140, 135, 128, 255)
    pal[78] = (190, 110, 105, 255); pal[79] = (170, 95, 90, 255)
    pal[80] = (205, 125, 115, 255)
    pal[81] = (130, 120, 70, 255);  pal[82] = (110, 100, 55, 255)
    pal[83] = (145, 135, 85, 255)
    pal[84] = (160, 75, 65, 255);   pal[85] = (175, 90, 50, 255)
    pal[86] = (95, 70, 110, 255);   pal[87] = (75, 95, 60, 255)
    pal[88] = (105, 85, 130, 255);  pal[89] = (155, 120, 90, 255)
    pal[90] = (135, 110, 80, 255)

    # Weathered book variants: 1 variant per color (alternating warm/cool)
    global BOOK_VARIANTS
    offsets = [(6, 6, 6), (-6, -6, -6)]
    vi = 147
    for idx, i in enumerate(range(21, 91)):
        r, g, b, _ = pal[i]
        dr, dg, db = offsets[idx % 2]
        pal[vi] = (min(255, max(0, r + dr)), min(255, max(0, g + dg)), min(255, max(0, b + db)), 255)
        BOOK_VARIANTS[i] = [vi]
        vi += 1

    # Desaturate all book colors (bases + variants) uniformly
    for i in list(range(21, 91)) + list(range(147, 217)):
        r, g, b, a = pal[i]
        gray = int(0.299 * r + 0.587 * g + 0.114 * b)
        t = 0.45
        pal[i] = (int(r + (gray - r) * t), int(g + (gray - g) * t), int(b + (gray - b) * t), a)

    # Stone / Tile (91-100) — rosy pink travertine, high contrast (+12% red)
    pal[91] = (255, 195, 175, 255)  # lightest pink
    pal[92] = (245, 178, 158, 255)  # light rosy
    pal[93] = (227, 162, 142, 255)  # medium light
    pal[94] = (208, 145, 125, 255)  # medium pink
    pal[95] = (180, 120, 102, 255)  # medium dark
    pal[96] = (253, 188, 168, 255)  # pale rosy
    pal[97] = (219, 155, 135, 255)  # warm mid
    pal[98] = (166, 110, 92, 255)   # warm dark
    pal[99] = (137, 85, 70, 255)    # darkest (grout/veins)
    pal[100] = (255, 192, 172, 255) # highlight pink

    # Plant greens (101-115) — desaturated for natural look
    pal[101] = (106, 138, 93, 255);  pal[102] = (89, 120, 79, 255)
    pal[103] = (73, 101, 64, 255);   pal[104] = (57, 82, 50, 255)
    pal[105] = (45, 66, 40, 255);    pal[106] = (114, 147, 100, 255)
    pal[107] = (96, 130, 84, 255);   pal[108] = (79, 108, 70, 255)
    pal[109] = (64, 89, 57, 255);    pal[110] = (118, 152, 104, 255)
    pal[111] = (84, 114, 74, 255);   pal[112] = (67, 95, 60, 255)
    pal[113] = (100, 134, 87, 255);  pal[114] = (52, 76, 47, 255)
    pal[115] = (110, 142, 95, 255)

    # Lamp / Light (116-125)
    pal[116] = (255, 230, 150, 255); pal[117] = (255, 160, 50, 255)
    pal[118] = (235, 200, 110, 255); pal[119] = (220, 185, 95, 255)
    pal[120] = (255, 240, 180, 255); pal[121] = (250, 225, 160, 255)
    pal[122] = (240, 210, 120, 255); pal[123] = (210, 175, 85, 255)
    pal[124] = (255, 245, 200, 255); pal[125] = (230, 195, 100, 255)

    # Metal (126-132)
    pal[126] = (90, 80, 65, 255);   pal[127] = (96, 85, 69, 255)
    pal[128] = (130, 115, 92, 255); pal[129] = (170, 140, 90, 255)
    pal[130] = (75, 65, 52, 255);   pal[131] = (100, 88, 70, 255)
    pal[132] = (120, 108, 85, 255)

    # Railing wood (133-138) (+10% red, -5% dark)
    pal[133] = (200, 147, 103, 255); pal[134] = (179, 131, 90, 255)
    pal[135] = (155, 112, 76, 255);  pal[136] = (134, 95, 65, 255)
    pal[137] = (113, 78, 52, 255);   pal[138] = (167, 122, 84, 255)

    # Book page edges (139-143)
    pal[139] = (240, 232, 210, 255); pal[140] = (228, 220, 198, 255)
    pal[141] = (218, 208, 185, 255); pal[142] = (235, 228, 205, 255)
    pal[143] = (210, 200, 178, 255)

    # Dirt / soil (144-146) - for planters
    pal[144] = (120, 85, 50, 255)   # medium dirt
    pal[145] = (100, 70, 40, 255)   # dark dirt
    pal[146] = (140, 100, 60, 255)  # light dirt

    # Extra-dark wood for sign (225-228) (+10% red, -5% dark)
    pal[225] = (40, 21, 11, 255)   # near-black mahogany
    pal[226] = (48, 27, 15, 255)   # very dark mahogany
    pal[227] = (55, 30, 19, 255)   # dark mahogany
    pal[228] = (44, 24, 13, 255)   # deep shadow mahogany

    # Sandstone (217-224) - warm buff tones, tight range for carved stone (+10% red)
    pal[217] = (248, 208, 178, 255)  # highlight
    pal[218] = (237, 198, 168, 255)  # light
    pal[219] = (226, 188, 158, 255)  # medium light
    pal[220] = (215, 178, 148, 255)  # medium
    pal[221] = (204, 168, 138, 255)  # medium warm
    pal[222] = (193, 158, 128, 255)  # medium dark
    pal[223] = (179, 145, 115, 255)  # dark
    pal[224] = (160, 128, 100, 255)  # shadow

    return pal


def save_palette_png(palette, filepath):
    """Save palette as a 256x1 PNG (importable by MagicaVoxel)."""
    width, height = 256, 1
    # Build raw RGBA row with filter byte
    raw = b'\x00'  # filter byte for the single row
    for i in range(1, 257):
        r, g, b, a = palette[i] if i < len(palette) else (0, 0, 0, 255)
        raw += struct.pack('BBBB', r, g, b, a)
    # PNG chunks
    def _png_chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = zlib.compress(raw)
    with open(filepath, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(_png_chunk(b'IHDR', ihdr))
        f.write(_png_chunk(b'IDAT', idat))
        f.write(_png_chunk(b'IEND', b''))
    print(f"  Palette saved: {filepath}")


# ============================================================
# Color index constants
# ============================================================

WOOD_LIGHTEST     = 1
WOOD_LIGHT        = 2
WOOD_MED_LIGHT    = 3
WOOD_MEDIUM       = 4
WOOD_MED_WARM     = 5
WOOD_MED_DARK     = 6
WOOD_DARK         = 7
WOOD_DARKER       = 8
WOOD_DARKEST      = 9
WOOD_SHADOW       = 10

BOOK_RED     = 21;  BOOK_BLUE   = 29;  BOOK_GREEN  = 37
BOOK_BROWN   = 45;  BOOK_PURPLE = 52;  BOOK_GOLD   = 57
BOOK_TEAL    = 65;  BOOK_CREAM  = 69;  BOOK_BLACK  = 74
BOOK_PINK    = 78

TILE_LIGHT   = 91;  TILE_MEDIUM = 92;  TILE_DARK   = 95
TILE_HIGHLIGHT = 96; TILE_MID   = 97;  TILE_SHADOW = 98

PLANT_BRIGHT = 101; PLANT_MEDIUM = 103; PLANT_DARK  = 105
PLANT_COLORS = list(range(101, 116))

LAMP_BRIGHT  = 116; LAMP_WARM   = 117; LAMP_GLOW   = 118
LAMP_COLORS  = list(range(116, 126))

METAL_DARK   = 126; METAL_MEDIUM = 128; METAL_LIGHT = 129

RAILING_LIGHT = 133; RAILING_MED = 134; RAILING_DARK = 136

PAGE_WHITE   = 139; PAGE_AGED   = 140
PAGE_COLORS  = list(range(139, 144))

DIRT_MED     = 144; DIRT_DARK   = 145; DIRT_LIGHT  = 146

SAND_HIGHLIGHT = 217; SAND_LIGHT = 218; SAND_MED_LIGHT = 219; SAND_MEDIUM = 220
SAND_MED_WARM  = 221; SAND_MED_DARK = 222; SAND_DARK = 223; SAND_SHADOW = 224

SAND_RIM_TONES   = [SAND_HIGHLIGHT, SAND_LIGHT]
SAND_BODY_TONES  = [SAND_MED_LIGHT, SAND_MEDIUM, SAND_MED_WARM]
SAND_BASE_TONES  = [SAND_MED_DARK, SAND_DARK]

BOOK_SPINE_COLORS = list(range(21, 91))
BOOK_VARIANTS = {}  # populated by make_palette(): base_index -> [variant_indices]
# Color family ranges — shifts stay within the same family
_BOOK_FAMILIES = [
    (21, 28), (29, 36), (37, 44), (45, 51), (52, 56),
    (57, 64), (65, 68), (69, 73), (74, 77), (78, 80),
    (81, 83), (84, 85), (86, 90),
]
def _spine_shift(base, shift):
    """Shift a spine color index, clamped within its color family."""
    s = base + shift
    for lo, hi in _BOOK_FAMILIES:
        if lo <= base <= hi:
            return max(lo, min(hi, s))
    return base

# Shelf construction constants (32x32 footprint, 128 voxels tall, hollow 3D)
SHELF_W        = 32
SHELF_D        = 32
SHELF_H        = 68
SHELF_DEPTH    = 14         # book space depth from face inward
BOARD_THICKNESS = 6         # thick substantial shelf boards
BACK_THICKNESS  = 2         # back panel thickness
BOARD_ZS       = [0, 27, 54, 80]  # z-start of each shelf board (3 levels + top cap)
LEVEL_RANGES   = [(6, 27), (33, 54), (60, 80)]  # book space per level
FRAME_TONE     = 13         # warm dark tone for frame edges (168,130,85)
CORNER_SIZE    = 5          # thick corner framing
BOOK_FACE_DEPTH = 5         # books recessed so shelf boards protrude past them
SHELF_STRUCT_TOP = BOARD_ZS[-1] + BOARD_THICKNESS  # top of structure

# 2-height shelf constants (for entrance gateway)
BOARD_ZS_2H       = BOARD_ZS[:3]                          # [0, 27, 54]
LEVEL_RANGES_2H   = LEVEL_RANGES[:2]                      # [(6, 27), (33, 54)]
SHELF_STRUCT_TOP_2H = BOARD_ZS_2H[-1] + BOARD_THICKNESS   # 60

SHELF_CFG_2H = {
    'board_zs': BOARD_ZS_2H,
    'level_ranges': LEVEL_RANGES_2H,
    'struct_top': SHELF_STRUCT_TOP_2H,
}

PLAQUE_SIGN_Z_OFFSET = 0  # posts start at ground level; sign sits on top

# Wood grain tone palettes (defined once, reused by all shelf/bridge generators)
GRAIN_BODY      = [WOOD_MED_DARK, 13, 13, WOOD_MED_DARK, 16]   # boards, frames, top, corner fill
GRAIN_DARK_WOOD = [WOOD_DARK, 14, 14, WOOD_DARK, 17]            # rails, dentils
GRAIN_EXTRA_DARK_WOOD = [225, 226, 227, 228, WOOD_SHADOW]       # sign background
GRAIN_RECESS    = [WOOD_DARK, WOOD_DARKER, WOOD_MED_DARK]      # end panel recess
GRAIN_FOOT      = [WOOD_DARKER, WOOD_DARK, 18]                 # base molding foot
GRAIN_KICK      = [WOOD_MED_DARK, 13, 16]                      # base molding kick/transition
GRAIN_CAP       = [WOOD_DARK, WOOD_DARKER, 13]                 # base molding cap
GRAIN_JOINT     = [WOOD_DARK, WOOD_DARKER, WOOD_DARK]          # bridge plank joints
GRAIN_PLANTER   = [WOOD_MED_DARK, WOOD_MEDIUM, WOOD_MED_WARM, 13, 16]  # planter pot body
GRAIN_PLANTER_RIM = [WOOD_MED_DARK, WOOD_MEDIUM, WOOD_MED_WARM, 13]    # planter pot rim


# ============================================================
# VoxelModel helper
# ============================================================

class VoxelModel:
    """Dict-based voxel builder - handles overlapping writes gracefully."""

    def __init__(self):
        self._v = {}
        self._materials = {}

    def set(self, x, y, z, color):
        self._v[(x, y, z)] = color

    def delete(self, x, y, z):
        self._v.pop((x, y, z), None)

    def get(self, x, y, z):
        return self._v.get((x, y, z), 0)

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

    def save(self, filepath, palette, size=None):
        write_vox_file(filepath, size or self.get_size(), self.to_list(), palette,
                       self._materials if self._materials else None)


# ============================================================
# Shelf building helpers
# ============================================================

def face_set_fn(model, face):
    """Return set(along, depth, z, color) mapping face-relative coords to world coords.
    along: position along the face (0..31)
    depth: distance inward from face (0 = face plane)
    """
    if face == 'W':
        return lambda a, d, z, c: model.set(d, a, z, c)
    elif face == 'E':
        return lambda a, d, z, c: model.set(31 - d, a, z, c)
    elif face == 'S':
        return lambda a, d, z, c: model.set(a, 31 - d, z, c)
    elif face == 'N':
        return lambda a, d, z, c: model.set(a, d, z, c)


def face_del_fn(model, face):
    """Return del(along, depth, z) that deletes a voxel in face-relative coords."""
    if face == 'W':
        return lambda a, d, z: model.delete(d, a, z)
    elif face == 'E':
        return lambda a, d, z: model.delete(31 - d, a, z)
    elif face == 'S':
        return lambda a, d, z: model.delete(a, 31 - d, z)
    elif face == 'N':
        return lambda a, d, z: model.delete(a, d, z)


def place_back_panel(model, face, cfg=None):
    """2-voxel back panel at SHELF_DEPTH from the exposed face."""
    _struct_top = cfg['struct_top'] if cfg else SHELF_STRUCT_TOP
    sd, bt = SHELF_DEPTH, BACK_THICKNESS
    if face == 'W':   model.fill(range(sd, sd + bt), range(32), range(_struct_top), WOOD_DARK)
    elif face == 'E': model.fill(range(32 - sd - bt, 32 - sd), range(32), range(_struct_top), WOOD_DARK)
    elif face == 'S': model.fill(range(32), range(32 - sd - bt, 32 - sd), range(_struct_top), WOOD_DARK)
    elif face == 'N': model.fill(range(32), range(sd, sd + bt), range(_struct_top), WOOD_DARK)


def place_shelf_boards(model, face, rng, a_range=None, cfg=None):
    """Warm wood boards with natural grain and vertical aging."""
    _board_zs = cfg['board_zs'] if cfg else BOARD_ZS
    set_v = face_set_fn(model, face)
    if a_range is None:
        a_range = range(32)
    span = SHELF_DEPTH + BACK_THICKNESS
    # Vertical aging: lower boards warmer/darker, upper lighter
    # Each palette uses ONLY close warm tones — no dark streaks
    board_tones = GRAIN_BODY
    for bi, z0 in enumerate(_board_zs):
        tones = board_tones
        base = rng.choice(tones)
        pattern = []
        cur = base
        left = rng.randint(6, 14)
        for _ in range(32):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(6, 14)
            pattern.append(cur)
            left -= 1
        for a in a_range:
            c = pattern[a]
            for dz in range(BOARD_THICKNESS):
                for d in range(BOOK_FACE_DEPTH, span):
                    set_v(a, d, z0 + dz, c)


def place_frame_edges(model, faces, rng, cfg=None):
    """Front face of shelf boards with wood grain and dramatically stepped profile.

    With BOOK_FACE_DEPTH=5, the profile from the side looks like:
      dz=0:  ____█    depth 4 only (deeply recessed bottom = shadow)
      dz=1:  __███    depth 2-4 (body, recessed 2 from face)
      dz=2:  __███    depth 2-4 (body)
      dz=3:  __███    depth 2-4 (body)
      dz=4:  ██████   depth 0-5 (lip, flush + 1 past body)
      dz=5:  ██████   depth 0-5 (lip, flush + 1 past body)

    This creates a visible 2-voxel step at every shelf level.
    """
    _board_zs = cfg['board_zs'] if cfg else BOARD_ZS
    # Darker warm wood tones for grain
    board_tones = GRAIN_BODY
    for face in faces:
        set_v = face_set_fn(model, face)
        for bi, z0 in enumerate(_board_zs):
            tones = board_tones
            # 2D grain: each dz row has its own pattern
            patterns = []
            for dz in range(BOARD_THICKNESS):
                pat = []
                cur = rng.choice(tones)
                left = rng.randint(5, 12)
                for _ in range(32):
                    if left <= 0:
                        cur = rng.choice(tones)
                        left = rng.randint(5, 12)
                    pat.append(cur)
                    left -= 1
                patterns.append(pat)
            for a in range(32):
                for dz in range(BOARD_THICKNESS):
                    c = patterns[dz][a]
                    z = z0 + dz
                    if dz == 0:
                        # Deeply recessed bottom (shadow reveal)
                        set_v(a, BOOK_FACE_DEPTH - 1, z, c)
                    elif dz >= BOARD_THICKNESS - 2:
                        # Top lip: flush with face, extends 1 past body into book area
                        for d in range(BOOK_FACE_DEPTH + 1):
                            set_v(a, d, z, c)
                    else:
                        # Body: recessed 2 from face
                        for d in range(2, BOOK_FACE_DEPTH):
                            set_v(a, d, z, c)


END_PANEL_THICKNESS = 3  # thin side board

def place_end_panel(model, face, rng, cfg=None, z_bottom=None, z_top=None, recess_z_bottom=None):
    """Thin wood end panel with one large recessed rectangle and base kick cutout.

    - Panel is END_PANEL_THICKNESS (3) voxels deep
    - One large geometric recess (depth 0 deleted) spanning from above first
      board to below last board, inset 4 voxels from edges
    - Base kick cutout: deletes voxels at z=2,3 in center so the plinth
      recess is visible (matching W/E base molding profile)
    - z_bottom/z_top: optional partial-height panel range
    """
    _struct_top = cfg['struct_top'] if cfg else SHELF_STRUCT_TOP
    _level_ranges = cfg['level_ranges'] if cfg else LEVEL_RANGES
    _board_zs = cfg['board_zs'] if cfg else BOARD_ZS
    if z_bottom is None:
        z_bottom = BOARD_THICKNESS
    if z_top is None:
        z_top = _struct_top
    set_v = face_set_fn(model, face)
    del_v = face_del_fn(model, face)
    pt = END_PANEL_THICKNESS
    body_tones = GRAIN_BODY
    recess_tones = GRAIN_RECESS
    board_tones = GRAIN_BODY
    # 1. Flat panel with vertical grain (skip base molding zone z=0..5)
    for a in range(32):
        for d in range(pt):
            cur = rng.choice(body_tones)
            left = rng.randint(4, 10)
            for z in range(z_bottom, z_top):
                if left <= 0:
                    cur = rng.choice(body_tones)
                    left = rng.randint(4, 10)
                set_v(a, d, z, cur)
                left -= 1
    # 2. One large recessed rectangle: delete depth 0 to create geometric indent
    rect_margin_a = 4
    rz0 = _level_ranges[0][0] + 2          # above first book tier start
    rz1 = _board_zs[-1] - 1                # one voxel below top board
    # Clamp recess to [z_bottom, z_top] range (recess_z_bottom overrides)
    rz0 = max(rz0, recess_z_bottom if recess_z_bottom is not None else z_bottom)
    rz1 = min(rz1, z_top)
    ra0 = rect_margin_a
    ra1 = 32 - rect_margin_a
    for a in range(ra0, ra1):
        for z in range(rz0, rz1):
            is_border = (a == ra0 or a == ra1 - 1 or z == rz0 or z == rz1 - 1)
            if is_border:
                # Dark border frame at depth 0
                c = WOOD_DARKER if rng.random() > 0.3 else rng.choice(recess_tones)
                set_v(a, 0, z, c)
            else:
                # Delete depth 0 — real geometric recess exposing depth 1
                del_v(a, 0, z)
    # 3. Base kick cutout: only when panel starts at base level
    if z_bottom <= BOARD_THICKNESS:
        kick_margin = BOOK_FACE_DEPTH  # leave legs at the edges
        for a in range(kick_margin, 32 - kick_margin):
            for d in range(3):
                del_v(a, d, 2)
                del_v(a, d, 3)


def add_corner_post(model, corner, rng, cfg=None):
    """Solid 5x5 corner post with vertical grain — blends with shelf boards.

    Uses the same warm body tones as the shelf interior so it doesn't
    create visible dark "pilaster" columns at the corner.  The outermost
    corner voxel is chamfered (removed) for a shaped profile.
    """
    _struct_top = cfg['struct_top'] if cfg else SHELF_STRUCT_TOP
    cs = CORNER_SIZE
    if corner == 'SW':
        x0, y0 = 0, 32 - cs
        chamfer = lambda lx, ly: lx == 0 and ly == cs - 1
    elif corner == 'SE':
        x0, y0 = 32 - cs, 32 - cs
        chamfer = lambda lx, ly: lx == cs - 1 and ly == cs - 1
    elif corner == 'NW':
        x0, y0 = 0, 0
        chamfer = lambda lx, ly: lx == 0 and ly == 0
    elif corner == 'NE':
        x0, y0 = 32 - cs, 0
        chamfer = lambda lx, ly: lx == cs - 1 and ly == 0
    body_tones = GRAIN_BODY
    for lx in range(cs):
        for ly in range(cs):
            if chamfer(lx, ly):
                continue
            x, y = x0 + lx, y0 + ly
            # Vertical grain streak per column
            cur = rng.choice(body_tones)
            left = rng.randint(4, 10)
            for z in range(_struct_top):
                if left <= 0:
                    cur = rng.choice(body_tones)
                    left = rng.randint(4, 10)
                model.set(x, y, z, cur)
    # Clean up frame edge lip remnants that extend 1 voxel past the corner post.
    # Frame edge lip is at depth BOOK_FACE_DEPTH (=5), but corner post only
    # covers CORNER_SIZE (=5) voxels at depth 0..4.  Overwrite the depth-5 lip
    # columns adjacent to the post so they don't appear as "pilasters".
    if corner in ('SW', 'NW'):
        lip_x = x0 + cs          # W face lip at x = CORNER_SIZE
    else:
        lip_x = x0 - 1           # E face lip at x = x0 - 1
    if corner in ('SW', 'SE'):
        lip_y = y0 - 1           # S face lip at y = y0 - 1
    else:
        lip_y = y0 + cs          # N face lip at y = y0 + cs
    lip_cols = [(lip_x, y) for y in range(y0, y0 + cs)] + \
               [(x, lip_y) for x in range(x0, x0 + cs)]
    for lx, ly in lip_cols:
        cur = rng.choice(body_tones)
        left = rng.randint(4, 10)
        for z in range(_struct_top):
            if left <= 0:
                cur = rng.choice(body_tones)
                left = rng.randint(4, 10)
            model.set(lx, ly, z, cur)
            left -= 1


def place_crown_molding(model, faces, rng, cfg=None):
    """Classical crown with dentil molding — 4 tall.
    z+0: cove (recessed, transition from frame body)
    z+1: dentil row (alternating blocks/gaps, flush with face)
    z+2: cap plate (widest, overhanging dentils)
    z+3: top fillet (slightly narrower, clean edge)
    """
    _struct_top = cfg['struct_top'] if cfg else SHELF_STRUCT_TOP
    crown_tones = GRAIN_BODY
    def _streak(tones):
        pat = []
        cur = rng.choice(tones)
        left = rng.randint(5, 12)
        for _ in range(32):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(5, 12)
            pat.append(cur)
            left -= 1
        return pat
    for face in faces:
        set_v = face_set_fn(model, face)
        z = _struct_top
        p0 = _streak(crown_tones)
        p2 = _streak(crown_tones)
        p3 = _streak(crown_tones)
        # z+0: cove — recessed 2 from face, same width as frame body
        for a in range(32):
            for d in range(2, BOOK_FACE_DEPTH + 1):
                set_v(a, d, z, p0[a])
        # z+1: dentil row — alternating 2-on/2-off blocks, flush with face
        dentil_tones = GRAIN_DARK_WOOD
        for a in range(32):
            if (a // 2) % 2 == 0:
                for d in range(BOOK_FACE_DEPTH + 1):
                        set_v(a, d, z + 1, rng.choice(dentil_tones))
        # z+2: cap plate — widest, depth-direction plank grain on top
        cap_depth = BOOK_FACE_DEPTH + 3
        for a in range(32):
            cur = p2[a]
            left = rng.randint(2, 4)
            for d in range(cap_depth):
                if left <= 0:
                    cur = rng.choice(crown_tones)
                    left = rng.randint(2, 4)
                set_v(a, d, z + 2, cur)
                left -= 1
        # z+3: top fillet — slightly narrower, depth-direction plank grain
        fil_depth = BOOK_FACE_DEPTH + 2
        for a in range(32):
            cur = p3[a]
            left = rng.randint(2, 4)
            for d in range(fil_depth):
                if left <= 0:
                    cur = rng.choice(crown_tones)
                    left = rng.randint(2, 4)
                set_v(a, d, z + 3, cur)
                left -= 1


def place_corner_crown(model, corner, rng, cfg=None):
    """Create stepped crown profile at a corner from two perpendicular faces.

    Generates the same 4-layer profile as place_crown_molding (cove, dentil,
    cap, fillet) but fills the union of two perpendicular face strips.
    """
    _struct_top = cfg['struct_top'] if cfg else SHELF_STRUCT_TOP
    cs = CORNER_SIZE
    z = _struct_top
    crown_tones = GRAIN_BODY
    dentil_tones = GRAIN_DARK_WOOD

    if corner == 'NE':
        x_range = range(32 - cs, 32)
        y_range = range(0, cs)
        y_fn = lambda d: d          # N face: depth into +y
        x_fn = lambda d: 31 - d     # E face: depth into -x
    elif corner == 'NW':
        x_range = range(0, cs)
        y_range = range(0, cs)
        y_fn = lambda d: d          # N face: depth into +y
        x_fn = lambda d: d          # W face: depth into +x
    elif corner == 'SW':
        x_range = range(0, cs)
        y_range = range(32 - cs, 32)
        y_fn = lambda d: 31 - d     # S face: depth into -y
        x_fn = lambda d: d          # W face: depth into +x
    elif corner == 'SE':
        x_range = range(32 - cs, 32)
        y_range = range(32 - cs, 32)
        y_fn = lambda d: 31 - d     # S face: depth into -y
        x_fn = lambda d: 31 - d     # E face: depth into -x

    def strip_cells(d_min, d_max):
        """L-shaped union of two perpendicular strips."""
        cells = set()
        for d in range(d_min, d_max):
            y = y_fn(d)
            for x in x_range:
                cells.add((x, y))
            x = x_fn(d)
            for yy in y_range:
                cells.add((x, yy))
        return sorted(cells)

    def full_rect(d_max):
        """Full square from corner vertex to max overhang in both directions."""
        x0 = min(x_fn(0), x_fn(d_max - 1))
        x1 = max(x_fn(0), x_fn(d_max - 1))
        y0 = min(y_fn(0), y_fn(d_max - 1))
        y1 = max(y_fn(0), y_fn(d_max - 1))
        return sorted((x, y) for x in range(x0, x1 + 1)
                       for y in range(y0, y1 + 1))

    # z+0: cove — recessed, L-shape preserves recession at corner vertex
    for x, y in strip_cells(2, BOOK_FACE_DEPTH + 1):
        model.set(x, y, z, rng.choice(crown_tones))

    # z+1: dentil — solid square at corner
    for x, y in full_rect(BOOK_FACE_DEPTH + 1):
        model.set(x, y, z + 1, rng.choice(dentil_tones))

    # z+2: cap — widest overhang, full square
    for x, y in full_rect(BOOK_FACE_DEPTH + 3):
        model.set(x, y, z + 2, rng.choice(crown_tones))

    # z+3: fillet — slightly narrower, full square
    for x, y in full_rect(BOOK_FACE_DEPTH + 2):
        model.set(x, y, z + 3, rng.choice(crown_tones))


def place_top_grain(model, rng, x_range, y_range, cfg=None):
    """Apply wood plank grain to the top surface of the uppermost board."""
    _board_zs = cfg['board_zs'] if cfg else BOARD_ZS
    top_z = _board_zs[-1] + BOARD_THICKNESS - 1  # top face of the cap board
    top_tones = GRAIN_BODY
    # Planks run along X — each Y row is one plank with its own streak
    for y in y_range:
        pat = []
        cur = rng.choice(top_tones)
        left = rng.randint(5, 12)
        for _ in range(max(x_range) - min(x_range) + 1):
            if left <= 0:
                cur = rng.choice(top_tones)
                left = rng.randint(5, 12)
            pat.append(cur)
            left -= 1
        for xi, x in enumerate(x_range):
            model.set(x, y, top_z, pat[xi])


def place_gallery_lips(model, faces, rng, a_ranges=None, cfg=None):
    """Mini fence at front of each shelf level: alternating posts + top rail.
    a_ranges: optional dict mapping face -> range to limit extent."""
    _level_ranges = cfg['level_ranges'] if cfg else LEVEL_RANGES
    rail_tones = GRAIN_DARK_WOOD
    for face in faces:
        set_v = face_set_fn(model, face)
        a_range = a_ranges.get(face, range(32)) if a_ranges else range(32)
        for z_start, _ in _level_ranges:
            for a in a_range:
                # Alternating posts at board level
                if a % 2 == 0:
                    set_v(a, 1, z_start, rng.choice(rail_tones))
                # Continuous top rail 1 above
                set_v(a, 1, z_start + 1, rng.choice(rail_tones))


def place_base_molding(model, faces, rng):
    """Architectural plinth — 6 tall with ogee-like stepped profile.
    Foot and cap PROTRUDE (depth 0), kick is RECESSED (depth 3).
    Side profile:
      z=0: ████████   foot (depth 0, flush, widest)
      z=1: ████████   foot (depth 0, flush)
      z=2: ___█████   kick (depth 3, recessed)
      z=3: ___█████   kick (depth 3, recessed)
      z=4: ████████   cap  (depth 0, flush, protruding past kick)
      z=5: __██████   transition (depth 2, matching frame body)
    """
    foot_tones = GRAIN_FOOT
    kick_tones = GRAIN_KICK
    cap_tones  = GRAIN_CAP
    # Build streak patterns per row along each face
    def _streak(tones):
        pat = []
        cur = rng.choice(tones)
        left = rng.randint(5, 12)
        for _ in range(32):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(5, 12)
            pat.append(cur)
            left -= 1
        return pat
    for face in faces:
        set_v = face_set_fn(model, face)
        p0, p1 = _streak(foot_tones), _streak(foot_tones)
        p2, p3 = _streak(kick_tones), _streak(kick_tones)
        p4 = _streak(cap_tones)
        p5 = _streak(kick_tones)
        for a in range(32):
            for d in range(BOOK_FACE_DEPTH + 4):
                set_v(a, d, 0, p0[a])
                set_v(a, d, 1, p1[a])
            for d in range(3, BOOK_FACE_DEPTH + 2):
                set_v(a, d, 2, p2[a])
                set_v(a, d, 3, p3[a])
            for d in range(BOOK_FACE_DEPTH + 3):
                set_v(a, d, 4, p4[a])
            for d in range(2, BOOK_FACE_DEPTH + 1):
                set_v(a, d, 5, p5[a])


def place_books_on_level(model, face, bays, z_start, z_end, rng):
    """Place books with natural weathering: sun-faded spines, yellowed pages, height variation.

    Weathering is per-book (consistent within each book, varied between books):
    - 12% of books are sun-faded (cream/tan spines replacing original color)
    - Page tone per book ranges from fresh white to deep amber
    - Height varies noticeably (some old books shorter from worn bindings)
    - No per-voxel noise — each book is one clean color.
    """
    set_v = face_set_fn(model, face)
    tier_h = z_end - z_start
    max_d = SHELF_DEPTH - BOOK_FACE_DEPTH
    # Sun-faded spine colors (cream, tan, pale gold)
    FADED_SPINES = [69, 70, 71, 72, 73, 89, 90]
    # Page tones from fresh to old (picked per-book for consistency)
    PAGE_FRESH   = [PAGE_WHITE, PAGE_WHITE, 142]          # bright white/near-white
    PAGE_MEDIUM  = [PAGE_AGED, 142, 141]                  # cream
    PAGE_OLD     = [141, 143, 143]                        # yellowed
    page_pools   = [PAGE_FRESH, PAGE_MEDIUM, PAGE_MEDIUM, PAGE_OLD]
    for bay in bays:
        positions = list(bay)
        i = 0
        prev_color = -1
        while i < len(positions):
            if rng.random() < 0.04:
                i += 1
                continue
            # Pick spine color, ensuring it differs from the previous book
            for _attempt in range(10):
                r = rng.random()
                if r < 0.06:
                    spine_color = rng.choice(FADED_SPINES)
                elif r < 0.20:
                    spine_color = rng.choice([47, 48, 50, 51, 74, 75, 76, 90])
                else:
                    spine_color = rng.choice(BOOK_SPINE_COLORS)
                if spine_color != prev_color:
                    break
            # Per-book page tone (consistent for entire book)
            page_pool = rng.choice(page_pools)
            page_c = rng.choice(page_pool)
            book_d = rng.randint(8, max_d)
            book_w = rng.choice([1, 2, 2, 3, 3, 4])
            book_h = rng.randint(max(tier_h - 12, 6), tier_h - 5)
            avail = len(positions) - i
            book_w = min(book_w, max(1, avail))
            if i + book_w > len(positions):
                break
            start_a = positions[i]
            for w in range(book_w):
                a = start_a + w
                is_cover = (w == 0 or w == book_w - 1)
                variants = BOOK_VARIANTS.get(spine_color, [])
                for z in range(z_start, z_start + book_h):
                    if variants and rng.random() < 0.35:
                        sc = rng.choice(variants)
                    else:
                        sc = spine_color
                    set_v(a, BOOK_FACE_DEPTH, z, sc)
                    pc = rng.choice(page_pool)
                    for d in range(BOOK_FACE_DEPTH + 1, BOOK_FACE_DEPTH + book_d):
                        set_v(a, d, z, spine_color if is_cover else pc)
                top_z = z_start + book_h
                set_v(a, BOOK_FACE_DEPTH, top_z, spine_color)
                top_page_c = rng.choice(page_pool)
                for d in range(BOOK_FACE_DEPTH + 1, BOOK_FACE_DEPTH + book_d):
                    set_v(a, d, top_z, spine_color if is_cover else top_page_c)
            prev_color = spine_color
            i += book_w


def build_shelf_planter(model, rng):
    """Stone planter centered on shelf top (above crown molding)."""
    base_z = SHELF_STRUCT_TOP + 4
    size = 8
    wall_h = 5
    cx = SHELF_W // 2 - size // 2
    cy = SHELF_D // 2 - size // 2
    for dx in range(size):
        for dy in range(size):
            x, y = cx + dx, cy + dy
            edge = dx == 0 or dx == size - 1 or dy == 0 or dy == size - 1
            if edge:
                for z in range(wall_h):
                    model.set(x, y, base_z + z, TILE_MEDIUM)
            else:
                for z in range(wall_h - 2):
                    model.set(x, y, base_z + z, DIRT_DARK)
                model.set(x, y, base_z + wall_h - 2, DIRT_MED)
                model.set(x, y, base_z + wall_h - 1, rng.choice(PLANT_COLORS))
                if rng.random() < 0.7:
                    model.set(x, y, base_z + wall_h, rng.choice(PLANT_COLORS))
                if rng.random() < 0.3:
                    model.set(x, y, base_z + wall_h + 1, rng.choice(PLANT_COLORS[:5]))


def build_lamp(model, base_z=0):
    """Build a Victorian lamp post. 6x6 footprint (x=0..5, y=0..5), 29 tall.
    No stone base — designed to sit in a planter."""
    rng = random.Random(77)

    def _m():
        return 127 if rng.random() < 0.30 else METAL_DARK

    z = base_z

    # --- z+0..1: Pedestal (4x4) ---
    for dz in range(2):
        for x in range(1, 5):
            for y in range(1, 5):
                model.set(x, y, z + dz, _m())

    # --- z+2..18: Post shaft (2x2, 17 layers) with collar at midpoint ---
    for sz in range(z + 2, z + 19):
        for x in (2, 3):
            for y in (2, 3):
                model.set(x, y, sz, _m())
    # Decorative collar at midpoint (4x4 ring)
    for x in range(1, 5):
        for y in range(1, 5):
            if x in (1, 4) or y in (1, 4):
                model.set(x, y, z + 10, _m())

    # --- z+19: Upper bracket (4x4) ---
    for x in range(1, 5):
        for y in range(1, 5):
            model.set(x, y, z + 19, _m())

    # --- z+20: Lantern base (6x6) ---
    for x in range(6):
        for y in range(6):
            model.set(x, y, z + 20, _m())

    # --- z+21..24: Lantern housing (6x6, 4 layers) ---
    # Emissive shell, hollow center:
    #   M E E E E M      M = Metal (corners)
    #   E . . . . E      E = LAMP_WARM (emissive)
    #   E . . . . E      . = empty (hollow)
    #   E . . . . E
    #   E . . . . E
    #   M E E E E M
    for lz in range(z + 21, z + 25):
        for x in range(6):
            for y in range(6):
                corner = (x in (0, 5)) and (y in (0, 5))
                edge = (x in (0, 5)) or (y in (0, 5))
                if corner:
                    model.set(x, y, lz, _m())
                elif edge:
                    model.set(x, y, lz, LAMP_WARM)

    # --- z+25: Lantern top plate (6x6) ---
    for x in range(6):
        for y in range(6):
            model.set(x, y, z + 25, _m())

    # --- z+26: Cap step 1 (4x4) ---
    for x in range(1, 5):
        for y in range(1, 5):
            model.set(x, y, z + 26, _m())

    # --- z+27: Cap step 2 (2x2) ---
    for x in (2, 3):
        for y in (2, 3):
            model.set(x, y, z + 27, _m())

    # --- z+28: Finial (1x1) ---
    model.set(2, 2, z + 28, METAL_DARK)


# ============================================================
# 1 & 2. Book generators
# ============================================================


# ============================================================
# 3-6. Shelf generators
# ============================================================

def generate_shelf_3conn(palette, output_dir, rng, filename="shelf_3conn.vox", save=True):
    """3-conn T: connections N, S, E (open). Exposed: W only."""
    m = VoxelModel()
    bp = SHELF_DEPTH + BACK_THICKNESS
    place_back_panel(m, 'W')
    place_shelf_boards(m, 'W', rng)
    m.fill(range(bp, 32), range(32), range(SHELF_STRUCT_TOP), WOOD_MED_DARK)
    # Vertical plank grain on connection face surfaces
    grain_tones = GRAIN_BODY
    for x in range(bp, 32):                                          # N face
        cur = rng.choice(grain_tones)
        left = rng.randint(5, 12)
        for z in range(SHELF_STRUCT_TOP):
            if left <= 0:
                cur = rng.choice(grain_tones)
                left = rng.randint(5, 12)
            m.set(x, 0, z, cur)
            left -= 1
    for x in range(bp, 32):                                          # S face
        cur = rng.choice(grain_tones)
        left = rng.randint(5, 12)
        for z in range(SHELF_STRUCT_TOP):
            if left <= 0:
                cur = rng.choice(grain_tones)
                left = rng.randint(5, 12)
            m.set(x, 31, z, cur)
            left -= 1
    for y in range(32):                                               # E face
        cur = rng.choice(grain_tones)
        left = rng.randint(5, 12)
        for z in range(SHELF_STRUCT_TOP):
            if left <= 0:
                cur = rng.choice(grain_tones)
                left = rng.randint(5, 12)
            m.set(31, y, z, cur)
            left -= 1
    place_frame_edges(m, ['W'], rng)
    bays = [range(0, 32)]
    for z_s, z_e in LEVEL_RANGES:
        place_books_on_level(m, 'W', bays, z_s, z_e, rng)
    place_base_molding(m, ['W'], rng)
    place_crown_molding(m, ['W'], rng)
    place_gallery_lips(m, ['W'], rng)
    place_corner_crown(m, 'NE', rng)
    place_corner_crown(m, 'SE', rng)
    place_top_grain(m, rng, range(0, 32), range(0, 32))
    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m


def generate_shelf_2conn_line(palette, output_dir, rng, filename="shelf_2conn_line.vox", save=True):
    """2-conn line: connections N, S (open). Exposed: E, W."""
    m = VoxelModel()
    place_back_panel(m, 'W')
    place_back_panel(m, 'E')
    place_shelf_boards(m, 'W', rng)
    place_shelf_boards(m, 'E', rng)
    place_frame_edges(m, ['W', 'E'], rng)
    bays = [range(0, 32)]
    for z_s, z_e in LEVEL_RANGES:
        place_books_on_level(m, 'W', bays, z_s, z_e, rng)
        place_books_on_level(m, 'E', bays, z_s, z_e, rng)
    place_base_molding(m, ['W', 'E'], rng)
    place_crown_molding(m, ['W', 'E'], rng)
    place_gallery_lips(m, ['W', 'E'], rng)
    place_top_grain(m, rng, range(0, 32), range(0, 32))
    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m


def generate_shelf_2conn_corner(palette, output_dir, rng, filename="shelf_2conn_corner.vox", save=True):
    """2-conn corner: connections N, E (open). Exposed: S, W."""
    m = VoxelModel()
    cs = CORNER_SIZE
    bp = SHELF_DEPTH + BACK_THICKNESS
    # Back panels — L-shape, each only extends to where the other face's shelf begins
    sd, bt = SHELF_DEPTH, BACK_THICKNESS
    m.fill(range(sd, sd + bt), range(32 - sd), range(SHELF_STRUCT_TOP), WOOD_DARK)   # W
    m.fill(range(sd + bt, 32), range(32 - sd - bt, 32 - sd), range(SHELF_STRUCT_TOP), WOOD_DARK)  # S
    place_shelf_boards(m, 'W', rng, a_range=range(32 - BOOK_FACE_DEPTH))  # y=0..26
    place_shelf_boards(m, 'S', rng, a_range=range(BOOK_FACE_DEPTH, 32))  # x=5..31
    m.fill(range(bp, 32), range(0, 32 - bp), range(SHELF_STRUCT_TOP), WOOD_MED_DARK)
    # Corner backing with vertical grain streaks per column
    corner_tones = GRAIN_BODY
    for x in range(BOOK_FACE_DEPTH):
        for y in range(32 - BOOK_FACE_DEPTH, 32):
            cur = rng.choice(corner_tones)
            left = rng.randint(5, 12)
            for z in range(SHELF_STRUCT_TOP):
                if left <= 0:
                    cur = rng.choice(corner_tones)
                    left = rng.randint(5, 12)
                m.set(x, y, z, cur)
                left -= 1
    place_frame_edges(m, ['W', 'S'], rng)
    w_bays = [range(0, 32 - SHELF_DEPTH)]        # y=0..17
    s_bays = [range(BOOK_FACE_DEPTH, 32)]       # x=5..31
    for z_s, z_e in LEVEL_RANGES:
        place_books_on_level(m, 'W', w_bays, z_s, z_e, rng)
        place_books_on_level(m, 'S', s_bays, z_s, z_e, rng)
    place_base_molding(m, ['W', 'S'], rng)
    place_gallery_lips(m, ['W', 'S'], rng, a_ranges={
        'W': range(0, 31),
        'S': range(1, 32),
    })
    place_crown_molding(m, ['W', 'S'], rng)
    place_corner_crown(m, 'NE', rng)
    place_top_grain(m, rng, range(0, 32), range(0, 32))
    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m


def generate_shelf_1conn(palette, output_dir, rng, filename="shelf_1conn.vox", save=True):
    """1-conn dead end: connection N only. Books on E, W. Thin wood end panel on S."""
    m = VoxelModel()
    ep = END_PANEL_THICKNESS
    bp = SHELF_DEPTH + BACK_THICKNESS
    place_back_panel(m, 'W')
    place_back_panel(m, 'E')
    place_shelf_boards(m, 'W', rng)
    place_shelf_boards(m, 'E', rng)
    m.fill(range(bp, 32 - bp), range(0, 32 - bp), range(SHELF_STRUCT_TOP), WOOD_MED_DARK)
    place_frame_edges(m, ['W', 'E'], rng)
    # Books stop before the end panel so they don't punch through
    bays = [range(0, 32 - ep)]
    for z_s, z_e in LEVEL_RANGES:
        place_books_on_level(m, 'W', bays, z_s, z_e, rng)
        place_books_on_level(m, 'E', bays, z_s, z_e, rng)
    place_base_molding(m, ['W', 'E', 'S'], rng)
    place_crown_molding(m, ['W', 'E', 'S'], rng)
    place_gallery_lips(m, ['W', 'E'], rng)
    place_top_grain(m, rng, range(0, 32), range(0, 32))
    # End panel last so it overwrites any W/E bleed-through at y=31
    place_end_panel(m, 'S', rng)
    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m


def generate_shelf_1conn_2height(palette, output_dir, rng, filename="shelf_1conn_2height.vox", save=True):
    """1-conn dead end at 2-level height (entrance gateway pillar).
    Connection N only. Books on E, W. End panel on S. Crown at z=60."""
    cfg = SHELF_CFG_2H
    m = VoxelModel()
    ep = END_PANEL_THICKNESS
    bp = SHELF_DEPTH + BACK_THICKNESS
    place_back_panel(m, 'W', cfg=cfg)
    place_back_panel(m, 'E', cfg=cfg)
    place_shelf_boards(m, 'W', rng, cfg=cfg)
    place_shelf_boards(m, 'E', rng, cfg=cfg)
    m.fill(range(bp, 32 - bp), range(0, 32 - bp), range(SHELF_STRUCT_TOP_2H), WOOD_MED_DARK)
    place_frame_edges(m, ['W', 'E'], rng, cfg=cfg)
    bays = [range(0, 32 - ep)]
    for z_s, z_e in LEVEL_RANGES_2H:
        place_books_on_level(m, 'W', bays, z_s, z_e, rng)
        place_books_on_level(m, 'E', bays, z_s, z_e, rng)
    place_base_molding(m, ['W', 'E', 'S'], rng)
    place_crown_molding(m, ['W', 'E', 'S'], rng, cfg=cfg)
    place_gallery_lips(m, ['W', 'E'], rng, cfg=cfg)
    place_top_grain(m, rng, range(0, 32), range(0, 32), cfg=cfg)
    place_end_panel(m, 'S', rng, cfg=cfg)
    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m


def generate_shelf_2conn_3to2height(palette, output_dir, rng, filename="shelf_2conn_3to2height.vox", save=True):
    """2-conn line with full 3-level height, but S face transitions to 2-level.
    Connections N, S. Books on W, E. Top level stops at S end panel.
    S end panel covers only top level. Crown at full height on all faces."""
    m = VoxelModel()
    ep = END_PANEL_THICKNESS
    bp = SHELF_DEPTH + BACK_THICKNESS
    # Full 3-level structure: back panels, boards, frame edges
    place_back_panel(m, 'W')
    place_back_panel(m, 'E')
    place_shelf_boards(m, 'W', rng)
    place_shelf_boards(m, 'E', rng)
    place_frame_edges(m, ['W', 'E'], rng)
    # Bottom 2 levels: books flow through full width (2conn_line behavior)
    bays_full = [range(0, 32)]
    for z_s, z_e in LEVEL_RANGES[:2]:
        place_books_on_level(m, 'W', bays_full, z_s, z_e, rng)
        place_books_on_level(m, 'E', bays_full, z_s, z_e, rng)
    # Top level: books stop before the S end panel
    bays_short = [range(0, 32 - ep)]
    z_s, z_e = LEVEL_RANGES[2]
    place_books_on_level(m, 'W', bays_short, z_s, z_e, rng)
    place_books_on_level(m, 'E', bays_short, z_s, z_e, rng)
    # S face: partial end panel for top level only (raised 4 voxels to meet 2-height shelf)
    place_end_panel(m, 'S', rng, z_bottom=BOARD_ZS[2] + 4, z_top=SHELF_STRUCT_TOP,
                    recess_z_bottom=BOARD_ZS[2] + 4 + 10)
    # Interior fill behind S end panel at top level
    m.fill(range(bp, 32 - bp), range(32 - ep, 32), range(BOARD_ZS[2] + 4, SHELF_STRUCT_TOP), WOOD_MED_DARK)
    # Base molding on W, E faces only (S has no base — it's open at bottom 2 levels)
    place_base_molding(m, ['W', 'E'], rng)
    # S face: base molding as structural plinth
    place_base_molding(m, ['S'], rng)
    # Crown at full 3-level height on all visible faces
    place_crown_molding(m, ['W', 'E', 'S'], rng)
    place_gallery_lips(m, ['W', 'E'], rng)
    place_top_grain(m, rng, range(0, 32), range(0, 32))
    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m


# ============================================================
# 6b. Entrance plaque
# ============================================================

# 5×7 bitmap font for plaque letters (1 = filled, 0 = empty).
# Each entry is 7 rows × 5 columns.
# Uppercase: full height (rows 0-6).  Lowercase: x-height rows 2-6, ascenders row 0.
PLAQUE_FONT = {
    'T': [
        [1,1,1,1,1],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
    ],
    'H': [
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    'E': [
        [1,1,1,1,1],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,1],
    ],
    'L': [
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,1],
    ],
    'I': [
        [1,1,1,1,1],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [1,1,1,1,1],
    ],
    'B': [
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
    ],
    'R': [
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
        [1,0,0,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    'A': [
        [0,0,1,0,0],
        [0,1,0,1,0],
        [1,0,0,0,1],
        [1,1,1,1,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    'Y': [
        [1,0,0,0,1],
        [0,1,0,1,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
    ],
    'O': [
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [0,1,1,1,0],
    ],
    'F': [
        [1,1,1,1,1],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
    ],
    'N': [
        [1,0,0,0,1],
        [1,1,0,0,1],
        [1,0,1,0,1],
        [1,0,0,1,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    # --- Lowercase (x-height rows 2-6, ascenders reach row 0) ---
    'a': [
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,1,1,1,0],
        [0,0,0,0,1],
        [0,1,1,1,1],
        [1,0,0,0,1],
        [0,1,1,1,1],
    ],
    'b': [
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
    ],
    'e': [
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,1,1,1,1],
        [1,0,0,0,0],
        [0,1,1,1,0],
    ],
    'f': [
        [0,0,1,1,0],
        [0,1,0,0,0],
        [1,1,1,1,0],
        [0,1,0,0,0],
        [0,1,0,0,0],
        [0,1,0,0,0],
        [0,1,0,0,0],
    ],
    'h': [
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,1,1,0],
        [1,1,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    'i': [
        [0,0,1,0,0],
        [0,0,0,0,0],
        [0,1,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,1,1,1,0],
    ],
    'l': [
        [0,1,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,1,1,1,0],
    ],
    'n': [
        [0,0,0,0,0],
        [0,0,0,0,0],
        [1,0,1,1,0],
        [1,1,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    'o': [
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [0,1,1,1,0],
    ],
    'r': [
        [0,0,0,0,0],
        [0,0,0,0,0],
        [1,0,1,1,0],
        [1,1,0,0,1],
        [1,0,0,0,0],
        [1,0,0,0,0],
        [1,0,0,0,0],
    ],
    't': [
        [0,1,0,0,0],
        [0,1,0,0,0],
        [1,1,1,1,0],
        [0,1,0,0,0],
        [0,1,0,0,0],
        [0,1,0,0,0],
        [0,0,1,1,0],
    ],
    'y': [
        [0,0,0,0,0],
        [0,0,0,0,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [0,1,0,1,0],
        [0,0,1,0,0],
        [0,1,0,0,0],
    ],
    ' ': [
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
    ],
}

# 9×14 variable-width bitmap font for plaque text.
# 14 rows tall. Cap height rows 0-10, x-height rows 4-10, descenders rows 11-13.
# Most glyphs 9 cols wide (active area + 1 col right padding).
# Narrow glyphs (i, l) are 5 cols wide; space is 5 cols wide.
PLAQUE_FONT_LG = {
    'L': [
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,1,1,1,1,1,0,0],
        [1,1,1,1,1,1,1,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
    ],
    'B': [
        [1,1,1,1,1,1,0,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,1,1,1,1,0,0,0],
        [1,1,1,1,1,1,0,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,1,1,1,1,0,0,0],
        [1,1,1,1,1,1,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
    ],
    'i': [
        [0,0,0,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,0,0,0,0],
        [1,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [1,1,1,1,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
    ],
    'b': [
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,1,1,1,0,0,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,1,1,1,1,0,0,0],
        [1,1,1,1,1,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
    ],
    'r': [
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [1,1,0,1,1,1,0,0,0],
        [1,1,1,0,0,1,1,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
    ],
    'a': [
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,1,1,1,1,1,0,0,0],
        [0,0,0,0,0,1,1,0,0],
        [0,1,1,1,1,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [0,1,1,1,1,1,1,0,0],
        [0,1,1,1,0,1,1,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
    ],
    'y': [
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [0,1,1,0,1,1,0,0,0],
        [0,0,1,1,1,0,0,0,0],
        [0,0,0,1,1,0,0,0,0],
        [0,0,0,1,1,0,0,0,0],
        [0,0,1,1,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
    ],
    'o': [
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,1,1,1,1,1,0,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,0,0,0,1,1,0,0],
        [0,1,1,1,1,1,0,0,0],
        [0,1,1,1,1,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
    ],
    'f': [
        [0,0,0,1,1,1,0,0,0],
        [0,0,1,1,0,1,1,0,0],
        [0,0,1,1,0,0,0,0,0],
        [0,0,1,1,0,0,0,0,0],
        [1,1,1,1,1,1,0,0,0],
        [0,0,1,1,0,0,0,0,0],
        [0,0,1,1,0,0,0,0,0],
        [0,0,1,1,0,0,0,0,0],
        [0,0,1,1,0,0,0,0,0],
        [0,0,1,1,0,0,0,0,0],
        [0,0,1,1,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
    ],
    'e': [
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,1,1,1,1,1,0,0,0],
        [1,1,0,0,0,1,1,0,0],
        [1,1,1,1,1,1,1,0,0],
        [1,1,0,0,0,0,0,0,0],
        [1,1,0,0,0,0,0,0,0],
        [0,1,1,1,1,1,0,0,0],
        [0,1,1,1,1,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0],
    ],
    'l': [
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,0,0],
        [0,1,1,1,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
    ],
    ' ': [
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
        [0,0,0,0,0],
    ],
}

# Lighter brass for letters (readability), darker brass for trim
BRASS_LETTER_TONES = [METAL_LIGHT, 131, 132]
BRASS_TRIM_TONES = [METAL_DARK, 127, METAL_MEDIUM]


def _render_text_line(text, scale=1, font=None, char_w=5, char_h=7, spacing=None):
    """Render a line of text into a 2D bitmap (list of rows, each a list of bool).
    Returns (bitmap, pixel_width).
    Variable-width: if char_w=0, reads per-glyph width from len(glyph[0])."""
    if font is None:
        font = PLAQUE_FONT
    if spacing is None:
        spacing = scale
    glyph_h = char_h * scale
    chars = list(text)
    # Pre-compute per-glyph widths
    widths = []
    for ch in chars:
        glyph = font.get(ch, font[' '])
        w = (len(glyph[0]) if char_w == 0 else char_w) * scale
        widths.append(w)
    total_w = sum(widths) + max(0, len(chars) - 1) * spacing if chars else 0
    bitmap = [[False] * total_w for _ in range(glyph_h)]
    x_off = 0
    for ci, ch in enumerate(chars):
        glyph = font.get(ch, font[' '])
        for gy, row in enumerate(glyph):
            for gx, val in enumerate(row):
                if val:
                    for sy in range(scale):
                        for sx in range(scale):
                            px = x_off + gx * scale + sx
                            py = gy * scale + sy
                            if 0 <= px < total_w and 0 <= py < glyph_h:
                                bitmap[py][px] = True
        x_off += widths[ci] + spacing
    return bitmap, total_w


def _render_text_pil(text, font_path, font_size, threshold=100,
                     tracking=0, weight=None):
    """Render text using a TrueType font via Pillow, return (bitmap, width).
    Renders character-by-character with optional tracking (extra inter-char px)
    and variable font weight."""
    font = ImageFont.truetype(font_path, font_size)
    if weight is not None:
        font.set_variation_by_axes([weight])
    # Measure total width with tracking
    advances = [font.getlength(ch) for ch in text]
    total_w = int(sum(advances) + tracking * max(0, len(text) - 1) + 0.5)
    # Get vertical metrics from full text
    full_bbox = font.getbbox(text)
    top = full_bbox[1]
    h = full_bbox[3] - full_bbox[1]
    # Render character by character
    img = Image.new('L', (total_w + 2, h + 2), 0)
    draw = ImageDraw.Draw(img)
    x_cursor = 1.0
    for i, ch in enumerate(text):
        draw.text((x_cursor, 1 - top), ch, fill=255, font=font)
        x_cursor += advances[i] + (tracking if i < len(text) - 1 else 0)
    pixels = img.load()
    bitmap = []
    for y in range(h + 2):
        row = [pixels[x, y] > threshold for x in range(total_w + 2)]
        bitmap.append(row)
    # Trim empty rows top and bottom
    while bitmap and not any(bitmap[0]):
        bitmap.pop(0)
    while bitmap and not any(bitmap[-1]):
        bitmap.pop()
    actual_w = len(bitmap[0]) if bitmap else 0
    return bitmap, actual_w


def generate_entrance_plaque(palette, output_dir, rng, filename="entrance_plaque.vox", save=True):
    """Generate shaped entrance sign on posts with gooseneck lamps.
    160 wide (x) × ~20 deep (y) × 92 tall (z).
    Posts (x=25..28, x=131..134), 12 voxels tall ending at sign bottom.
    Sign x=0..159, z=64..91 (chamfered top+bottom corners).
    Gooseneck arms extend ~10 voxels from SIGN_Y0 face (camera side).
    POST_Y0=14 to leave room for arms+lanterns at low y."""
    m = VoxelModel()
    W = 160

    # --- Posts (shifted up in y to leave room for gooseneck arms) ---
    POST_W, POST_D = 4, 4
    POST_Y0 = 27
    POST_Y1 = POST_Y0 + POST_D - 1          # 17
    POST_Z_TOP = 76
    POST_L_X0 = 27                           # inward by 2
    POST_R_X0 = 129                          # inward by 2

    # --- Sign ---
    SIGN_X0 = 0
    SIGN_X1 = 159
    SIGN_Y0 = POST_Y0                        # 5
    SIGN_Y1 = SIGN_Y0 + 4                    # 9  (5 deep)
    SIGN_Z_BOT = POST_Z_TOP                  # 64
    SIGN_Z_PEAK = 103                         # sign = z 76..103
    CHAMFER_TOP = 8
    CHAMFER_BOT = 6

    # --- Gooseneck lamp arms ---

    def sign_z_top(x):
        dx = min(x - SIGN_X0, SIGN_X1 - x)
        if dx < CHAMFER_TOP:
            return SIGN_Z_PEAK - (CHAMFER_TOP - dx)
        return SIGN_Z_PEAK

    def sign_z_bot(x):
        dx = min(x - SIGN_X0, SIGN_X1 - x)
        if dx < CHAMFER_BOT:
            return SIGN_Z_BOT + (CHAMFER_BOT - dx)
        return SIGN_Z_BOT

    def streak(tones, length):
        """Generate a streak pattern: long runs of same tone, like real wood."""
        pat, cur = [], rng.choice(tones)
        left = rng.randint(5, 12)
        for _ in range(length):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(5, 12)
            pat.append(cur); left -= 1
        return pat

    # --- 2. Posts (12 voxels tall) ---
    POST_Z_BOT = POST_Z_TOP - 11             # z=65..76 inclusive = 12 voxels
    for px0 in [POST_L_X0, POST_R_X0]:
        wood_z_lo = POST_Z_BOT + 2
        wood_z_hi = POST_Z_TOP - 2
        post_z_span = wood_z_hi - wood_z_lo + 1   # 7

        # Wood body with chamfered vertical edges
        for x in range(px0, px0 + POST_W):
            for y in range(POST_Y0, POST_Y1 + 1):
                # Corner voxels of the 4x4 cross-section
                is_x_edge = (x == px0 or x == px0 + POST_W - 1)
                is_y_edge = (y == POST_Y0 or y == POST_Y1)
                if is_x_edge and is_y_edge:
                    continue  # chamfer: skip corner columns
                pat = streak(GRAIN_EXTRA_DARK_WOOD, post_z_span)
                for zi, z in enumerate(range(wood_z_lo, wood_z_hi + 1)):
                    m.set(x, y, z, pat[zi])

        # Brass plinth (2 voxels, wider by 1 on each face)
        for x in range(px0 - 1, px0 + POST_W + 1):
            for y in range(POST_Y0 - 1, POST_Y1 + 2):
                for z in range(POST_Z_BOT, POST_Z_BOT + 2):
                    m.set(x, y, z, METAL_MEDIUM)

        # Brass capital (2 voxels, wider by 1)
        for x in range(px0 - 1, px0 + POST_W + 1):
            for y in range(POST_Y0 - 1, POST_Y1 + 2):
                for z in range(POST_Z_TOP - 1, POST_Z_TOP + 1):
                    m.set(x, y, z, METAL_MEDIUM)

    # --- 3. Sign body: extra-dark wood, front face removed for depth ---
    sign_w = SIGN_X1 - SIGN_X0 + 1
    for z in range(SIGN_Z_BOT, SIGN_Z_PEAK + 1):
        pat = streak(GRAIN_EXTRA_DARK_WOOD, sign_w)
        for xi, x in enumerate(range(SIGN_X0, SIGN_X1 + 1)):
            zt = sign_z_top(x)
            zb = sign_z_bot(x)
            if zb <= z <= zt:
                for y in range(SIGN_Y0, SIGN_Y1 + 1):
                    m.set(x, y, z, pat[xi])

    # --- 4. Double gold border: pops out 1 voxel on front + back ---
    for x in range(SIGN_X0, SIGN_X1 + 1):
        zt = sign_z_top(x)
        zb = sign_z_bot(x)
        for z in range(zb, zt + 1):
            dt = zt - z
            db = z - zb
            dx = min(x - SIGN_X0, SIGN_X1 - x)
            d = min(dx, db, dt)
            if d <= 1 or d == 3:
                m.set(x, SIGN_Y0, z, METAL_LIGHT)
                m.set(x, SIGN_Y1, z, METAL_LIGHT)
                m.set(x, SIGN_Y0 - 1, z, METAL_LIGHT)
                m.set(x, SIGN_Y1 + 1, z, METAL_LIGHT)

    # --- 5. Text: "LIBRARY OF BABEL" using Cinzel serif font ---
    PLAQUE_FONT_PATH = os.path.join(
        os.path.expanduser("~"),
        "AppData/Local/Microsoft/Windows/Fonts/Cinzel-VariableFont_wght.ttf")
    bmp, text_w = _render_text_pil("LIBRARY OF BABEL", PLAQUE_FONT_PATH,
                                    font_size=15, weight=600)
    line_h = len(bmp)

    int_z_bot = SIGN_Z_BOT + 4                     # 68
    int_z_top = SIGN_Z_PEAK - 4                    # 99
    int_h = int_z_top - int_z_bot + 1              # 32
    z_line = int_z_bot + (int_h - line_h) // 2     # vertically centered

    x_off = (W - text_w) // 2
    for ri, row in enumerate(bmp):
        for ci, val in enumerate(row):
            if val:
                x = x_off + ci
                z = z_line + (line_h - 1 - ri)
                zt = sign_z_top(x)
                zb = sign_z_bot(x)
                dt = zt - z
                db = z - zb
                dx = min(x - SIGN_X0, SIGN_X1 - x)
                d = min(dx, db, dt)
                if d >= 4:
                    m.set(x, SIGN_Y0, z, METAL_LIGHT)
                    m.set(x, SIGN_Y1, z, METAL_LIGHT)
                    m.set(x, SIGN_Y0 - 1, z, METAL_LIGHT)
                    m.set(x, SIGN_Y1 + 1, z, METAL_LIGHT)

    # --- 6. Truncated standard lamps on 2-height shelf corners ---
    # Standard lamp (build_lamp) with bottom 10 voxels discarded,
    # sitting on top of the 2-height shelves (z=64) at outer corners,
    # 1 voxel from each edge.
    SHELF_2H_Z_TOP = 65                       # +1 voxel up from shelf top
    LAMP_TRUNCATE = 10                         # discard bottom 10 voxels of lamp

    lamp_tmp = VoxelModel()
    build_lamp(lamp_tmp, base_z=0)

    # Left shelf tile: x=0..31; outer corner at (x=0, y=0)
    # Right shelf tile: x=128..159; outer corner at (x=159, y=0)
    # Lamp is 6x6; "1 voxel from each edge" positions:
    lamp_positions = [
        (26, 0),                              # left lamp
        (128, 0),                             # right lamp
    ]

    for lx_off, ly_off in lamp_positions:
        for (vx, vy, vz), vc in lamp_tmp._v.items():
            if vz >= LAMP_TRUNCATE:
                m.set(lx_off + vx, ly_off + vy,
                      SHELF_2H_Z_TOP + (vz - LAMP_TRUNCATE), vc)

    # --- 7. Materials ---
    # Emissive for lamps
    m.set_material(117, {"_type": "_emit", "_emit": "0.8", "_flux": "3"})
    # Metal for brass palette indices
    for idx in [METAL_DARK, 127, METAL_MEDIUM, METAL_LIGHT, 130, 131, 132]:
        m.set_material(idx, {"_type": "_metal", "_metal": "0.8", "_rough": "0.3"})

    # --- 8. Normalize z to tight bounding box ---
    z_base = 0
    if m._v:
        z_base = min(vz for _, _, vz in m._v)
        if z_base > 0:
            shifted = {}
            for (vx, vy, vz), vc in m._v.items():
                shifted[(vx, vy, vz - z_base)] = vc
            m._v = shifted

    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m, z_base


# ============================================================
# 7. Tile generators
# ============================================================

def _tile_smooth_noise(w, h, rng, grid_w=4, grid_h=2):
    """Generate smooth value noise via bilinear interpolation of a coarse grid."""
    # Coarse grid of random values 0.0-1.0
    gw, gh = grid_w + 1, grid_h + 1
    grid = [[rng.random() for _ in range(gw)] for _ in range(gh)]
    result = [[0.0] * h for _ in range(w)]
    for x in range(w):
        for y in range(h):
            # Map pixel to grid coords
            gx = x / w * grid_w
            gy = y / h * grid_h
            ix, iy = int(gx), int(gy)
            fx, fy = gx - ix, gy - iy
            # Bilinear interpolation
            top = grid[iy][ix] * (1 - fx) + grid[iy][min(ix+1, grid_w)] * fx
            bot = grid[min(iy+1, grid_h)][ix] * (1 - fx) + grid[min(iy+1, grid_h)][min(ix+1, grid_w)] * fx
            result[x][y] = top * (1 - fy) + bot * fy
    return result


def generate_tile(palette, output_dir, variant, rng, save=True):
    """Generate a 32x16x1 natural stone floor tile — warm travertine with sedimentary banding."""
    m = VoxelModel()
    w, h = 32, 16

    # Sorted light to dark by luminance
    tone_ramp = [91, 100, 96, 92, 93, 97, 94, 95, 98, 99]

    # Each variant biases toward a different part of the ramp
    variant_bias = [0.25, 0.30, 0.35, 0.20, 0.40, 0.22, 0.33, 0.28, 0.38, 0.18][variant % 10]

    # 1. Horizontal banding — stretched noise simulates sedimentary layers
    #    Wide grid_w + narrow grid_h = bands that run across the tile
    noise_band = _tile_smooth_noise(w, h, rng, grid_w=8, grid_h=2)
    noise_fine = _tile_smooth_noise(w, h, rng, grid_w=6, grid_h=3)

    for x in range(w):
        for y in range(h):
            v = noise_band[x][y] * 0.8 + noise_fine[x][y] * 0.2
            v = max(0.0, min(1.0, v + variant_bias - 0.3))
            idx = int(v * 5.99)  # 0-5 range (top 6 tones only for soft body)
            m.set(x, y, 0, tone_ramp[idx])

    # 2. Veining — thin wispy lines, 1-2 per tile, darkened only 1 step
    num_veins = rng.randint(1, 2)
    for _ in range(num_veins):
        vy = rng.randint(3, h - 4)
        vx_start = rng.randint(0, 6)
        vx_end = rng.randint(24, w - 1)
        drift = 0
        for vx in range(vx_start, vx_end):
            cur = m.get(vx, vy + drift, 0)
            ci = tone_ramp.index(cur) if cur in tone_ramp else 3
            m.set(vx, vy + drift, 0, tone_ramp[min(ci + 1, 7)])
            # Gentle drift — travertine veins meander slowly
            if rng.random() < 0.15:
                drift += rng.choice([-1, 0, 0, 1])
                drift = max(-1, min(1, drift))

    # 3. Grout edges — darken by 1 step
    for x in range(w):
        for y in [0, h - 1]:
            cur = m.get(x, y, 0)
            ci = tone_ramp.index(cur) if cur in tone_ramp else 3
            m.set(x, y, 0, tone_ramp[min(ci + 2, 9)])
    for y in range(h):
        for x in [0, w - 1]:
            cur = m.get(x, y, 0)
            ci = tone_ramp.index(cur) if cur in tone_ramp else 3
            m.set(x, y, 0, tone_ramp[min(ci + 2, 9)])

    if save:
        m.save(os.path.join(output_dir, f"tile_{variant+1}.vox"), palette)
    return m


# ============================================================
# 8. Semi-circle planter
# ============================================================


# ============================================================
# 9. Square planter (for top of shelf)
# ============================================================

def generate_square_planter(palette, output_dir, rng, filename="planter_square.vox", save=True):
    """16x16 wood planter with lush, naturalistic foliage."""
    if save:
        import random as _random
        rng = _random.Random()  # unique plant every run
    m = VoxelModel()
    pot_size = 16
    wall_h = 5  # pot is 5 tall (z=0..4)
    # Offset pot so overflow foliage fits on all sides without going negative.
    # Target ~32x32 model: off=8, pot=16, off=8.
    off = 8

    # --- Wood grain helper (horizontal streaks like shelf boards) -------
    body_tones = GRAIN_PLANTER
    rim_tones = GRAIN_PLANTER_RIM

    def _wood_streak(tones, length):
        pat = []
        cur = rng.choice(tones)
        left = rng.randint(3, 8)
        for _ in range(length):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(3, 8)
            pat.append(cur)
            left -= 1
        return pat

    # Pre-generate streak patterns per z-row
    wall_patterns = {}
    for z in range(wall_h):
        tones = rim_tones if z == wall_h - 1 else body_tones
        wall_patterns[z] = _wood_streak(tones, pot_size)

    # --- Pot: 1-voxel thick wood walls with grain -----------------------
    for x in range(pot_size):
        for y in range(pot_size):
            px, py = x + off, y + off
            edge = x == 0 or x == pot_size - 1 or y == 0 or y == pot_size - 1
            if edge:
                for z in range(wall_h):
                    # Streak index = position along the wall face
                    if x == 0 or x == pot_size - 1:
                        idx = y
                    else:
                        idx = x
                    c = wall_patterns[z][idx]
                    if rng.random() < 0.12:
                        c = rng.choice(body_tones)
                    m.set(px, py, z, c)
            else:
                # Dirt fill inside — with per-voxel noise
                for z in range(3):
                    dc = rng.choice([DIRT_DARK, DIRT_DARK, DIRT_MED])
                    m.set(px, py, z, dc)
                # Top soil layer: lighter with more variation
                dc = rng.choice([DIRT_MED, DIRT_MED, DIRT_DARK, DIRT_LIGHT])
                m.set(px, py, 3, dc)

    # --- Foliage: wild branching plant with distinct leaf clusters -------
    import math
    rim_z = wall_h - 1     # z=4
    soil_z = wall_h - 1    # z=4, stems start just above dirt (z=3)
    G_BRIGHT = [101, 106, 110, 115]
    G_MID    = [102, 107, 113, 108, 111]
    G_DARK   = [103, 104, 105, 109, 112, 114]
    STEM_TONES = [WOOD_DARK, WOOD_DARKER, WOOD_MED_DARK]
    model_max = pot_size + 2 * off  # 32

    def _in_bounds(lx, ly, lz):
        vx, vy, vz = lx + off, ly + off, soil_z + lz
        return vx >= 0 and vy >= 0 and vz >= 0 and vx < model_max and vy < model_max

    def _set(lx, ly, lz, color):
        """Place voxel in pot-local coords, skip out-of-bounds."""
        if not _in_bounds(lx, ly, lz):
            return
        m.set(lx + off, ly + off, soil_z + lz, color)

    # 26-connected neighbor offsets (includes all diagonals)
    _NBRS_26 = [(dx, dy, dz)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                if (dx, dy, dz) != (0, 0, 0)]

    def _leaf_cluster(cx, cy, cz, r, tones):
        """Grow an organic leaf cluster using Eden growth (26-connected).
        Every leaf is guaranteed connected to the seed at (cx, cy, cz)."""
        target = max(8, int((4.0 / 3.0) * math.pi * r**3 * 0.15))
        r_sq = r * r

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

            # Soft bounding: hard cutoff beyond 1.4r, probabilistic near edge
            dx, dy, dz = pos[0] - cx, pos[1] - cy, pos[2] - cz
            dist_sq = dx * dx + dy * dy + dz * dz
            if dist_sq > r_sq * 3.0:
                continue
            if dist_sq > r_sq * 0.7 and rng.random() < 0.10:
                continue

            placed.add(pos)
            # Fern-arch bias: rise near stem, droop further out
            dist_from_seed = math.sqrt(dx * dx + dy * dy + dz * dz)
            frac_r = dist_from_seed / max(r, 0.1)
            for nd in _NBRS_26:
                np = (pos[0] + nd[0], pos[1] + nd[1], pos[2] + nd[2])
                if np not in placed:
                    frontier.append(np)
                    if frac_r < 0.4 and nd[2] > 0:
                        # Near stem: bias upward (frond rising)
                        frontier.append(np)
                        frontier.append(np)
                    elif frac_r > 0.7 and nd[2] < 0:
                        # Far from stem: bias downward (drooping)
                        for _ in range(4):
                            frontier.append(np)

        # Color by z-position: bright top, dark bottom
        min_z = min(p[2] for p in placed)
        max_z = max(p[2] for p in placed)
        z_range = max(1, max_z - min_z)
        for px, py, pz in placed:
            z_frac = (pz - min_z) / z_range
            if z_frac > 0.6:
                c = rng.choice(tones[0])
            elif z_frac > 0.3:
                c = rng.choice(tones[1])
            else:
                c = rng.choice(tones[2])
            _set(px, py, pz, c)

    def _grow_stem(x, y, z, dx, dy, dz, length):
        """Grow a stem and return its path. Stops at model boundary.
        Each step is clamped to ±1 per axis so voxels stay 26-connected."""
        path = []
        fx, fy, fz = float(x), float(y), float(z)
        for _ in range(length):
            ix, iy, iz = int(round(fx)), int(round(fy)), int(round(fz))
            if not _in_bounds(ix, iy, iz):
                break
            path.append((ix, iy, iz))
            _set(ix, iy, iz, rng.choice(STEM_TONES))
            fx += max(-1.0, min(1.0, dx + rng.uniform(-0.2, 0.2)))
            fy += max(-1.0, min(1.0, dy + rng.uniform(-0.2, 0.2)))
            fz += max(-1.0, min(1.0, dz + rng.uniform(-0.15, 0.15)))
        return path

    # -- Main trunks from soil, spreading outward at varied angles --------
    mid = pot_size // 2  # 8
    # Each trunk: (base_x, base_y, lean_dx, lean_dy, rise_dz, height)
    # Aggressive lean for surrealist untamed overgrowth; cover all quadrants.
    trunks = [
        # Central tall
        (mid,     mid,      0.0,   0.0,  1.0, rng.randint(7, 10)),
        # 8 trunks evenly spaced: N, NE, E, SE, S, SW, W, NW
        (mid,     mid - 2,  0.0,  -0.55, 1.0, rng.randint(6, 9)),   # N
        (mid + 2, mid - 2,  0.45, -0.45, 1.0, rng.randint(6, 9)),   # NE
        (mid + 2, mid,      0.55,  0.0,  1.0, rng.randint(6, 9)),   # E
        (mid + 2, mid + 2,  0.45,  0.45, 1.0, rng.randint(6, 9)),   # SE
        (mid,     mid + 2,  0.0,   0.55, 1.0, rng.randint(6, 9)),   # S
        (mid - 2, mid + 2, -0.45,  0.45, 1.0, rng.randint(6, 9)),   # SW
        (mid - 2, mid,     -0.55,  0.0,  1.0, rng.randint(6, 9)),   # W
        (mid - 2, mid - 2, -0.45, -0.45, 1.0, rng.randint(6, 9)),   # NW
        # 4 tall ones between cardinals for extra fill
        (mid + 1, mid - 1,  0.3,  -0.2,  1.0, rng.randint(8, 11)),
        (mid + 1, mid + 1,  0.2,   0.3,  1.0, rng.randint(8, 11)),
        (mid - 1, mid + 1, -0.2,   0.3,  1.0, rng.randint(8, 11)),
        (mid - 1, mid - 1, -0.3,  -0.2,  1.0, rng.randint(8, 11)),
    ]

    for bx, by, ldx, ldy, ldz, height in trunks:
        path = _grow_stem(bx, by, 0, ldx, ldy, ldz, height)
        if not path:
            continue
        tip_x, tip_y, tip_z = path[-1]

        # Leaf cluster at the tip
        tr = rng.uniform(3.0, 4.5)
        _leaf_cluster(tip_x, tip_y, tip_z, tr,
                      (G_BRIGHT, G_MID, G_DARK))

        # 2-4 side branches splitting off partway up the trunk
        num_branches = rng.randint(2, 4)
        for _ in range(num_branches):
            bi = rng.randint(1, max(1, len(path) - 2))
            bpx, bpy, bpz = path[bi]
            # Branch leans outward more aggressively than parent
            br_dx = ldx * 1.8 + rng.uniform(-0.6, 0.6)
            br_dy = ldy * 1.8 + rng.uniform(-0.6, 0.6)
            br_dz = rng.uniform(0.2, 0.7)
            br_len = rng.randint(3, 6)
            br_path = _grow_stem(bpx, bpy, bpz, br_dx, br_dy, br_dz, br_len)
            if br_path:
                btx, bty, btz = br_path[-1]
                br_r = rng.uniform(2.5, 3.5)
                _leaf_cluster(btx, bty, btz, br_r,
                              (G_BRIGHT, G_MID, G_DARK))

    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m


# ============================================================
# 13. Large sandstone planter
# ============================================================

def generate_sandstone_planter(palette, output_dir, rng, filename="planter_rectangle.vox", save=True):
    """Large rectangular carved sandstone planter (96x32) with foliage."""
    if save:
        import random as _random
        rng = _random.Random()  # unique plant every run

    m = VoxelModel()

    # Rectangle body: 84 wide x 26 deep.  Max outset +2 → 88 x 30.
    body_w = 84
    body_d = 26
    wall_thick = 3
    stone_rows = 20  # z=0..19

    # Offset centers body in 96-wide model (3 tiles); back is flat against a wall
    off_x = 4
    off_y = 0

    # Smooth profile: base step-out, continuous body, rim step-out
    # Outset expands left/right in x and forward in y (back stays at y=0).
    profile = [
        (0,  2,  2, SAND_BASE_TONES),    # Base plinth
        (2,  4,  1, SAND_BODY_TONES),    # Step
        (4,  17, 0, SAND_BODY_TONES),    # Body (continuous)
        (17, 18, 1, SAND_BODY_TONES),    # Rim transition
        (18, 20, 2, SAND_RIM_TONES),     # Rim lip
    ]

    def _sand_streak(tones, length):
        """Subtle sandstone mottling — very long runs with rare shifts."""
        pat = []
        cur = rng.choice(tones)
        left = rng.randint(30, 60)
        for _ in range(length):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(30, 60)
            pat.append(cur)
            left -= 1
        return pat

    # Body rect: x in [2, 93], y in [0, 27]  (92 x 28)
    # Cavity:    x in [5, 90], y in [3, 24]
    bx0 = 2                   # body x start
    by0 = 0                   # body y start (back wall)
    cx0 = bx0 + wall_thick    # cavity x start
    cx1 = bx0 + body_w - 1 - wall_thick  # cavity x end
    cy0 = wall_thick           # cavity y start
    cy1 = by0 + body_d - 1 - wall_thick  # cavity y end

    # Pre-generate streak patterns per z-row
    z_streaks = {}
    for z_start, z_end, outset, tones in profile:
        for z in range(z_start, z_end):
            z_streaks[z] = _sand_streak(tones, body_w + 6)

    # --- Foliage: Eden growth system (reused from square planter) ---
    # Generated BEFORE stone so that stone overwrites any overlapping leaves.
    soil_z = stone_rows - 1
    G_BRIGHT = [101, 106, 110, 115]
    G_MID    = [102, 107, 113, 108, 111]
    G_DARK   = [103, 104, 105, 109, 112, 114]
    STEM_TONES = [WOOD_DARK, WOOD_DARKER, WOOD_MED_DARK]

    # Foliage local coords match stone coords; off_x shifts into model space
    model_w = 96  # 3 tiles; cap plant growth at tile boundary
    model_d = 32  # cap at one tile depth to prevent forward spillover
    mid_x = bx0 + body_w // 2     # center of planter in local coords
    mid_y = body_d // 2

    def _in_bounds(lx, ly, lz):
        vx = lx + off_x
        vy = ly + off_y
        vz = soil_z + lz
        return 0 <= vx < model_w and ly >= 0 and vy < model_d and vz >= 0

    def _set(lx, ly, lz, color):
        if not _in_bounds(lx, ly, lz):
            return
        m.set(lx + off_x, ly + off_y, soil_z + lz, color)

    _NBRS_26 = [(dx, dy, dz)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                if (dx, dy, dz) != (0, 0, 0)]

    def _leaf_cluster(cx, cy, cz, r, tones):
        target = max(8, int((4.0 / 3.0) * math.pi * r**3 * 0.15))
        r_sq = r * r
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
            if dist_sq > r_sq * 4.0:
                continue
            placed.add(pos)
            dist_from_seed = math.sqrt(dx * dx + dy * dy + dz * dz)
            frac_r = dist_from_seed / max(r, 0.1)
            for nd in _NBRS_26:
                np = (pos[0] + nd[0], pos[1] + nd[1], pos[2] + nd[2])
                if np not in placed:
                    frontier.append(np)
                    if frac_r < 0.4 and nd[2] > 0:
                        frontier.append(np)
                        frontier.append(np)
                    elif frac_r > 0.7 and nd[2] < 0:
                        for _ in range(4):
                            frontier.append(np)
        min_z = min(p[2] for p in placed)
        max_z = max(p[2] for p in placed)
        z_range = max(1, max_z - min_z)
        for px, py, pz in placed:
            z_frac = (pz - min_z) / z_range
            if z_frac > 0.6:
                c = rng.choice(tones[0])
            elif z_frac > 0.3:
                c = rng.choice(tones[1])
            else:
                c = rng.choice(tones[2])
            _set(px, py, pz, c)

    def _grow_stem(x, y, z, dx, dy, dz, length):
        """Grow a stem and return its path. Each step clamped to ±1 per axis."""
        path = []
        fx, fy, fz = float(x), float(y), float(z)
        for _ in range(length):
            ix, iy, iz = int(round(fx)), int(round(fy)), int(round(fz))
            if not _in_bounds(ix, iy, iz):
                break
            path.append((ix, iy, iz))
            _set(ix, iy, iz, rng.choice(STEM_TONES))
            fx += max(-1.0, min(1.0, dx + rng.uniform(-0.2, 0.2)))
            fy += max(-1.0, min(1.0, dy + rng.uniform(-0.2, 0.2)))
            fz += max(-1.0, min(1.0, dz + rng.uniform(-0.15, 0.15)))
        return path

    # Trunk distribution: randomly placed, biased toward front/sides
    trunks = []
    num_trunks = rng.randint(40, 50)
    for _ in range(num_trunks):
        tx = rng.randint(cx0, cx1)
        # Bias toward front: 60% front half, 40% back half
        if rng.random() < 0.6:
            ty = rng.randint(mid_y, cy1)
        else:
            ty = rng.randint(cy0, mid_y)
        # Lean outward based on position
        lean_x = (tx - mid_x) / (body_w / 2) * 0.5
        lean_y = (ty - mid_y) / (body_d / 2) * 0.4
        height = rng.randint(10, 18)
        trunks.append((tx, ty, lean_x, lean_y, 1.0, height))

    for bx, by, ldx, ldy, ldz, height in trunks:
        path = _grow_stem(bx, by, 0, ldx, ldy, ldz, height)
        if not path:
            continue
        tip_x, tip_y, tip_z = path[-1]
        tr = rng.uniform(3.5, 5.0)
        _leaf_cluster(tip_x, tip_y, tip_z, tr, (G_BRIGHT, G_MID, G_DARK))

        num_branches = rng.randint(3, 6)
        for _ in range(num_branches):
            bi = rng.randint(1, max(1, len(path) - 2))
            bpx, bpy, bpz = path[bi]
            br_dx = ldx * 1.8 + rng.uniform(-0.6, 0.6)
            br_dy = ldy * 1.8 + rng.uniform(-0.6, 0.6)
            br_dz = rng.uniform(0.2, 0.7)
            br_len = rng.randint(4, 8)
            br_path = _grow_stem(bpx, bpy, bpz, br_dx, br_dy, br_dz, br_len)
            if br_path:
                btx, bty, btz = br_path[-1]
                br_r = rng.uniform(2.5, 4.2)
                _leaf_cluster(btx, bty, btz, br_r, (G_BRIGHT, G_MID, G_DARK))

    # Build stone shell AFTER foliage so stone always takes precedence
    weather_dark = [SAND_MEDIUM, SAND_MED_WARM]  # very subtle weathering
    for z_start, z_end, outset, tones in profile:
        ox0 = bx0 - outset
        ox1 = bx0 + body_w - 1 + outset
        oy1 = by0 + body_d - 1 + outset
        for z in range(z_start, z_end):
            streak = z_streaks[z]
            # Weathering increases toward the base
            z_frac = z / max(stone_rows - 1, 1)
            darken_chance = 0.08 * (1.0 - z_frac)  # ~8% at z=0, ~0% at top
            for x in range(ox0, ox1 + 1):
                for y in range(by0, oy1 + 1):
                    # Inside cavity: skip (hollow above z=1)
                    if cx0 <= x <= cx1 and cy0 <= y <= cy1 and z >= 2:
                        continue
                    c = streak[(x - ox0) % len(streak)]
                    r = rng.random()
                    if r < 0.05:
                        c = rng.choice(tones)
                    elif r < 0.05 + darken_chance:
                        c = rng.choice(weather_dark)
                    m.set(x + off_x, y + off_y, z, c)

    # Fill dirt inside cavity
    for x in range(cx0, cx1 + 1):
        for y in range(cy0, cy1 + 1):
            for z in range(2, stone_rows - 2):
                dc = rng.choice([DIRT_DARK, DIRT_DARK, DIRT_MED])
                m.set(x + off_x, y + off_y, z, dc)
            dc = rng.choice([DIRT_MED, DIRT_MED, DIRT_DARK, DIRT_LIGHT])
            m.set(x + off_x, y + off_y, stone_rows - 2, dc)

    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m


# ============================================================
# 10. Lamp (standalone)
# ============================================================

def generate_lamp(palette, output_dir):
    """Standalone Victorian lamp post."""
    m = VoxelModel()
    build_lamp(m, base_z=0)
    m.set_material(117, {"_type": "_emit", "_emit": "0.8", "_flux": "3"})
    m.save(os.path.join(output_dir, "lamp.vox"), palette)


# ============================================================
# 11. Staircase
# ============================================================

def generate_staircase_treads(palette, output_dir, rng, filename="staircase_treads.vox", save=True):
    """Staircase treads: 10 stepped treads, variable rises."""
    m = VoxelModel()

    RISES = [10, 10, 10, 10, 10, 10, 10, 10, 10, 9]
    NUM_TREADS = 10
    TREAD_DEPTH = 8
    TREAD_THICK = 2
    NOSING = 2
    TREAD_X0, TREAD_X1 = 0, 63                # 64 wide
    Y_OFF = 8                                  # push to far right of 88-wide box

    wood_tones = GRAIN_DARK_WOOD
    tread_w = TREAD_X1 - TREAD_X0 + 1         # 64

    # Cumulative heights: [10, 20, 30, 40, 50, 60, 70, 80, 90, 99]
    cum = []
    total = 0
    for r in RISES:
        total += r
        cum.append(total)

    def streak(tones, length):
        pat, cur = [], rng.choice(tones)
        left = rng.randint(1, 12)
        for _ in range(length):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(5, 12)
            pat.append(cur); left -= 1
        return pat


    # Build tread geometry list — nosing fits within 8-voxel depth
    all_treads = []
    for i in range(NUM_TREADS):
        z_s = cum[i] - 1
        z_b = z_s - TREAD_THICK + 1
        y0 = Y_OFF + i * TREAD_DEPTH
        y1 = min(y0 + TREAD_DEPTH - 1 + NOSING, Y_OFF + NUM_TREADS * TREAD_DEPTH - 1)
        all_treads.append((i, z_s, z_b, y0, y1))

    # ---- Phase 1: Tread planks + surface grain ----
    for i, z_s, z_b, y0, y1 in all_treads:
        m.fill(range(TREAD_X0, TREAD_X1 + 1),
               range(y0, y1 + 1),
               range(z_b, z_s + 1), WOOD_DARK)
        for y in range(y0, y1 + 1):
            pat = streak(wood_tones, tread_w)
            for xi, x in enumerate(range(TREAD_X0, TREAD_X1 + 1)):
                m.set(x, y, z_s, pat[xi])

    # ---- Phase 2: Nosing edge detail + bullnose ----
    # Nosing is the front NOSING voxels of the tread; riser is recessed behind them
    for i, z_s, z_b, y0, y1 in all_treads:
        y_front = y0
        # Front face streak
        pat = streak(wood_tones, tread_w)
        for xi, x in enumerate(range(TREAD_X0, TREAD_X1 + 1)):
            for z in range(z_b, z_s + 1):
                m.set(x, y_front, z, pat[xi])
        # Underside of nosing overhang
        for y in range(y_front, y_front + NOSING):
            pat = streak(wood_tones, tread_w)
            for xi, x in enumerate(range(TREAD_X0, TREAD_X1 + 1)):
                m.set(x, y, z_b, pat[xi])
        # Bullnose: remove bottom-front corner for rounded profile
        for x in range(TREAD_X0, TREAD_X1 + 1):
            m._v.pop((x, y_front, z_b), None)

    # ---- Phase 3: Risers (recessed NOSING voxels behind nosing edge) ----
    for i, z_s, z_b, y0, y1 in all_treads:
        y_face = y0 + NOSING
        r_bot = 0 if i == 0 else cum[i - 1]
        r_top = z_b - 1
        if r_top < r_bot:
            continue
        rh = r_top - r_bot + 1
        for x in range(TREAD_X0, TREAD_X1 + 1):
            pat = streak(wood_tones, rh)
            for zi, z in enumerate(range(r_bot, r_top + 1)):
                m.set(x, y_face, z, pat[zi])

    if save:
        m.save(os.path.join(output_dir, filename), palette, size=(64, 88, 108))
    return m


def generate_staircase_top_tread(palette, output_dir, rng, filename="staircase_top_tread.vox", save=True):
    """Standalone top tread (Pictoria rectangle): 64x8x11.
    Bottom: previous step slab (2), riser (7), top tread slab (2)."""
    m = VoxelModel()

    TREAD_DEPTH = 8
    TREAD_THICK = 2
    NOSING = 2
    TREAD_X0, TREAD_X1 = 0, 63
    HEIGHT = 11  # prev slab(2) + riser(7) + tread slab(2)

    wood_tones = GRAIN_DARK_WOOD
    tread_w = TREAD_X1 - TREAD_X0 + 1

    def streak(tones, length):
        pat, cur = [], rng.choice(tones)
        left = rng.randint(1, 12)
        for _ in range(length):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(5, 12)
            pat.append(cur); left -= 1
        return pat


    # Previous step's back extension: z=0,1 at y=0..NOSING-1
    prev_z_b = 0
    prev_z_s = TREAD_THICK - 1       # 1
    m.fill(range(TREAD_X0, TREAD_X1 + 1),
           range(0, NOSING),
           range(prev_z_b, prev_z_s + 1), WOOD_DARK)
    for y in range(NOSING):
        pat = streak(wood_tones, tread_w)
        for xi, x in enumerate(range(TREAD_X0, TREAD_X1 + 1)):
            m.set(x, y, prev_z_s, pat[xi])

    # Riser: z=2..8 at y=NOSING (recessed)
    r_bot = prev_z_s + 1             # 2
    r_top = HEIGHT - TREAD_THICK - 1  # 8
    rh = r_top - r_bot + 1           # 7
    for x in range(TREAD_X0, TREAD_X1 + 1):
        pat = streak(wood_tones, rh)
        for zi, z in enumerate(range(r_bot, r_top + 1)):
            m.set(x, NOSING, z, pat[zi])

    # Top tread slab: z=9,10 full depth
    z_b = HEIGHT - TREAD_THICK        # 9
    z_s = HEIGHT - 1                  # 10
    m.fill(range(TREAD_X0, TREAD_X1 + 1),
           range(0, TREAD_DEPTH),
           range(z_b, z_s + 1), WOOD_DARK)

    # Surface grain
    for y in range(TREAD_DEPTH):
        pat = streak(wood_tones, tread_w)
        for xi, x in enumerate(range(TREAD_X0, TREAD_X1 + 1)):
            m.set(x, y, z_s, pat[xi])

    # Nosing front face
    pat = streak(wood_tones, tread_w)
    for xi, x in enumerate(range(TREAD_X0, TREAD_X1 + 1)):
        for z in range(z_b, z_s + 1):
            m.set(x, 0, z, pat[xi])

    # Nosing underside grain
    for y in range(NOSING):
        pat = streak(wood_tones, tread_w)
        for xi, x in enumerate(range(TREAD_X0, TREAD_X1 + 1)):
            m.set(x, y, z_b, pat[xi])

    # Bullnose: remove bottom-front corner
    for x in range(TREAD_X0, TREAD_X1 + 1):
        m._v.pop((x, 0, z_b), None)

    if save:
        m.save(os.path.join(output_dir, filename), palette)
    return m


# ============================================================
# 11b. Staircase balustrade
# ============================================================

def generate_staircase_balustrade(palette, output_dir, rng, inside_x=4,
                                  filename="staircase_balustrade.vox", save=True):
    """One balustrade panel for the staircase side.

    Model axes: x=0..4 (5px cross-section), y=0..95 (ascent), z=0..98 (height).
    Closed stringer: 17px thick diagonal band (5 above + 12 below centerline)
    centered on the line through tread top-left corners, clipped to model bounds.

    inside_x: which x face is staircase-facing (4 for left panel, 0 for right).
    """
    m = VoxelModel()

    # Tread geometry (matches generate_staircase_treads / top_tread)
    RISES = [10, 10, 10, 10, 10, 10, 10, 10, 10, 9]
    TREAD_DEPTH = 8
    Y_OFF = 8

    cum = []
    total = 0
    for r in RISES:
        total += r
        cum.append(total)

    # Tread top-left corners: (y_front, z_surface)
    tread_pts = []
    for i in range(len(RISES)):
        tread_pts.append((Y_OFF + i * TREAD_DEPTH, cum[i] - 1))
    # Top tread: front at y=88, surface at z=107
    tread_pts.append((88, 107))

    # Stringer centerline: line from first to last tread top-left corner
    y0_line, z0_line = tread_pts[0]    # (8, 9)
    y1_line, z1_line = tread_pts[-1]   # (88, 107)

    def z_center(y):
        return z0_line + (z1_line - z0_line) * (y - y0_line) / (y1_line - y0_line)

    wood_tones = GRAIN_DARK_WOOD
    stringer_tones = GRAIN_DARK_WOOD

    def streak(tones, length):
        pat, cur = [], rng.choice(tones)
        left = rng.randint(1, 12)
        for _ in range(length):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(5, 12)
            pat.append(cur); left -= 1
        return pat

    # ---- Diagonal stringer ----
    # 18 voxels thick vertically: 5 above centerline, 13 below
    # Cap (top 5) uses lighter grain, body (bottom 13) uses darker grain
    Z_MAX = 111  # stringer clipping; balusters extend beyond this
    for y in range(96):
        zc = z_center(y)
        z_top = round(zc) + 5    # 5 above center
        z_bot = round(zc) - 13   # 13 below center (total 18)

        # Clip to model bounds
        z_top_c = min(z_top, Z_MAX)
        z_bot_c = max(z_bot, 0)

        if z_bot_c > z_top_c:
            continue

        # Cap (top 5 of the band)
        cap_bot = max(z_top - 4, z_bot_c)
        for x in range(5):
            pat = streak(wood_tones, z_top_c - cap_bot + 1)
            for zi, z in enumerate(range(cap_bot, z_top_c + 1)):
                m.set(x, y, z, pat[zi])

        # Body (bottom 13 of the band)
        body_top = min(cap_bot - 1, z_top_c)
        if body_top >= z_bot_c:
            for x in range(5):
                pat = streak(stringer_tones, body_top - z_bot_c + 1)
                for zi, z in enumerate(range(z_bot_c, body_top + 1)):
                    m.set(x, y, z, pat[zi])

    # ---- Grooves ----
    # Side grooves: cut at x=0 and x=4, 2 voxels from top and bottom of band.
    # Remove at gz and gz+1 to fill gaps at rounding transitions.
    # Skip when stringer is clamped at the groove's end to keep surfaces clean.
    SIDE_OFFSETS = [+1, -10]  # +5-4=+1 (4 from top), -13+3=-10 (3 from bottom)
    for y in range(96):
        zc = z_center(y)
        z_top = round(zc) + 5
        z_bot = round(zc) - 13
        z_top_c = min(z_top, Z_MAX)
        z_bot_c = max(z_bot, 0)
        for off in SIDE_OFFSETS:
            if off > 0 and z_top > Z_MAX:
                continue
            if off < 0 and z_bot < 0:
                continue
            if off < 0 and y >= 94:      # lower groove stops 2 before end
                continue
            gz = round(zc) + off
            for g in (gz, gz + 1):
                if z_bot_c <= g <= z_top_c:
                    m._v.pop((0, y, g), None)
                    m._v.pop((4, y, g), None)

    # Groove transitions to horizontal at ascending end
    # Upper: last diagonal at y=87 (z=107,108). Horizontal at z=109 to y=95.
    for y in range(88, 96):
        m._v.pop((0, y, 109), None)
        m._v.pop((4, y, 109), None)
    # Lower: diagonal stopped at y=93. Horizontal for y=94,95.
    last_gz = round(z_center(93)) - 10 + 2 - 1
    for y in range(94, 96):
        m._v.pop((0, y, last_gz), None)
        m._v.pop((4, y, last_gz), None)

    # Fill rounding gap at y=95: stringer bottom jumps 2 voxels due to rounding,
    # leaving a 1-voxel hole 2 below the lower groove.
    fill_z = last_gz - 2
    pat = streak(stringer_tones, 5)
    for x in range(5):
        m.set(x, 95, fill_z, pat[x])

    # Top groove: cut 1 voxel from the inside face on the top surface.
    # Skip when stringer top is clamped to keep end surfaces clean.
    groove_x = inside_x - 1 if inside_x == 4 else inside_x + 1
    for y in range(96):
        zc = z_center(y)
        z_top = round(zc) + 5
        if z_top > Z_MAX:
            continue
        m._v.pop((groove_x, y, z_top), None)
        m._v.pop((groove_x, y, z_top - 1), None)

    # ---- Balusters: + shaped 3x3, one per tread (excluding top tread) ----
    BALUSTER_HEIGHT = 21
    for i in range(len(RISES)):  # 10 balusters, treads 0-9
        y_c = Y_OFF + i * TREAD_DEPTH + 1
        # + shape in x-y plane, centered at (x=2, y=y_c)
        plus_xy = [
            (2, y_c - 1),
            (1, y_c), (2, y_c), (3, y_c),
            (2, y_c + 1),
        ]
        for bx, by in plus_xy:
            z_bot = round(z_center(by)) + 4
            z_top = z_bot + BALUSTER_HEIGHT - 1
            pat = streak(wood_tones, BALUSTER_HEIGHT)
            for zi, z in enumerate(range(z_bot, z_top + 1)):
                m.set(bx, by, z, pat[zi])

    # ---- Rail: 4→3→2 taper, follows stringer incline ----
    RAIL_HEIGHT = 3
    RAIL_Z_OFF = 25  # 1 above baluster tops (balusters end at zc+24)
    NEWEL_Y_RANGES = [(0, 4, 4), (88, 92, 0)]  # (y_start, y_end, extra_z)
    # Rail spans between newel posts (inclusive) so it terminates inside them
    RAIL_Y_START = NEWEL_Y_RANGES[0][0] + 4   # pull back from descending end
    RAIL_Y_END = NEWEL_Y_RANGES[1][1] - 1     # pull back from ascending end
    # Cross-section: bottom 4 wide, middle 3, top 2 (all biased toward x=0)
    RAIL_LAYERS = [
        [0, 1, 2, 3],  # bottom: 4 wide
        [1, 2, 3],     # middle: 3 wide
        [1, 2],         # top: 2 wide
    ]
    for y in range(RAIL_Y_START, RAIL_Y_END + 1):
        zc = z_center(y)
        rz_bot = round(zc) + RAIL_Z_OFF
        pat = streak(GRAIN_DARK_WOOD, RAIL_HEIGHT)
        for zi in range(RAIL_HEIGHT):
            for x in RAIL_LAYERS[zi]:
                m.set(x, y, rz_bot + zi, pat[zi])

    # ---- Horizontal rail for bridge connection (y=93..95) ----
    # After ascending newel posts (y=88..92), a horizontal rail at bridge
    # height connects the staircase to the bridge.
    HORIZ_RAIL_BOT = 131    # bridge rail bottom in staircase model z (zone z=132)
    for y in range(92, 96):
        pat = streak(GRAIN_DARK_WOOD, RAIL_HEIGHT)
        for zi in range(RAIL_HEIGHT):
            for x in RAIL_LAYERS[zi]:
                m.set(x, y, HORIZ_RAIL_BOT + zi, pat[zi])

    # ---- Newel posts: shaped 5x5 at bottom and top of stringer ----
    # Profile (bottom to top): plinth, taper, shaft w/ bands, capital, finial
    # 5x5 = full square, 3x3 = center + cross (like balusters but filled)
    def cross_5x5():
        return [(x, y) for x in range(5) for y in range(5)]

    def cross_3x3(cx=2, cy=2):
        return [(cx + dx, cy + dy) for dx in range(-1, 2) for dy in range(-1, 2)]

    NEWEL_MARGIN = 2  # how far newel tops extend above the rail
    POLE_H = 15       # 3x3 metal pole under lamp head
    LAMP_HEAD_H = 7   # base(1) + housing(3) + top(1) + 3x3(1) + 1x1(1)

    def _m():
        return 127 if rng.random() < 0.30 else METAL_DARK

    for y_start, y_end, extra_z in NEWEL_Y_RANGES:
        # Flat top: must be taller than the rail so rail stops *inside* the post
        z_tops = []
        z_bots = []
        for ny in range(y_start, y_end + 1):
            zc = z_center(ny)
            z_bots.append(round(zc) + 4)  # start above stringer cap, not from bottom
            z_tops.append(round(zc) + RAIL_Z_OFF + RAIL_HEIGHT - 1
                          + NEWEL_MARGIN + extra_z + POLE_H + 1)
        z_base = min(z_bots)
        z_cap = max(z_tops)
        total_h = z_cap - z_base + 1

        # Profile heights (from z_base upward)
        plinth_h = 3
        taper_h = 2
        shaft_h = total_h - plinth_h - taper_h - POLE_H - LAMP_HEAD_H
        if shaft_h < 4:
            shaft_h = max(total_h - plinth_h - POLE_H - LAMP_HEAD_H, 1)
            taper_h = 0

        # Band positions within shaft (relative to shaft start)
        band_positions = set()
        if shaft_h > 8:
            band_positions.add(0)
            band_positions.add(shaft_h - 1)
            mid = shaft_h // 2
            band_positions.add(mid)
            band_positions.add(mid - 1)

        for ny in range(y_start, y_end + 1):
            cy = ny - y_start  # 0..4
            z_cur = z_base
            # Plinth: full 5x5
            for dz in range(plinth_h):
                c = rng.choice(wood_tones)
                for nx in range(5):
                    m.set(nx, ny, z_cur + dz, c)
            z_cur += plinth_h
            # Taper: transition 5x5 to 3x3 (corners removed layer by layer)
            if taper_h >= 1:
                # First taper layer: remove only the 4 actual corners
                c = rng.choice(wood_tones)
                for nx in range(5):
                    for _ny in [ny]:
                        if (nx, cy) in {(0,0),(0,4),(4,0),(4,4)}:
                            continue
                        m.set(nx, _ny, z_cur, c)
                z_cur += 1
            if taper_h >= 2:
                # Second taper layer: 3x3
                c = rng.choice(wood_tones)
                for nx, _cy in cross_3x3():
                    if 0 <= nx < 5 and 0 <= y_start + _cy <= y_end:
                        m.set(nx, y_start + _cy, z_cur, c)
                z_cur += 1
            # Shaft: 3x3 with occasional 5x5 bands
            pat = streak(wood_tones, shaft_h)
            for dz in range(shaft_h):
                is_band = dz in band_positions
                if is_band:
                    for nx in range(5):
                        m.set(nx, ny, z_cur + dz, pat[dz])
                else:
                    for nx, _cy in cross_3x3():
                        if 0 <= nx < 5 and 0 <= y_start + _cy <= y_end:
                            m.set(nx, y_start + _cy, z_cur + dz, pat[dz])
            z_cur += shaft_h
            # Metal pole: 2x2, POLE_H layers
            for dz in range(POLE_H):
                for nx, _cy in [(1, 1), (1, 2), (2, 1), (2, 2)]:
                    if 0 <= y_start + _cy <= y_end:
                        m.set(nx, y_start + _cy, z_cur + dz, _m())
            z_cur += POLE_H
            # Lamp head: base plate, housing, top plate, taper
            # Lantern base plate: 5x5 metal
            for nx in range(5):
                m.set(nx, ny, z_cur, _m())
            z_cur += 1
            # Housing: 3 layers, metal corners + emissive edges
            for hz in range(3):
                for nx in range(5):
                    is_corner = (nx in (0, 4)) and (cy in (0, 4))
                    is_edge = (nx in (0, 4)) or (cy in (0, 4))
                    if is_corner:
                        m.set(nx, ny, z_cur + hz, _m())
                    elif is_edge:
                        m.set(nx, ny, z_cur + hz, LAMP_WARM)
            z_cur += 3
            # Top plate: 5x5 metal
            for nx in range(5):
                m.set(nx, ny, z_cur, _m())
            z_cur += 1
            # Taper: 3x3 metal
            for nx, _cy in cross_3x3():
                if 0 <= nx < 5 and 0 <= y_start + _cy <= y_end:
                    m.set(nx, y_start + _cy, z_cur, _m())
            z_cur += 1
            # Taper: 1x1 cap
            m.set(2, y_start + 2, z_cur, _m())

    if save:
        m.save(os.path.join(output_dir, filename), palette, size=(5, 96, 162))
    return m


# ============================================================
# 12. Bridge
# ============================================================

def generate_bridge_part(palette, output_dir, rng, supported=False, filename=None):
    """Bridge segment: 32 deep (y) × ~82 wide (x), matching staircase railing style.

    supported=True adds support columns reaching down from deck.
    Deck planks are 64 wide (x=16..79), with railings making total ~82 wide.
    Designed to tile end-to-end seamlessly — posts at y=0,8,16,24 so
    the gap after y=24 to the next bridge's y=0 post is identical to
    every other inter-post gap.
    """
    m = VoxelModel()

    BRIDGE_LEN = 32
    DECK_X0, DECK_X1 = 16, 79    # 64 wide planks
    DECK_THICK = 2
    RAILING_H = 18                # 3 above-deck rail + 12 balusters + 3 handrail
    SUPPORT_H = 16                # support below deck
    POST_SPACING = 8              # thick post every 8 y-voxels
    PLANK_WIDTH = 8               # wider planks (joint every 8 rows)
    UNDERSIDE_H = 4               # clearance below deck for detail

    z_off = SUPPORT_H if supported else UNDERSIDE_H
    deck_top = z_off + DECK_THICK - 1
    hr_z_top = deck_top + RAILING_H

    wood_tones = GRAIN_BODY
    plank_joint_tones = GRAIN_JOINT

    def streak(tones, length):
        pat, cur = [], rng.choice(tones)
        left = rng.randint(1, 12)
        for _ in range(length):
            if left <= 0:
                cur = rng.choice(tones)
                left = rng.randint(5, 12)
            pat.append(cur); left -= 1
        return pat

    # ---- Phase 1: Deck fill ----
    m.fill(range(DECK_X0, DECK_X1 + 1), range(BRIDGE_LEN),
           range(z_off, z_off + DECK_THICK), WOOD_MED_DARK)
    for x_range in [range(9, DECK_X0), range(DECK_X1 + 1, 87)]:
        m.fill(x_range, range(BRIDGE_LEN),
               range(z_off, z_off + DECK_THICK), WOOD_MED_DARK)

    # ---- Phase 2: Deck surface grain with wider plank lines ----
    full_w = 87 - 9 + 1  # x=9..86
    for y in range(BRIDGE_LEN):
        if y % PLANK_WIDTH == 0:
            for x in range(DECK_X0, DECK_X1 + 1):
                m.set(x, y, deck_top, rng.choice(plank_joint_tones))
        else:
            pat = streak(wood_tones, full_w)
            for xi, x in enumerate(range(9, 87)):
                m.set(x, y, deck_top, pat[xi])

    # ---- Phase 2b: Deck edge grain (front/back faces, below surface) ----
    for y_face in [0, BRIDGE_LEN - 1]:
        for z in range(z_off, deck_top):
            pat = streak(wood_tones, full_w)
            for xi, x in enumerate(range(9, 87)):
                m.set(x, y_face, z, pat[xi])

    # ---- Phase 2c: Deck underside grain (supported only) ----
    if supported:
        for y in range(BRIDGE_LEN):
            pat = streak(wood_tones, full_w)
            for xi, x in enumerate(range(9, 87)):
                m.set(x, y, z_off, pat[xi])

    # ---- Phase 4: Support structure (supported only) ----
    if supported:
        chamfer3 = {(0, 0), (0, 2), (2, 0), (2, 2)}
        chamfer5 = {(0, 0), (0, 4), (4, 0), (4, 4)}
        col_positions = [
            (13, 1), (13, BRIDGE_LEN - 4),
            (80, 1), (80, BRIDGE_LEN - 4),
        ]

        # Columns: 3x3 chamfered, full height
        for cx, cy in col_positions:
            for dx in range(3):
                for dy in range(3):
                    if (dx, dy) in chamfer3:
                        continue
                    pat = streak(wood_tones, SUPPORT_H)
                    for zi in range(SUPPORT_H):
                        m.set(cx + dx, cy + dy, zi, pat[zi])

        # Capital plates: 5x5 chamfered at column tops
        for cx, cy in col_positions:
            cap_x, cap_y = cx - 1, cy - 1
            for dx in range(5):
                for dy in range(5):
                    if (dx, dy) in chamfer5:
                        continue
                    m.set(cap_x + dx, cap_y + dy, SUPPORT_H - 1,
                          rng.choice(wood_tones))

        # Knee braces: triangular brackets (y-direction, toward span center)
        BRACE_H = 5
        for cx, cy in col_positions:
            y_dir = 1 if cy < BRIDGE_LEN // 2 else -1
            face_y = (cy + 3) if y_dir == 1 else (cy - 1)
            for i in range(BRACE_H):
                z = SUPPORT_H - 1 - i
                extent = BRACE_H - i
                for step in range(extent):
                    by = face_y + step * y_dir
                    if 0 <= by < BRIDGE_LEN:
                        for dx in range(3):
                            m.set(cx + dx, by, z, rng.choice(wood_tones))


    # ---- Phase 5: Profiled bottom rail (extends below deck) + stringer ----
    br_z_bot = z_off - 2
    br_z_top = deck_top + 3
    br_height = br_z_top - br_z_bot + 1  # 7
    for x0_br in [8, 84]:
        # Grain per Z layer — each layer gets its own Y-streak per dx
        for dz in range(br_height):
            z = br_z_bot + dz
            pats_layer = [streak(wood_tones, BRIDGE_LEN) for _ in range(4)]
            for yi in range(BRIDGE_LEN):
                for dx in range(4):
                    if dz == 0 and dx in (0, 3):
                        continue
                    if dz == br_height - 1 and dx in (0, 3):
                        continue
                    m.set(x0_br + dx, yi, z, pats_layer[dx][yi])
    # Stringer trim (matches bottom rail height)
    for outer_x in [12, 83]:
        # Longitudinal grain for side face
        for z in range(br_z_bot, br_z_top + 1):
            pat = streak(wood_tones, BRIDGE_LEN)
            for yi in range(BRIDGE_LEN):
                m.set(outer_x, yi, z, pat[yi])
        # Front/back face grain
        for y_face in [0, BRIDGE_LEN - 1]:
            pat = streak(wood_tones, br_height)
            for zi in range(br_height):
                m.set(outer_x, y_face, br_z_bot + zi, pat[zi])

    # ---- Phase 6: Balusters (3×3 chamfered, matching staircase) ----
    # Every 8y → 4 per bridge: y=3,11,19,27 — tiles with 5-voxel gaps
    chamfer3 = {(0, 0), (0, 2), (2, 0), (2, 2)}
    z_bot_bal = br_z_top
    z_top_bal = hr_z_top - 3  # adjacent to handrail bottom
    bal_h = z_top_bal - z_bot_bal + 1
    baluster_ys = [3, 11, 19, 27]
    for bx0 in [9, 84]:
        for by in baluster_ys:
            for dx in range(3):
                for dy in range(3):
                    if (dx, dy) in chamfer3:
                        continue
                    pat = streak(wood_tones, bal_h)
                    for zi in range(bal_h):
                        m.set(bx0 + dx, by + dy, z_bot_bal + zi, pat[zi])

    # ---- Phase 8: Profiled handrails (4 wide × 3 tall) ----
    for x0_hr in [8, 84]:
        pats_hr = [streak(wood_tones, BRIDGE_LEN) for _ in range(4)]
        for yi in range(BRIDGE_LEN):
            for dz in range(3):
                z = hr_z_top - dz
                for dx in range(4):
                    if dz == 0 and dx in (0, 3):
                        continue
                    if dz == 2 and dx in (0, 3):
                        continue
                    m.set(x0_hr + dx, yi, z, pats_hr[dx][yi])

    if filename is None:
        filename = "bridge_supported.vox" if supported else "bridge.vox"
    m.save(os.path.join(output_dir, filename), palette)


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "generated", "parts")
    shelves_dir = os.path.join(output_dir, "shelves")
    tiles_dir = os.path.join(output_dir, "tiles")
    planters_dir = os.path.join(output_dir, "planters")
    bridge_dir = os.path.join(output_dir, "bridge")
    misc_dir = os.path.join(output_dir, "misc")
    os.makedirs(shelves_dir, exist_ok=True)
    os.makedirs(tiles_dir, exist_ok=True)
    os.makedirs(planters_dir, exist_ok=True)
    os.makedirs(bridge_dir, exist_ok=True)
    os.makedirs(misc_dir, exist_ok=True)
    palette = make_palette()
    rng = random.Random(42)  # deterministic seed

    print("Generating library maze parts...")
    print()

    print("-- Shelves --")
    for i in range(1, 6):
        generate_shelf_3conn(palette, shelves_dir, random.Random(i), f"shelf_3conn_{i}.vox")
    for i in range(1, 6):
        generate_shelf_2conn_line(palette, shelves_dir, random.Random(i), f"shelf_2conn_line_{i}.vox")
    for i in range(1, 6):
        generate_shelf_2conn_corner(palette, shelves_dir, random.Random(i), f"shelf_2conn_corner_{i}.vox")
    for i in range(1, 6):
        generate_shelf_1conn(palette, shelves_dir, random.Random(i), f"shelf_1conn_{i}.vox")
    for i in range(1, 6):
        generate_shelf_1conn_2height(palette, shelves_dir, random.Random(i), f"shelf_1conn_2height_{i}.vox")
    for i in range(1, 6):
        generate_shelf_2conn_3to2height(palette, shelves_dir, random.Random(i), f"shelf_2conn_3to2height_{i}.vox")

    # 6b. Entrance plaque
    print("-- Entrance plaque --")
    generate_entrance_plaque(palette, shelves_dir, random.Random(42))

    # 7. Tiles x10
    print("-- Tiles --")
    for i in range(10):
        generate_tile(palette, tiles_dir, i, rng)

    # 8. Planters
    print("-- Planters --")

    # Square planters (5 variants)
    for i in range(1, 6):
        generate_square_planter(palette, planters_dir, rng, f"planter_square_{i}.vox")

    # Large rectangle planters (5 variants)
    for i in range(1, 6):
        generate_sandstone_planter(palette, planters_dir, rng, f"planter_rectangle_{i}.vox")

    # 10. Lamp
    print("-- Lamp --")
    generate_lamp(palette, misc_dir)

    # 11. Staircase treads + balustrade
    print("-- Staircase treads --")
    generate_staircase_treads(palette, bridge_dir, rng)
    generate_staircase_top_tread(palette, bridge_dir, rng)
    generate_staircase_balustrade(palette, bridge_dir, rng, inside_x=4,
                                  filename="staircase_balustrade_left.vox")
    generate_staircase_balustrade(palette, bridge_dir, rng, inside_x=0,
                                  filename="staircase_balustrade_right.vox")

    # 12. Bridge (now generated inline by generate_zone_voxs.py)

    # Export palette
    save_palette_png(palette, os.path.join(output_dir, "palette.png"))

    print()
    print("Done! All parts written to:", output_dir)
