# Blender 4.5 LTS+ script for rendering objs created from a .vox file
import bpy
import math
import os
import json
import sys

class BlenderOptions:
    """All options passed from C# to Blender via blender_options.json."""
    def __init__(self, json_path):
        with open(json_path, 'r') as file:
            data = json.load(file)
        self.obj_directory = data["objDirectory"]
        self.renders_directory = data["rendersDirectory"]
        self.bin_directory = data["binDirectory"]
        self.skip_individual_renders = data["skipIndividualRenders"]
        self.full_samples = data["fullSamples"]
        self.ortho_scale = data["orthoScale"]
        self.resolution_width = data["resolutionWidth"]
        self.resolution_height = data["resolutionHeight"]
        self.camera_x = data["cameraX"]
        self.camera_y = data["cameraY"]
        self.camera_z = data["cameraZ"]
        self.sun_energy = data["sunEnergy"]
        self.sun_color = data["sunColor"]
        self.ambient_strength = data["ambientStrength"]
        self.ambient_light_color = data["ambientLightColor"]
        self.emission_camera_cap = data["emissionCameraCap"]
        self.emission_bounce_multiplier = data["emissionBounceMultiplier"]
        self.view_transform = data["viewTransform"]
        self.structure_render_parameters = data["structureRenderParameters"]
        print(f"Directories: obj={self.obj_directory}, renders={self.renders_directory}, bin={self.bin_directory}")
        print(f"Full scene render parameters: ortho_scale={self.ortho_scale}, resolution={self.resolution_width}x{self.resolution_height}, camera=({self.camera_x}, {self.camera_y}, {self.camera_z})")
        print(f"Lighting: sun_energy={self.sun_energy}, sun_color={self.sun_color}, ambient_strength={self.ambient_strength}, ambient_light_color={self.ambient_light_color}, emission_camera_cap={self.emission_camera_cap}, emission_bounce_multiplier={self.emission_bounce_multiplier}, view_transform={self.view_transform}")


if len(sys.argv) < 5:
    raise ValueError("Usage: blender --background --python main.py <blender_options.json>")
blender_options = BlenderOptions(sys.argv[4])

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
camera.data.ortho_scale = blender_options.ortho_scale
# Setup camera - clipping
camera.data.clip_start = 0.001
camera.data.clip_end = 1000
# Setup camera - set camera location
camera.location = (blender_options.camera_x, blender_options.camera_y, blender_options.camera_z)

# Setup scene
# Setup scene - set scene dimensions
bpy.context.scene.render.resolution_x = blender_options.resolution_width
bpy.context.scene.render.resolution_y = blender_options.resolution_height
bpy.context.scene.render.resolution_percentage = 100
# Setup scene - set scene render engine to cycles
bpy.context.scene.render.engine = 'CYCLES'
# Setup scene - set film to transparent
bpy.context.scene.render.film_transparent = True
# Setup scene - hardware
bpy.context.scene.cycles.device = 'GPU'
# Setup scene - set samples
samples = 2048 if blender_options.full_samples else 32
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

# Setup color management
#
# https://github.com/blender/blender/blob/main/release/datafiles/colormanagement/config.ocio
bpy.context.scene.view_settings.view_transform = blender_options.view_transform
if blender_options.view_transform == 'AgX':
    bpy.context.scene.view_settings.look = 'AgX - Medium High Contrast'
elif blender_options.view_transform == 'Filmic':
    bpy.context.scene.view_settings.look = 'Medium High Contrast'
else:
    bpy.context.scene.view_settings.look = 'None'

# Emission rendering optimizations
#
# sample_clamp_indirect was set to 10 by default to reduce fireflies - https://blenderartists.org/t/cycles-default-indirect-light-clamp/1614180/5
# However, now there are dedicated denoisers, so we can disable indirect clamping for maximum color quality - https://devtalk.blender.org/t/light-clamping-make-the-render-overly-saturated/16291
# Note that denoisers are enabled by default in Blender 4.5 LTS.
bpy.context.scene.cycles.sample_clamp_indirect = 0

# Setup world
#
# Set ambient light color and strength
bpy.context.scene.world.node_tree.nodes['Background'].inputs[0].default_value = (blender_options.ambient_light_color[0], blender_options.ambient_light_color[1], blender_options.ambient_light_color[2], 1)
bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value = blender_options.ambient_strength

# Setup lighting
#
# Setup lighting - add sun lamp
bpy.ops.object.light_add(type='SUN', location=(-10.0284, 14.9572, 16.0788))
sun_lamp = bpy.context.active_object
sun_lamp.rotation_euler = (math.radians(-13.867), math.radians(372.021), math.radians(414.172))
sun_lamp.data.energy = blender_options.sun_energy
sun_lamp.data.color = (blender_options.sun_color[0], blender_options.sun_color[1], blender_options.sun_color[2])

# Parse structure_infos.json
structure_info_path = os.path.join(blender_options.bin_directory, "structure_infos.json")
with open(structure_info_path, 'r') as file:
    structure_infos = json.load(file)

# Ensure renders output directory exists
if not os.path.exists(blender_options.renders_directory):
    os.makedirs(blender_options.renders_directory)

def apply_structure_render_parameters(structure_name, camera):
    parameters = blender_options.structure_render_parameters[structure_name]
    camera.data.ortho_scale = parameters["orthoScale"]
    camera.location = (parameters["cameraX"], parameters["cameraY"], parameters["cameraZ"])
    bpy.context.scene.render.resolution_x = parameters["resolutionWidth"]
    bpy.context.scene.render.resolution_y = parameters["resolutionHeight"]


if not blender_options.skip_individual_renders:
    # Set samples, don't need many for volumes
    bpy.context.scene.cycles.samples = 32

    # Import and render volume objs in vox_file_directory/temp/obj
    #
    # Each structure has a volume obj file with name: "<structure name>_volume.obj". For each, import, render, save to output_directory/<structure name>_volume.png and delete the imported obj. If any is missing, print message and exit.
    for structure_info in structure_infos:
        structure_name = structure_info["name"]
        structure_volume_filename = f"{structure_name}_volume.obj"
        structure_volume_filepath = os.path.join(blender_options.obj_directory, structure_volume_filename)

        if os.path.exists(structure_volume_filepath):
            apply_structure_render_parameters(structure_name, camera)
            bpy.ops.wm.obj_import(filepath=structure_volume_filepath)
            bpy.context.scene.render.filepath = os.path.join(blender_options.renders_directory, f"{structure_name}_volume.png")
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
        structure_occluded_faces_filepath = os.path.join(blender_options.obj_directory, structure_occluded_faces_filename)

        if os.path.exists(structure_occluded_faces_filepath):
            apply_structure_render_parameters(structure_name, camera)
            bpy.ops.wm.obj_import(filepath=structure_occluded_faces_filepath)
            bpy.context.scene.render.filepath = os.path.join(blender_options.renders_directory, f"{structure_name}_occludedFaces.png")
            bpy.ops.render.render(write_still=True)
            bpy.ops.object.delete()  # Delete imported occluded faces obj after rendering

# Helpers
def check_and_import_structure_obj(structure_name):
    shape_obj_filename = f"{structure_name}.obj"
    shape_obj_filepath = os.path.join(blender_options.obj_directory, shape_obj_filename)

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

def load_material_properties():
    """Load material properties from special_material_properties.json, which is generated by MtlService and contains material properties that the Blender/MTL combination doesn't fully support."""
    json_path = os.path.join(blender_options.obj_directory, "special_material_properties.json")
    # Read special_material_properties.json
    with open(json_path, 'r') as f:
        grouped = json.load(f)

    glass_props = grouped.get("glass", {})
    emissive_props = grouped.get("emissive", {})
    metal_props = grouped.get("metal", {})
    return glass_props, emissive_props, metal_props

def srgb_to_linear(rgb):
    """Convert an sRGB color (3 channels, 0-1 each) to a linear RGBA tuple. Formula: https://en.wikipedia.org/wiki/SRGB#Transfer_function_(%22gamma%22), Blender linear color space: https://docs.blender.org/manual/en/latest/render/color_management/color_spaces.html"""
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb) + (1.0,)

# TODO incomplete
# - density, phase and media modes are not currently supported
def setup_glass_materials(glass_props):
    """Apply glass material properties from special_material_properties.json to Blender's Principled BSDF materials."""
    # Apply glass material properties
    for mat in bpy.data.materials:
        # Not a glass material
        if not mat.name.startswith("glass_"):
            continue

        # We didn't find properties for this material
        base_name = mat.name.split('.')[0]
        if base_name not in glass_props:
            continue

        # Enable nodes
        if not mat.use_nodes:
            mat.use_nodes = True

        # Get properties for this material
        props = glass_props[base_name]

        # Get Principled BSDF node
        tree = mat.node_tree
        principled = None
        for node in tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break
        if not principled:
            continue

        # Get palette color from JSON (sRGB 0-1) and convert to linear for Blender
        rgb = props['rgb']
        base_color = srgb_to_linear(rgb)

        # Remove the link between texture.png and the BSDF_PRINCIPLED node's Base Color input - we manually set BASE COLOR below.
        for link in list(tree.links):
            if link.to_node == principled and link.to_socket.name == "Base Color":
                tree.links.remove(link)

        principled.inputs["Transmission Weight"].default_value = props['d']
        principled.inputs["Alpha"].default_value = 1.0
        principled.inputs["Base Color"].default_value = base_color
        principled.inputs["IOR"].default_value = props['ior']
        principled.inputs["Roughness"].default_value = props['rough']

        print(f"  Glass material configured: {mat.name} (transmission={props['d']:.2f}, ior={props['ior']:.2f}, roughness={props['rough']:.3f})")

def setup_emissive_materials(emissive_props):
    """Apply emissive material properties from special_material_properties.json. Uses a Light Path trick that allows controlling
    the brightness of emissive materials when viewed from the camera separately from their brightness when lighting other surfaces. This is to avoid emissive materials blowing out in renders."""
    # Apply emissive material properties
    for mat in bpy.data.materials:
        # Not an emissive material
        if not mat.name.startswith("emissive_"):
            continue

        # We didn't find properties for this material
        base_name = mat.name.split('.')[0]
        if base_name not in emissive_props:
            continue

        # Enable nodes
        if not mat.use_nodes:
            mat.use_nodes = True

        # Calculate emission color and strength from Ke values
        ke_r, ke_g, ke_b = emissive_props[base_name]["ke"]
        max_ke = max(ke_r, ke_g, ke_b)
        if max_ke > 1.0:
            emission_color = (ke_r / max_ke, ke_g / max_ke, ke_b / max_ke, 1.0)
            emission_strength = max_ke
        elif max_ke > 0:
            emission_color = (ke_r, ke_g, ke_b, 1.0)
            emission_strength = 1.0
        else:
            continue

        # Light Path trick: camera sees moderate emission (preserves lamp detail/color), bounced/indirect rays get full strength (lights up surrounding surfaces).
        camera_strength = min(emission_strength, blender_options.emission_camera_cap)
        bounce_strength = emission_strength * blender_options.emission_bounce_multiplier

        # Clear existing nodes
        tree = mat.node_tree
        tree.nodes.clear()

        # Light Path node - "Is Camera Ray" output
        light_path = tree.nodes.new('ShaderNodeLightPath')

        # Emission for camera rays (moderate strength, preserves detail)
        emit_camera = tree.nodes.new('ShaderNodeEmission')
        emit_camera.inputs['Color'].default_value = emission_color
        emit_camera.inputs['Strength'].default_value = camera_strength

        # Emission for bounced rays (full strength, lights up surroundings)
        emit_bounce = tree.nodes.new('ShaderNodeEmission')
        emit_bounce.inputs['Color'].default_value = emission_color
        emit_bounce.inputs['Strength'].default_value = bounce_strength

        # Mix Shader: Is Camera Ray → camera emission, otherwise → bounce emission
        mix = tree.nodes.new('ShaderNodeMixShader')
        tree.links.new(light_path.outputs['Is Camera Ray'], mix.inputs['Fac'])
        tree.links.new(emit_bounce.outputs['Emission'], mix.inputs[1])  # Fac=0 (not camera) → bounce
        tree.links.new(emit_camera.outputs['Emission'], mix.inputs[2])  # Fac=1 (camera) → camera

        # Connect to Material Output
        output_node = tree.nodes.new('ShaderNodeOutputMaterial')
        tree.links.new(mix.outputs['Shader'], output_node.inputs['Surface'])

        print(f"  Emissive material configured: {mat.name} (camera_strength={camera_strength:.2f}, bounce_strength={bounce_strength:.2f}, color=({emission_color[0]:.3f}, {emission_color[1]:.3f}, {emission_color[2]:.3f}))")

def setup_metal_materials(metal_props):
    """Apply metal material properties from special_material_properties.json to Blender's Principled BSDF materials."""
    # Apply metal material properties
    for mat in bpy.data.materials:
        # Not a metal material
        if not mat.name.startswith("metal_"):
            continue

        # We didn't find properties for this material
        base_name = mat.name.split('.')[0]
        if base_name not in metal_props:
            continue

        # Enable nodes
        if not mat.use_nodes:
            mat.use_nodes = True

        # Get Principled BSDF node
        tree = mat.node_tree
        principled = None
        for node in tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break
        if not principled:
            continue

        # Get palette color from JSON (sRGB 0-1) and convert to linear for Blender
        props = metal_props[base_name]
        rgb = props['rgb']
        base_color = srgb_to_linear(rgb)

        # Remove the link between texture.png and the BSDF_PRINCIPLED node's Base Color input - we manually set BASE COLOR below.
        for link in list(tree.links):
            if link.to_node == principled and link.to_socket.name == "Base Color":
                tree.links.remove(link)

        principled.inputs["Metallic"].default_value = props['metallic']
        principled.inputs["Roughness"].default_value = props['rough']
        principled.inputs["Specular IOR Level"].default_value = props['spec']
        principled.inputs["IOR"].default_value = props['ior']
        principled.inputs["Base Color"].default_value = base_color

        print(f"  Metal material configured: {mat.name} (metallic={props['metallic']:.3f}, roughness={props['rough']:.3f}, specular={props['spec']:.3f}, ior={props['ior']:.3f})")

# Import structure objs in vox_file_directory/temp/obj
for structure_info in structure_infos:
    check_and_import_structure_obj(structure_info["name"])

    # Make all structure objs invisible to the camera initially if not rendering scene
    if not blender_options.skip_individual_renders:
        make_structure_invisible(structure_info["name"])

# Post-process special materials after all OBJ imports
glass_props, emissive_props, metal_props = load_material_properties()
setup_glass_materials(glass_props)
setup_emissive_materials(emissive_props)
setup_metal_materials(metal_props)

# Set samples
bpy.context.scene.cycles.samples = samples

if blender_options.skip_individual_renders:
    # Render the entire scene and save it as scene.png
    bpy.context.scene.render.filepath = os.path.join(blender_options.renders_directory, "scene.png")
    bpy.ops.render.render(write_still=True)
else:
    # Render each structure obj, one at a time
    for main_structure_info in structure_infos:
        main_structure_name = main_structure_info["name"]

        # Apply per-structure camera and resolution
        apply_structure_render_parameters(main_structure_name, camera)

        # Make structure visible
        make_structure_visible(main_structure_name)

        # Render all shapes of the main structure together
        bpy.context.scene.render.filepath = os.path.join(blender_options.renders_directory, f"{main_structure_name}.png")
        bpy.ops.render.render(write_still=True)

        # Make structure invisible
        make_structure_invisible(main_structure_name)

# Exit with 0 code
sys.exit(0)
