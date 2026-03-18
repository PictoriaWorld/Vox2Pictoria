"""Render the arcade cabinet as a standalone .vox for preview."""
import os
from generate_parts import build_arcade_cabinet, make_palette

output_dir = os.path.join(os.path.dirname(__file__), "generated", "parts")
os.makedirs(output_dir, exist_ok=True)

palette = make_palette()
m = build_arcade_cabinet()
filepath = os.path.join(output_dir, "arcade_cabinet.vox")
m.save(filepath, palette)
print(f"Written: {filepath}")
