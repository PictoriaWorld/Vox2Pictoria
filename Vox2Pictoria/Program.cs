using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;
using FileToVoxCore.Vox;

namespace Vox2Pictoria;

internal class Program
{
    private static Process? _blenderProcess;

    static async Task Main(string[] args)
    {
        Console.CancelKeyPress += KillBlenderProcess; // Handles Ctrl+C
        AppDomain.CurrentDomain.ProcessExit += KillBlenderProcess; // Handles clicking the X button on the terminal and normal process exit

        try
        {
            // Get options
            var options = new Options(args);

            // Load vox file
            var reader = new VoxReader();
            VoxModel model = reader.LoadModel(options.VoxAbsolutePath);

            // Extract structure data from vox file
            Dictionary<string, StructureInfo> structureNameStructureInfoMap = VoxDataService.ExtractStructureDataFromVox(model, options);

            // Compute render parameters from scene content
            BlenderRenderParameters fullSceneImageBlenderRenderParameters = ComputeFullSceneImageBlenderRenderParameters(structureNameStructureInfoMap, options);

            // Compute per-structure blender render parameters
            ComputePerStructureBlenderRenderParameters(structureNameStructureInfoMap, options);

            // Create structure infos json
            string json = JsonSerializer.Serialize(structureNameStructureInfoMap.Values, new JsonSerializerOptions { WriteIndented = true });
            string jsonFilePath = Path.Combine(options.BinDirectory, "structure_infos.json");
            if (!Directory.Exists(options.BinDirectory)) Directory.CreateDirectory(options.BinDirectory);
            File.WriteAllText(jsonFilePath, json);
            Console.WriteLine("structure_infos created at: " + jsonFilePath + ", num structures: " + structureNameStructureInfoMap.Count);

            // Create obj output directory
            if (!Directory.Exists(options.ObjOutputDirectory)) Directory.CreateDirectory(options.ObjOutputDirectory);

            // Write per-structure render params to a temporary file in the ObjOutputDirectory (consumed by main.py, not end-user facing)
            Dictionary<string, BlenderRenderParameters> blenderRenderParamsMap = [];
            foreach (StructureInfo structureInfo in structureNameStructureInfoMap.Values) blenderRenderParamsMap[structureInfo.Name] = structureInfo.BlenderRenderParameters!;
            string renderParamsJson = JsonSerializer.Serialize(blenderRenderParamsMap, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(Path.Combine(options.ObjOutputDirectory, "render_params.json"), renderParamsJson);

            // Create voxel-frame voxel-infos map
            Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap = VoxelGridService.CreateVoxelFrameVisibleVoxelInfoMap(model);

            // Create voxel grid
            //
            // Used for checking if voxels are occupied
            ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap = [];
            VoxelGridService.GetVisibleVoxelsGrid(structureNameStructureInfoMap, model, voxelFrameVisibleVoxelInfoMap, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap);

            // Generate mtls
            MtlService.GenerateMtls(options);

            // Generate structure objs
            await StructureObjService.GenerateStructureObjsAsync(structureNameStructureInfoMap, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, voxelFrameVisibleVoxelInfoMap, model, options);

            if (!options.SceneTestRun)
            {
                // TODO attempt to calculate pixel locations instead of using volumes > use isometric formulas to find isometric coordinates > map isometric coordinates to render pixels
                // Generate structure volume objs
                await VolumeObjService.GenerateVolumeObjsAsync(structureNameStructureInfoMap, options.ObjOutputDirectory);

                // Generate occluded objs
                await OccludedFacesObjService.GenerateOccludedFacesObjsAsync(structureNameStructureInfoMap, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, voxelFrameVisibleVoxelInfoMap, options);
            }

            // Render objs
            RenderObjs(options, fullSceneImageBlenderRenderParameters);

            if (!options.SceneTestRun)
            {
                // Crop and scale renders
                await PostProcessingService.CropAndScaleRenders(structureNameStructureInfoMap, options);
            }

            // Success
            Console.WriteLine("Vox successfully processed");
            Environment.Exit(0);
        }
        catch (Exception exception)
        {
            Console.WriteLine(exception);
            Environment.Exit(1);
        }
    }

    // Note that these parameters are only used when we render the full scene as a single image (--scene-test-run). But they're cheap to compute so we just always compute them.
    // TODO skip if not needed.
    private static BlenderRenderParameters ComputeFullSceneImageBlenderRenderParameters(Dictionary<string, StructureInfo> structureNameStructureInfoMap, Options options)
    {
        // Compute scene Pictoria isometric bounding rectangle
        double scenePictoriaIsometricMinX = double.MaxValue;
        double scenePictoriaIsometricMaxX = double.MinValue;
        double scenePictoriaIsometricMinY = double.MaxValue;
        double scenePictoriaIsometricMaxY = double.MinValue;
        foreach (StructureInfo structureInfo in structureNameStructureInfoMap.Values)
        {
            IsometricPolygon isometricPolygon = structureInfo.IsometricPolygon!;
            scenePictoriaIsometricMinX = Math.Min(scenePictoriaIsometricMinX, isometricPolygon.MinX);
            scenePictoriaIsometricMaxX = Math.Max(scenePictoriaIsometricMaxX, isometricPolygon.MaxX);
            scenePictoriaIsometricMinY = Math.Min(scenePictoriaIsometricMinY, isometricPolygon.MinY);
            scenePictoriaIsometricMaxY = Math.Max(scenePictoriaIsometricMaxY, isometricPolygon.MaxY);
        }
        double scenePictoriaIsometricWidth = scenePictoriaIsometricMaxX - scenePictoriaIsometricMinX;
        double scenePictoriaIsometricHeight = scenePictoriaIsometricMaxY - scenePictoriaIsometricMinY;

        // Find ortho_scale
        //
        // Terms:
        //   - Blender world coordinate system: 3D coordinates in Blender's coordinate system (before rotations: X is right, Y is into-the-screen, Z is up). OBJ vertices are written in these units - 
        //       they correspond to MagicaVoxel voxels/Pictoria cartesian coordinates divided by 10.
        //   - Blender screen position of a 3D point: Projection of the vector from the origin to the point, onto the unit vector pointing to the right of the screen (after rotations), uBlenderScreenRight. 
        //       Note that this is a 1D (scalar) value that is in blender world units (it's the length of a vector in the Blender world coordinate system).
        //   - ortho_scale: Blender screen position of the furthest right point minus the Blender screen position of the furthest left point. Defines the visible width of the blender scene.
        //       We use sensor_fit='HORIZONTAL', so ortho_scale in blender always controls width.
        //   - Pictoria isometric coordinate system: Pictoria's 2D isometric coordinate system for the plane parallel to the screen. Derived from Pictoria cartesian coordinates via CoordinatesService.cs.
        //   - Pictoria cartesian coordinate system: Pictoria's 3D coordinate system. Related to Blender world units by a factor of 10: pictoria = blender * 10. Equal to MagicaVoxel voxel coordinates.
        //
        // Goal: Find ortho_scale that fits sceneIsometricWidth Pictoria isometric units on screen.
        //
        // Step 1: Find uBlenderScreenRight in Blender world coordinates, after rotations.
        //   - Camera rotation = (60deg, 0deg, -45deg)
        //   - After rotation, the vector pointing to the right of the screen is 45deg counter-clockwise from the -Y axis and 45deg clockwise from the +X axis.
        //   - We calculate its x and y components by projecting it onto the X and Y axes (can use simple trigonometry)
        //   - Result: uBlenderScreenRight = (sqrt(2)/2, -sqrt(2)/2, 0), note that the Z component is 0 - there is no vertical component to the screen right vector.
        //
        // Step 2: Find formula for calculating Blender screen position of a Blender world point (bX, bY, bZ).
        //   - We're just projecting (bX, bY, bZ) onto uBlenderScreenRight.
        //   - blenderScreenPosition = dot((bX,bY,bZ), (sqrt(2)/2, -sqrt(2)/2, 0)) = (bX - bY) * sqrt(2)/2
        //
        // Step 3: Find formula for calculating Pictoria isometric X coordinate of a Blender world point (bX, bY, bZ).
        //   - CoordinatesService.cs: pictoriaIsometricX = pictoriaCartesianX - pictoriaCartesianZ (pictoriaCartesianZ is in the same direction as Blender Y)
        //   - VolumeObjService.cs:24: Blender world units = Pictoria cartesian coordinates / 10
        //   - pictoriaCartesianX = bX * 10, pictoriaCartesianZ = bY * 10:
        //   - pictoriaIsometricX = 10 * (bX - bY)
        //
        // Step 4: Find formula for calculating Blender screen position from Pictoria isometric X.
        //   - From step 2: blenderScreenPosition = (bX - bY) * sqrt(2)/2
        //   - From step 3: pictoriaIsometricX = 10 * (bX - bY), so (bX - bY) = pictoriaIsometricX / 10
        //   - Therefore:  blenderScreenPosition = (pictoriaIsometricX / 10) * sqrt(2)/2 = pictoriaIsometricX * sqrt(2)/20
        //
        // Step 5: Find ortho_scale.
        //   - ortho_scale = blenderScreenPositionMax - blenderScreenPositionMin = (pictoriaIsometricMaxX - pictoriaIsometricMinX) * sqrt(2)/20 = sceneIsometricWidth * sqrt(2)/20 = sceneIsometricWidth / (10 * sqrt(2))
        double orthoScale = scenePictoriaIsometricWidth / (Constants.PictoriaCartesianToBlenderWorldDivisor * Math.Sqrt(2));

        // Output image resolution: supersampling factor * pictoria scene isometric extent
        int supersamplingFactor = options.FullResolution ? 4 : 1;
        int outputImagePixelWidth = (int)Math.Ceiling(scenePictoriaIsometricWidth * supersamplingFactor);
        int outputImagePixelHeight = (int)Math.Ceiling(scenePictoriaIsometricHeight * supersamplingFactor);

        // Camera position
        (double blenderCameraX, double blenderCameraY, double blenderCameraZ) = ComputeBlenderCameraPosition(scenePictoriaIsometricMinX, scenePictoriaIsometricMaxX, scenePictoriaIsometricMinY, scenePictoriaIsometricMaxY);

        Console.WriteLine($"Full scene image Blender render parameters: orthoScale={orthoScale:F4}, resolution={outputImagePixelWidth}x{outputImagePixelHeight}, camera=({blenderCameraX:F4}, {blenderCameraY:F4}, {blenderCameraZ:F4})");

        return new BlenderRenderParameters(orthoScale, outputImagePixelWidth, outputImagePixelHeight, blenderCameraX, blenderCameraY, blenderCameraZ);
    }

    private static void ComputePerStructureBlenderRenderParameters(Dictionary<string, StructureInfo> structureNameStructureInfoMap, Options options)
    {
        int supersamplingFactor = options.FullResolution ? 4 : 1;
        int padding = 8;

        foreach (StructureInfo structureInfo in structureNameStructureInfoMap.Values)
        {
            IsometricPolygon pictoriaIsometricPolygon = structureInfo.IsometricPolygon!;
            double pictoriaIsometricWidth = pictoriaIsometricPolygon.MaxX - pictoriaIsometricPolygon.MinX;
            double pictoriaIsometricHeight = pictoriaIsometricPolygon.MaxY - pictoriaIsometricPolygon.MinY;

            // Find output image resolution from structure's isometric extent
            int outputImagePixelWidth = (int)Math.Ceiling(pictoriaIsometricWidth * supersamplingFactor) + 2 * padding;
            int outputImagePixelHeight = (int)Math.Ceiling(pictoriaIsometricHeight * supersamplingFactor) + 2 * padding;

            // ortho_scale: visible scene width for this structure's render
            //
            // See explanation in ComputeFullSceneImageBlenderRenderParameters. 
            // 
            // Basically orthoScale is the width of the blender scene included in the image. We want to include the structure's full isometric width, plus padding.
            double pictoriaIsometricWidthWithPadding = outputImagePixelWidth / (double)supersamplingFactor;
            double orthoScale = pictoriaIsometricWidthWithPadding / (Constants.PictoriaCartesianToBlenderWorldDivisor * Math.Sqrt(2));

            // Camera centered on this structure's isometric center
            (double blenderCameraX, double blenderCameraY, double blenderCameraZ) = ComputeBlenderCameraPosition(pictoriaIsometricPolygon.MinX, pictoriaIsometricPolygon.MaxX, pictoriaIsometricPolygon.MinY, pictoriaIsometricPolygon.MaxY);

            structureInfo.SetBlenderRenderParameters(new BlenderRenderParameters(orthoScale, outputImagePixelWidth, outputImagePixelHeight, blenderCameraX, blenderCameraY, blenderCameraZ));

            Console.WriteLine($"Per-structure render params for {structureInfo.Name}: orthoScale={orthoScale:F4}, resolution={outputImagePixelWidth}x{outputImagePixelHeight}, camera=({blenderCameraX:F4}, {blenderCameraY:F4}, {blenderCameraZ:F4})");
        }
    }

    /// <summary>
    /// Converts the center of the Pictoria isometric bounding rectangle to a Blender world point (bX, bY, bZ), then makes adjustments to position the camera directed at that point
    /// </summary>
    private static (double cameraX, double cameraY, double cameraZ) ComputeBlenderCameraPosition(double pictoriaIsometricMinX, double pictoriaIsometricMaxX, double pictoriaIsometricMinY, double pictoriaIsometricMaxY)
    {
        // Convert the center of the Pictoria isometric bounding rectangle to the corresponding Blender world point (bX, bY, bZ)
        //
        // This is the "look at" point that the camera will be directed at.
        // The logic here is the inverse of what is documented in ComputeFullSceneImageBlenderRenderParameters step 3

        // Find the center of the Pictoria isometric bounding rectangle in Pictoria isometric coordinates
        double pictoriaIsometricCenterX = (pictoriaIsometricMinX + pictoriaIsometricMaxX) / 2.0;
        double pictoriaIsometricCenterY = (pictoriaIsometricMinY + pictoriaIsometricMaxY) / 2.0;

        // Find the Pictoria cartesian point that projects to the isometric center
        //
        // pictoriaIsometricX = pictoriaCartesianX - pictoriaCartesianZ
        // pictoriaIsometricY = -(pictoriaCartesianX + pictoriaCartesianZ) / 2
        //
        // Using simultaneous equations:
        double pictoriaCartesianX = (pictoriaIsometricCenterX - 2 * pictoriaIsometricCenterY) / 2.0;
        double pictoriaCartesianZ = (-pictoriaIsometricCenterX - 2 * pictoriaIsometricCenterY) / 2.0;

        // Convert to Blender world coordinates
        //
        // bX = pictoriaCartesianX / PictoriaCartesianToBlenderWorldDivisor, bY = pictoriaCartesianZ / PictoriaCartesianToBlenderWorldDivisor (bY corresponds to pictoriaCartesianZ)
        double lookAtX = pictoriaCartesianX / Constants.PictoriaCartesianToBlenderWorldDivisor;
        double lookAtY = pictoriaCartesianZ / Constants.PictoriaCartesianToBlenderWorldDivisor;
        double lookAtZ = 0;

        // Find the camera location by offsetting the look at point along the unit vector perpendicular to the screen plane, pointing out of the screen (uOffset).
        //
        // uOffset, (-sqrt(6)/4, -sqrt(6)/4, 0.5), is derived from rotation (60deg, 0deg, -45deg) - we just project the vector perpendicular to the screen plane, pointing out of the screen, onto the X, Y, and Z axes using 
        // simple trigonometry.
        //
        // Use a fixed large distance (half of clip_end=1000) so the camera is always far outside all
        // scene geometry. For orthographic cameras, distance only affects depth clipping, not framing.
        double uOffsetX = -Math.Sqrt(6) / 4.0;
        double uOffsetY = -Math.Sqrt(6) / 4.0;
        double uOffsetZ = 0.5;
        double dist = 500; // Vector magnitude, arbitrary large distance
        double cameraX = lookAtX + dist * uOffsetX;
        double cameraY = lookAtY + dist * uOffsetY;
        double cameraZ = lookAtZ + dist * uOffsetZ;
        return (cameraX, cameraY, cameraZ);
    }

    private static void RenderObjs(Options options, BlenderRenderParameters fullSceneImageBlenderRenderParameters)
    {
        // Get main.py path
        string mainPyPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "main.py");
        Console.WriteLine($"main.py path: {mainPyPath}");

        using Process process = new();

        process.StartInfo.FileName = GetBlenderPath();
        string orthoScaleString = fullSceneImageBlenderRenderParameters.OrthoScale.ToString(CultureInfo.InvariantCulture);
        string cameraXString = fullSceneImageBlenderRenderParameters.CameraX.ToString(CultureInfo.InvariantCulture);
        string cameraYString = fullSceneImageBlenderRenderParameters.CameraY.ToString(CultureInfo.InvariantCulture);
        string cameraZString = fullSceneImageBlenderRenderParameters.CameraZ.ToString(CultureInfo.InvariantCulture);
        process.StartInfo.Arguments = $"--background --python {mainPyPath} {options.ObjOutputDirectory} {options.RendersDirectory} {options.BinDirectory} {options.SceneTestRun} {options.FullSamples} {orthoScaleString} {fullSceneImageBlenderRenderParameters.ResolutionWidth} {fullSceneImageBlenderRenderParameters.ResolutionHeight} {cameraXString} {cameraYString} {cameraZString}";
        process.StartInfo.UseShellExecute = false;
        process.StartInfo.RedirectStandardOutput = true;
        process.StartInfo.RedirectStandardError = true;
        process.StartInfo.CreateNoWindow = true;
        _blenderProcess = process;
        process.Start();

        while (!process.StandardOutput.EndOfStream)
        {
            string? line = process.StandardOutput.ReadLine();

            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }

            // Filter out clutter from blender
            if (line.StartsWith("Fra:1") ||
                line.StartsWith("Progress: "))
            {
                continue;
            }
            if (line.Contains("Importing OBJ"))
            {
                Console.WriteLine(line[line.IndexOf("Importing OBJ")..]);
            }
            else if (line.Contains("building geometries"))
            {
                Console.WriteLine("Building geometries" + line[line.IndexOf("(verts")..]);
            }
            else if (line.Contains("Finished importing"))
            {
                Console.WriteLine(line[line.IndexOf("Finished importing")..]);
            }
            else if (Regex.IsMatch(line, @"\d+\.\d{4} sec"))
            {
                continue;
            }
            else
            {
                Console.WriteLine(line);
            }
        }

        string error = process.StandardError.ReadToEnd();
        process.WaitForExit();
        _blenderProcess = null;

        if (process.ExitCode != 0)
        {
            throw new Exception($"Blender process failed with exit code {process.ExitCode}. Error: {error}");
        }

        Console.WriteLine("Blender process completed successfully.");
    }

    private static string GetBlenderPath()
    {
        // Check for bundled Blender next to the executable
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string bundledPath = OperatingSystem.IsWindows() ? Path.Combine(baseDir, "blender", "blender.exe") : Path.Combine(baseDir, "blender", "blender");

        if (File.Exists(bundledPath))
        {
            Console.WriteLine($"Using bundled Blender: {bundledPath}");
            return bundledPath;
        }

        // Fall back to PATH for development
        Console.WriteLine("Bundled Blender not found, falling back to PATH");
        return "blender";
    }

    private static void KillBlenderProcess(object? sender, EventArgs e)
    {
        try { _blenderProcess?.Kill(entireProcessTree: true); } catch { }
    }
}