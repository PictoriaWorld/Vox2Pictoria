using System.Globalization;
using System.Text;
using System.Text.Json;
using FileToVoxCore.Vox;
using FileToVoxCore.Vox.Chunks;
using FileToVoxCore.Drawing;

namespace Vox2Pictoria;

public class MtlService
{
    private static readonly JsonSerializerOptions _jsonOptions = new() { WriteIndented = true };

    // Writes structures.mtl (named material stubs) and special_material_properties.json to disk, for Blender script main.py.
    //
    // Returns a dictionary mapping palette indices to special material names (e.g. "emissive_5", "glass_10", "metal_3").
    public static Dictionary<int, string> GenerateMtls(Options options, VoxModel model)
    {
        // Write structures.mtl diffuse material
        //
        // All materials have the same base properties and reference texture.png for their hue. We need to have materials with separate names for special materials though - this allows
        // us to assign special material properties passed to Blender via special_material_properties.json to them. Note that we have to do it this way because Blender doesn't support those properties properly/at all
        // when they're included in the MTL file.
        StringBuilder mtlContent = new();
        AppendMaterialStub(mtlContent, "palette", first: true);

        // Build special material properties and write special material stubs to structures.mtl
        Dictionary<int, string> paletteIDToSpecialMaterialNameMap = [];
        var groupedSpecialMaterialProperties = new GroupedSpecialMaterialProperties();
        foreach (MaterialChunk materialChunk in model.MaterialChunks)
        {
            // Each palette index can only have one corresponding material type
            int paletteNumber = materialChunk.Id;
            if (!model.ColorUsed.Contains(paletteNumber)) continue;

            // Determine material name based on type
            string? materialName = null;
            if (materialChunk.Type == MaterialType._emit) materialName = $"emissive_{paletteNumber}";
            else if (materialChunk.Type == MaterialType._glass) materialName = $"glass_{paletteNumber}";
            else if (materialChunk.Type == MaterialType._metal) materialName = $"metal_{paletteNumber}";
            if (materialName == null) continue;
            paletteIDToSpecialMaterialNameMap[paletteNumber] = materialName;

            // MTL stub (same for all special materials, just with different names so blender creates material slots for each)
            AppendMaterialStub(mtlContent, materialName, first: false);

            // Special material properties
            if (materialChunk.Type == MaterialType._emit)
            {

                // Compute HDR emission: emit * 10^flux
                //
                // MagicaVoxel stores _emit (0-1) and _flux (1-5, matches UI power directly)
                double hdrEmission = materialChunk.Emit * Math.Pow(10, materialChunk.Flux);

                Color emitColor = model.Palette[paletteNumber - 1];
                groupedSpecialMaterialProperties.Emissive[materialName] = new EmissiveMaterialProperties([emitColor.R / 255.0 * hdrEmission, emitColor.G / 255.0 * hdrEmission, emitColor.B / 255.0 * hdrEmission]);
            }
            else if (materialChunk.Type == MaterialType._glass)
            {
                Color glassColor = model.Palette[paletteNumber - 1];
                groupedSpecialMaterialProperties.Glass[materialName] = new GlassMaterialProperties(materialChunk.Alpha, materialChunk.Ior, materialChunk.Rough,
                    [glassColor.R / 255.0, glassColor.G / 255.0, glassColor.B / 255.0]);
            }
            else if (materialChunk.Type == MaterialType._metal)
            {
                Color metalColor = model.Palette[paletteNumber - 1];
                groupedSpecialMaterialProperties.Metal[materialName] = new MetalMaterialProperties(materialChunk.Metal, materialChunk.Rough, materialChunk.Specular, materialChunk.Ior,
                    [metalColor.R / 255.0, metalColor.G / 255.0, metalColor.B / 255.0]);
            }
        }

        // Write structures.mtl and special_material_properties.json to disk
        File.WriteAllText(Path.Combine(options.ObjOutputDirectory, "structures.mtl"), mtlContent.ToString());
        Console.WriteLine("Mtl file generated at: " + Path.Combine(options.ObjOutputDirectory, "structures.mtl"));
        File.WriteAllText(Path.Combine(options.ObjOutputDirectory, "special_material_properties.json"), JsonSerializer.Serialize(groupedSpecialMaterialProperties, _jsonOptions));
        Console.WriteLine("Material properties JSON generated at: " + Path.Combine(options.ObjOutputDirectory, "special_material_properties.json"));

        // Log summary of special materials generated
        int emissiveCount = groupedSpecialMaterialProperties.Emissive.Count;
        int glassCount = groupedSpecialMaterialProperties.Glass.Count;
        int metalCount = groupedSpecialMaterialProperties.Metal.Count;
        if (emissiveCount > 0) Console.WriteLine($"  {emissiveCount} emissive material(s) generated");
        if (glassCount > 0) Console.WriteLine($"  {glassCount} glass material(s) generated");
        if (metalCount > 0) Console.WriteLine($"  {metalCount} metal material(s) generated");

        // If we're rendering images for individual structures (not scene test run), we need to render volume images. We choose to render them red, so we create a shared.mtl file with a red diffuse material.
        if (!options.SceneTestRun)
        {
            // Volumes mtl
            string sharedMtlContent = @"newmtl red_mtl
Kd 1.0 0.0 0.0
";
            File.WriteAllText(Path.Combine(options.ObjOutputDirectory, "shared.mtl"), sharedMtlContent);
            Console.WriteLine($"Shared MTL created at: {Path.Combine(options.ObjOutputDirectory, "shared.mtl")}");
        }

        return paletteIDToSpecialMaterialNameMap;
    }

    private static void AppendMaterialStub(StringBuilder mtlContent, string name, bool first)
    {
        if (!first) mtlContent.AppendLine();
        mtlContent.AppendLine(string.Format(CultureInfo.InvariantCulture,
            @"newmtl {0}
illum 1
Ka 0.000 0.000 0.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
map_Kd texture.png", name));
    }
}
