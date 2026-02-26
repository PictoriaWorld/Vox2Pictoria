using System.Globalization;

namespace Vox2Pictoria;

public class Options
{
    public string VoxRelativePath { get; }
    public List<(string voxRelativePath, int centerX, int centerY)> CombineInputs { get; }
    public int PropertyMinTileX { get; }
    public int PropertyMinTileZ { get; }
    public bool SceneTestRun { get; }
    public bool FullSamples { get; }
    public bool FullResolution { get; }
    public float SunEnergy { get; }
    public float[] SunColor { get; }
    public float AmbientLightStrength { get; }
    public float[] AmbientLightColor { get; }
    public float EmissionCameraCap { get; }
    public float EmissionBounceMultiplier { get; }
    public string ToneMapper { get; }

    // Derived
    public string VoxAbsolutePath { get; }
    public string ObjOutputDirectory { get; }
    public string BinDirectory { get; }
    public string TempDirectory { get; }
    public string RendersDirectory { get; }
    public string ImagesDirectory { get; }
    public string StructureDefinitionsDirectory { get; }
    public string BlenderOptionsPath { get; }

    public Options(string[] args)
    {
        // Defaults
        string? tempVoxRelativePath = null;
        var tempCombineInputs = new List<(string voxRelativePath, int centerX, int centerY)>();
        int tempPropertyMinTileX = 0;
        int tempPropertyMinTileZ = 0;
        bool tempSceneTestRun = false;
        bool tempFullSamples = false;
        bool tempFullResolution = false;
        float tempSunEnergy = 12f;
        float[] tempSunColor = [1f, 1f, 1f];
        float tempAmbientLightStrength = 0.2f;
        float[] tempAmbientLightColor = [1f, 1f, 1f];
        float tempEmissionCameraCap = 3.5f;
        float tempEmissionBounceMultiplier = 3f;
        string tempToneMapper = "AgX";
        string? tempOutputDirectory = null;

        // Parse named arguments
        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "-h" or "--help":
                    PrintHelp();
                    Environment.Exit(0);
                    break;
                case "--min-tile-x":
                    if (i + 1 >= args.Length || !int.TryParse(args[++i], out tempPropertyMinTileX)) throw new ArgumentException("--min-tile-x requires an integer value.");
                    break;
                case "--min-tile-z":
                    if (i + 1 >= args.Length || !int.TryParse(args[++i], out tempPropertyMinTileZ)) throw new ArgumentException("--min-tile-z requires an integer value.");
                    break;
                case "--scene-test-run":
                    tempSceneTestRun = true;
                    break;
                case "--full-samples":
                    tempFullSamples = true;
                    break;
                case "--full-resolution":
                    tempFullResolution = true;
                    break;
                case "--sun-energy":
                    if (i + 1 >= args.Length || !float.TryParse(args[++i], NumberStyles.Float, CultureInfo.InvariantCulture, out tempSunEnergy)) throw new ArgumentException("--sun-energy requires a numeric value.");
                    break;
                case "--sun-color":
                    if (i + 3 >= args.Length) throw new ArgumentException("--sun-color requires three float values (R G B).");
                    for (int j = 0; j < 3; j++)
                        if (!float.TryParse(args[++i], NumberStyles.Float, CultureInfo.InvariantCulture, out tempSunColor[j])) throw new ArgumentException("--sun-color requires three float values (R G B).");
                    break;
                case "--ambient-light-strength":
                    if (i + 1 >= args.Length || !float.TryParse(args[++i], NumberStyles.Float, CultureInfo.InvariantCulture, out tempAmbientLightStrength)) throw new ArgumentException("--ambient-light-strength requires a numeric value.");
                    break;
                case "--ambient-light-color":
                    if (i + 3 >= args.Length) throw new ArgumentException("--ambient-light-color requires three float values (R G B).");
                    for (int j = 0; j < 3; j++)
                        if (!float.TryParse(args[++i], NumberStyles.Float, CultureInfo.InvariantCulture, out tempAmbientLightColor[j])) throw new ArgumentException("--ambient-light-color requires three float values (R G B).");
                    break;
                case "--emission-camera-cap":
                    if (i + 1 >= args.Length || !float.TryParse(args[++i], NumberStyles.Float, CultureInfo.InvariantCulture, out tempEmissionCameraCap)) throw new ArgumentException("--emission-camera-cap requires a numeric value.");
                    break;
                case "--emission-bounce-multiplier":
                    if (i + 1 >= args.Length || !float.TryParse(args[++i], NumberStyles.Float, CultureInfo.InvariantCulture, out tempEmissionBounceMultiplier)) throw new ArgumentException("--emission-bounce-multiplier requires a numeric value.");
                    break;
                case "--tone-mapper":
                    if (i + 1 >= args.Length) throw new ArgumentException("--tone-mapper requires a value (AgX, Filmic, Standard).");
                    tempToneMapper = args[++i];
                    break;
                case "-o" or "--output":
                    if (i + 1 >= args.Length) throw new ArgumentException("--output requires a directory path.");
                    tempOutputDirectory = args[++i];
                    break;
                case "--combine":
                    if (i + 1 >= args.Length) throw new ArgumentException("--combine requires at least one argument of the form \"path cx cy\".");
                    while (i + 1 < args.Length && !args[i + 1].StartsWith('-'))
                    {
                        string combineArg = args[++i];
                        string[] parts = combineArg.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                        if (parts.Length != 3 || !int.TryParse(parts[1], out int cx) || !int.TryParse(parts[2], out int cy)) throw new ArgumentException($"--combine argument must be \"path cx cy\", got: \"{combineArg}\"");
                        tempCombineInputs.Add((parts[0], cx, cy));
                    }
                    if (tempCombineInputs.Count == 0) throw new ArgumentException("--combine requires at least one argument.");
                    break;
                default:
                    if (args[i].StartsWith('-')) throw new ArgumentException($"Unknown option: {args[i]}. Use --help for usage.");
                    if (tempVoxRelativePath != null) throw new ArgumentException($"Unexpected argument: {args[i]}. Vox path was already set to '{tempVoxRelativePath}'.");
                    tempVoxRelativePath = args[i];
                    break;
            }
        }


        // If no vox path specified and --combine is not used, find the first .vox file in the current directory
        if (tempVoxRelativePath == null && tempCombineInputs.Count == 0)
        {
            string[] voxFiles = Directory.GetFiles(Directory.GetCurrentDirectory(), "*.vox");
            if (voxFiles.Length == 0) throw new ArgumentException("No .vox file specified and none found in current directory. Use --help for usage.");
            tempVoxRelativePath = Path.GetFileName(voxFiles[0]);
            Console.WriteLine($"No vox path specified, using: {tempVoxRelativePath}");
        }
        VoxRelativePath = tempVoxRelativePath ?? "";
        CombineInputs = tempCombineInputs;
        PropertyMinTileX = tempPropertyMinTileX;
        PropertyMinTileZ = tempPropertyMinTileZ;
        SceneTestRun = tempSceneTestRun;
        FullSamples = tempFullSamples;
        FullResolution = tempFullResolution;
        SunEnergy = tempSunEnergy;
        SunColor = tempSunColor;
        AmbientLightStrength = tempAmbientLightStrength;
        AmbientLightColor = tempAmbientLightColor;
        EmissionCameraCap = tempEmissionCameraCap;
        EmissionBounceMultiplier = tempEmissionBounceMultiplier;
        ToneMapper = tempToneMapper;

        string resolvedOutputDirectory = tempOutputDirectory != null ? Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), tempOutputDirectory)) : Directory.GetCurrentDirectory();
        TempDirectory = Path.Combine(resolvedOutputDirectory, "temp");
        if (CombineInputs.Count > 0) VoxAbsolutePath = Path.Combine(TempDirectory, "combined.vox");
        else VoxAbsolutePath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), VoxRelativePath));
        RendersDirectory = Path.Combine(TempDirectory, "renders");
        ObjOutputDirectory = Path.Combine(TempDirectory, "obj");
        BlenderOptionsPath = Path.Combine(ObjOutputDirectory, "blender_options.json");
        BinDirectory = Path.Combine(resolvedOutputDirectory, "bin");
        ImagesDirectory = Path.Combine(BinDirectory, "images");
        StructureDefinitionsDirectory = Path.Combine(BinDirectory, "StructureDefinitions");
    }

    private static void PrintHelp()
    {
        Console.WriteLine("""
            Usage: Vox2Pictoria [vox-path] [options]

            Arguments:
              vox-path                                                          Path to the .vox file (default: first .vox in current directory)

            Options:
              --combine "vox-path-1 cx cy" "vox-path-2 cx cy" ...               Combine multiple .vox files into one scene. Each argument is a quoted string with the .vox path and its MagicaVoxel X/Y center position. All .vox files must share the same palette. This option exists to work around MagicaVoxel's project dimensions limit. When specified, this option takes precedence over vox-path.
              --min-tile-x <integer>                                            Minimum tile-X coordinate of the property in Pictoria (default: 0)
              --min-tile-z <integer>                                            Minimum tile-Z coordinate of the property in Pictoria (default: 0)
              --scene-test-run                                                  When specified, only a single 2D image of the full scene is rendered. Useful for previewing. (default: off)
              --full-samples                                                    When specified, renders images at maximum quality (2048 Blender Cycles samples). When not specified, 32 samples are used (faster, useful for previewing). (default: off)
              --full-resolution                                                 When specified, renders a larger image for higher quality after resizing. When not specified, renders a smaller image (faster, useful for previewing). (default: off)
              --sun-energy <float>                                              Blender sun lamp energy (default: 12)
              --sun-color <R> <G> <B>                                           Blender sun lamp color as three floats 0-1 (default: 1 1 1)
              --ambient-light-strength <float>                                  Blender ambient light strength (default: 0.2)
              --ambient-light-color <R> <G> <B>                                 Blender ambient light color as three floats 0-1 (default: 1 1 1)
              --emission-camera-cap <float>                                     Max emission strength visible to camera in Blender. Controls how bright emissive surfaces appear. Use this to avoid blowout. (default: 3.5)
              --emission-bounce-multiplier <float>                              Multiplier for emission strength on bounced light in Blender. Controls how strongly emissive surfaces light up surroundings. (default: 3)
              --tone-mapper <name>                                              Blender tone mapper: AgX, Filmic, or Standard. Affects how colors appear in rendered images. (default: AgX)
              -o, --output <dir>                                                Output directory (default: current directory)
              -h, --help                                                        Show usage information
            """);
    }
}
