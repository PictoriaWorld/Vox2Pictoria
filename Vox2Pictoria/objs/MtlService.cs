namespace Vox2Pictoria;

public class MtlService
{
    public static void GenerateMtls(Options options)
    {
        // Structures mtl
        string mtlContent = @"newmtl palette
illum 1
Ka 0.000 0.000 0.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
map_Kd texture.png
";
        File.WriteAllText(Path.Combine(options.ObjOutputDirectory, "structures.mtl"), mtlContent);
        Console.WriteLine("Mtl file generated at: " + Path.Combine(options.ObjOutputDirectory, "structures.mtl"));

        if (!options.SceneTestRun)
        {
            // Volumes mtl
            string sharedMtlContent = @"newmtl red_mtl
Kd 1.0 0.0 0.0
";
            File.WriteAllText(Path.Combine(options.ObjOutputDirectory, "shared.mtl"), sharedMtlContent);
            Console.WriteLine($"Shared MTL created at: {Path.Combine(options.ObjOutputDirectory, "shared.mtl")}");
        }
    }
}