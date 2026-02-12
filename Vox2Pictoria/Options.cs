namespace Vox2Pictoria;

public class Options
{
    public string VoxRelativePath { get; }
    public int PropertyMinTileX { get; }
    public int PropertyMinTileZ { get; }
    public bool SceneTestRun { get; }
    public bool FullSamples { get; }
    public bool FullResolution { get; }

    public string VoxAbsolutePath { get; }
    public string VoxDirectory { get; }
    public string ObjOutputDirectory { get; }
    public string BinDirectory { get; }
    public string TempDirectory { get; }
    public string RendersDirectory { get; }
    public string ImagesDirectory { get; }

    public Options(string[] args)
    {
        // Defaults
        string? tempVoxRelativePath = null;
        int tempPropertyMinTileX = 0;
        int tempPropertyMinTileZ = 0;
        bool tempSceneTestRun = false;
        bool tempFullSamples = false;
        bool tempFullResolution = false;
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
                case "-o" or "--output":
                    if (i + 1 >= args.Length) throw new ArgumentException("--output requires a directory path.");
                    tempOutputDirectory = args[++i];
                    break;
                default:
                    if (args[i].StartsWith('-')) throw new ArgumentException($"Unknown option: {args[i]}. Use --help for usage.");
                    if (tempVoxRelativePath != null) throw new ArgumentException($"Unexpected argument: {args[i]}. Vox path was already set to '{tempVoxRelativePath}'.");
                    tempVoxRelativePath = args[i];
                    break;
            }
        }

        // If no vox path specified, find the first .vox file in the current directory
        if (tempVoxRelativePath == null)
        {
            string[] voxFiles = Directory.GetFiles(Directory.GetCurrentDirectory(), "*.vox");
            if (voxFiles.Length == 0) throw new ArgumentException("No .vox file specified and none found in current directory. Use --help for usage.");
            tempVoxRelativePath = Path.GetFileName(voxFiles[0]);
            Console.WriteLine($"No vox path specified, using: {tempVoxRelativePath}");
        }

        VoxRelativePath = tempVoxRelativePath;
        PropertyMinTileX = tempPropertyMinTileX;
        PropertyMinTileZ = tempPropertyMinTileZ;
        SceneTestRun = tempSceneTestRun;
        FullSamples = tempFullSamples;
        FullResolution = tempFullResolution;

        VoxAbsolutePath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), VoxRelativePath));
        VoxDirectory = Path.GetDirectoryName(VoxAbsolutePath) ?? throw new Exception($"Could not get directory of vox file: {VoxAbsolutePath}");

        string resolvedOutputDirectory = tempOutputDirectory != null ? Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), tempOutputDirectory)) : Directory.GetCurrentDirectory();
        TempDirectory = Path.Combine(resolvedOutputDirectory, "temp");
        RendersDirectory = Path.Combine(TempDirectory, "renders");
        ObjOutputDirectory = Path.Combine(TempDirectory, "obj");
        BinDirectory = Path.Combine(resolvedOutputDirectory, "bin");
        ImagesDirectory = Path.Combine(BinDirectory, "images");
    }

    private static void PrintHelp()
    {
        Console.WriteLine("""
            Usage: Vox2Pictoria [vox-path] [options]

            Arguments:
              vox-path                     Path to the .vox file (default: first .vox in current directory)

            Options:
              --min-tile-x <integer>       Minimum tile-X coordinate of the property in Pictoria (default: 0)
              --min-tile-z <integer>       Minimum tile-Z coordinate of the property in Pictoria (default: 0)
              --scene-test-run             When specified, only a single 2D image of the full scene is rendered. Useful for previewing. (default: off)
              --full-samples               When specified, renders images at maximum quality (2048 Blender Cycles samples). When not specified, 32 samples are used (faster, useful for previewing). (default: off)
              --full-resolution            When specified, renders a larger image for higher quality after resizing. When not specified, renders at a smaller image (faster, useful for previewing). (default: off)
              -o, --output <dir>           Output directory (default: current directory)
              -h, --help                   Show usage information
            """);
    }
}
