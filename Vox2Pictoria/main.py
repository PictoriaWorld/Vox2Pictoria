# Blender 4.5 LTS+ script for rendering objs created from a .vox file
import bpy
import math
import os
import json
import sys

# Check if command line argument is provided
#
# Note that if we want to manually edit the scene in blender, we can set the directories and skip_individual_renders, then run this script without -b.
if len(sys.argv) < 15:
    raise ValueError(f"Usage: script.py <obj directory> <renders directory> <bin directory> <skip individual renders> <full samples> <ortho_scale> <resolution_x> <resolution_y> <camera_x> <camera_y> <camera_z>")
obj_directory = sys.argv[4]
renders_output_dir = sys.argv[5]
bin_directory = sys.argv[6]
skip_individual_renders = sys.argv[7].lower() in ['true', '1', 't', 'y', 'yes']
full_samples = sys.argv[8].lower() in ['true', '1', 't', 'y', 'yes']
ortho_scale = float(sys.argv[9])
resolution_x = int(sys.argv[10])
resolution_y = int(sys.argv[11])
camera_x = float(sys.argv[12])
camera_y = float(sys.argv[13])
camera_z = float(sys.argv[14])
print(f"OBJ directory: {obj_directory}")
print(f"Renders directory: {renders_output_dir}")
print(f"Bin directory: {bin_directory}")
print(f"Render params: ortho_scale={ortho_scale}, resolution={resolution_x}x{resolution_y}, camera=({camera_x}, {camera_y}, {camera_z})")

# Delete all objects except the camera
for obj in bpy.data.objects:
    if obj.type != 'CAMERA':
        bpy.data.objects.remove(obj, do_unlink=True)

# Setup camera
# Setup camera - set camera rotations
camera = bpy.data.objects['Camera']
camera.rotation_euler = (math.radians(60), math.radians(0), math.radians(-45))
# Setup camera - set camera to orthographic
camera.data.type = 'ORTHO'
camera.data.sensor_fit = 'HORIZONTAL' # Force ortho_scale to always control visible width, regardless of aspect ratio. If we don't set this and the resolution is taller than wide, ortho_scale would control height instead.
camera.data.ortho_scale = ortho_scale
# Setup camera - clipping
camera.data.clip_start = 0.001
camera.data.clip_end = 1000
# Setup camera - set camera location
camera.location = (camera_x, camera_y, camera_z)

# Setup scene
# Setup scene - set scene dimensions
bpy.context.scene.render.resolution_x = resolution_x
bpy.context.scene.render.resolution_y = resolution_y
bpy.context.scene.render.resolution_percentage = 100
# Setup scene - set scene render engine to cycles
bpy.context.scene.render.engine = 'CYCLES'
# Setup scene - set film to transparent
bpy.context.scene.render.film_transparent = True
# Setup scene - hardware
bpy.context.scene.cycles.device = 'GPU'
# Setup scene - set samples
samples = 2048 if full_samples else 32
# Set cycles render devices - auto-detect GPU type (CUDA for NVIDIA, HIP for AMD, etc.)
cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
gpu_type_found = None
for gpu_type in ['CUDA', 'OPTIX', 'HIP', 'ONEAPI']:
    try:
        cycles_prefs.compute_device_type = gpu_type
        cycles_prefs.get_devices_for_type(gpu_type)
        gpu_devices = [d for d in cycles_prefs.devices if d.type != 'CPU']
        if gpu_devices:
            gpu_type_found = gpu_type
            break
    except Exception:
        continue
if gpu_type_found:
    print(f"Using GPU compute type: {gpu_type_found}")
    for device in cycles_prefs.devices:
        device.use = True
        print(f"  Enabled device: {device.name} ({device.type})")
else:
    print("No GPU found, falling back to CPU rendering")
    bpy.context.scene.cycles.device = 'CPU'

# Setup color management - Blender 4.x defaults to AgX, but Filmic is closer to MagicaVoxel's ACES Filmic tone mapping
bpy.context.scene.view_settings.view_transform = 'Filmic'

# Setup world
# Setup world - set surface color to white and strength to 1
bpy.context.scene.world.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1)
bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value = 0.2

# Setup lighting
# Setup lighting - add sun lamp
bpy.ops.object.light_add(type='SUN', location=(-10.0284, 14.9572, 16.0788))
sun_lamp = bpy.context.active_object
sun_lamp.rotation_euler = (math.radians(-13.867), math.radians(372.021), math.radians(414.172))
sun_lamp.data.energy = 12

# Parse structure_infos.json
structure_info_path = os.path.join(bin_directory, "structure_infos.json")
with open(structure_info_path, 'r') as file:
    structure_infos = json.load(file)

# Parse render_params.json (per-structure camera and resolution, written to obj directory)
render_params_path = os.path.join(obj_directory, "render_params.json")
with open(render_params_path, 'r') as file:
    render_params = json.load(file)

# Ensure renders output directory exists
if not os.path.exists(renders_output_dir):
    os.makedirs(renders_output_dir)

def apply_structure_render_params(structure_name, camera):
    params = render_params[structure_name]
    camera.data.ortho_scale = params["orthoScale"]
    camera.location = (params["cameraX"], params["cameraY"], params["cameraZ"])
    bpy.context.scene.render.resolution_x = params["resolutionWidth"]
    bpy.context.scene.render.resolution_y = params["resolutionHeight"]


if not skip_individual_renders:
    # Set samples, don't need many for volumes
    bpy.context.scene.cycles.samples = 32

    # Import and render volume objs in vox_file_directory/temp/obj
    #
    # Each structure has a volume obj file with name: "<structure name>_volume.obj". For each, import, render, save to output_directory/<structure name>_volume.png and delete the imported obj. If any is missing, print message and exit.
    for structure_info in structure_infos:
        structure_name = structure_info["name"]
        structure_volume_filename = f"{structure_name}_volume.obj"
        structure_volume_filepath = os.path.join(obj_directory, structure_volume_filename)

        if os.path.exists(structure_volume_filepath):
            apply_structure_render_params(structure_name, camera)
            bpy.ops.wm.obj_import(filepath=structure_volume_filepath)
            bpy.context.scene.render.filepath = os.path.join(renders_output_dir, f"{structure_name}_volume.png")
            bpy.ops.render.render(write_still=True)
            bpy.ops.object.delete()  # Delete imported volume obj after rendering
        else:
            raise FileNotFoundError(f"Missing OBJ file for {structure_name}: {structure_volume_filepath}")

    # Import and render occluded faces objs in vox_file_directory/temp/obj
    #
    # Some structures have an occluded faces obj file with name: "<structure name>_occludedFaces.obj". For each, import, render, save to output_directory/<structure name>_occludedFaces.png and delete the imported obj. If any is missing, print message and exit.
    for structure_info in structure_infos:
        structure_name = structure_info["name"]
        structure_occluded_faces_filename = f"{structure_name}_occludedFaces.obj"
        structure_occluded_faces_filepath = os.path.join(obj_directory, structure_occluded_faces_filename)

        if os.path.exists(structure_occluded_faces_filepath):
            apply_structure_render_params(structure_name, camera)
            bpy.ops.wm.obj_import(filepath=structure_occluded_faces_filepath)
            bpy.context.scene.render.filepath = os.path.join(renders_output_dir, f"{structure_name}_occludedFaces.png")
            bpy.ops.render.render(write_still=True)
            bpy.ops.object.delete()  # Delete imported occluded faces obj after rendering

# Helpers
def check_and_import_structure_obj(structure_name, obj_directory):
    shape_obj_filename = f"{structure_name}.obj"
    shape_obj_filepath = os.path.join(obj_directory, shape_obj_filename)

    if os.path.exists(shape_obj_filepath):
        bpy.ops.wm.obj_import(filepath=shape_obj_filepath)
        rename_last_imported_object(structure_name) # Blender changes the names of all imported objects to ObjObject.XXX, we manually rename them back to their original names
    else:
        raise FileNotFoundError(f"Missing OBJ file for {structure_name}: {shape_obj_filepath}")

def rename_last_imported_object(new_name):
    last_imported_obj = None
    for obj in bpy.context.scene.objects:
        if obj.select_get():  # Newly imported objects are selected by default
            last_imported_obj = obj
            break

    if last_imported_obj:
        last_imported_obj.name = new_name
        last_imported_obj.data.name = new_name
    else:
        print("No object was imported.")

def make_structure_invisible(structure_name):
    shape_obj = bpy.data.objects.get(structure_name)
    if shape_obj:
        shape_obj.visible_camera = False
    else:
        raise FileNotFoundError(f"Object not found: {structure_name}.obj")

def make_structure_visible(structure_name):
    shape_obj = bpy.data.objects.get(structure_name)
    if shape_obj:
        shape_obj.visible_camera = True
    else:
        raise FileNotFoundError(f"Object not found: {structure_name}.obj")

# Import structure objs in vox_file_directory/temp/obj
for structure_info in structure_infos:
    check_and_import_structure_obj(structure_info["name"], obj_directory)

     # Make all structure objs invisible to the camera initially if not rendering scene
    if not skip_individual_renders:
        make_structure_invisible(structure_info["name"])
    
# Set samples
bpy.context.scene.cycles.samples = samples

if skip_individual_renders:
    # Render the entire scene and save it as scene.png
    bpy.context.scene.render.filepath = os.path.join(renders_output_dir, "scene.png")
    bpy.ops.render.render(write_still=True)
else:
    # Render each structure obj, one at a time
    for main_structure_info in structure_infos:
        main_structure_name = main_structure_info["name"]

        # Apply per-structure camera and resolution
        apply_structure_render_params(main_structure_name, camera)

        # Make structure visible
        make_structure_visible(main_structure_name)

        # Render all shapes of the main structure together
        bpy.context.scene.render.filepath = os.path.join(renders_output_dir, f"{main_structure_name}.png")
        bpy.ops.render.render(write_still=True)

        # Make structure invisible
        make_structure_invisible(main_structure_name)

# Exit with 0 code
sys.exit(0)