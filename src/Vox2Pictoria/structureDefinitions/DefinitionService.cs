using System.Formats.Tar;
using System.IO.Compression;
using System.Text.Json;

namespace Vox2Pictoria;

public class DefinitionService
{
    private static readonly JsonSerializerOptions _jsonOptions = new() { WriteIndented = true };

    public static async Task GeneratePstrFiles(Dictionary<string, StructureInfo> structureNameStructureInfoMap, Options options)
    {
        Console.WriteLine("Generating .pstr files...");
        if (!Directory.Exists(options.StructureDefinitionsDirectory)) Directory.CreateDirectory(options.StructureDefinitionsDirectory);

        DateTime currentTime = DateTime.Now;
        await Parallel.ForEachAsync(structureNameStructureInfoMap.Values, (structureInfo, cancellationToken) => GeneratePstrFile(structureInfo, options));
        Console.WriteLine($".pstr generation duration: {(DateTime.Now - currentTime).TotalSeconds} s");
    }

    private static async ValueTask GeneratePstrFile(StructureInfo structureInfo, Options options)
    {
        // Write gzip tar
        string pstrPath = Path.Combine(options.StructureDefinitionsDirectory, $"{structureInfo.Name}.pstr");
        await using FileStream fileStream = File.Create(pstrPath);
        await using GZipStream gzipStream = new(fileStream, CompressionLevel.Optimal);
        await using TarWriter tarWriter = new(gzipStream, TarEntryFormat.Ustar);

        await WriteStructureEntries(tarWriter, structureInfo, $"{structureInfo.Name}_structure", options);

        Console.WriteLine($"Generated {pstrPath}");
    }

    public static async Task GeneratePptyFile(Dictionary<string, StructureInfo> structureNameStructureInfoMap, Options options)
    {
        Console.WriteLine("Generating .ppty file...");
        DateTime currentTime = DateTime.Now;

        string propertyName = Path.GetFileNameWithoutExtension(options.VoxAbsolutePath);

        // Compute scene bounds from structure Pictoria locations
        int maxPictoriaX = int.MinValue;
        int maxPictoriaZ = int.MinValue;
        foreach (StructureInfo structureInfo in structureNameStructureInfoMap.Values)
        {
            Cuboid location = structureInfo.ShapeInfo.PictoriaLocation;
            maxPictoriaX = Math.Max(maxPictoriaX, location.MaxX);
            maxPictoriaZ = Math.Max(maxPictoriaZ, location.MaxZ);
        }

        // Compute tile lengths (a tile = 32 cartesian units, scene centered at origin)
        int tileXLength = (int)Math.Ceiling(2 * maxPictoriaX / 32.0);
        int tileZLength = (int)Math.Ceiling(2 * maxPictoriaZ / 32.0);

        // Create PropertyDetails
        var propertyDetails = new PropertyDetails(1, propertyName, tileXLength, tileZLength);

        // Write gzip tar
        if (!Directory.Exists(options.PropertyDefinitionDirectory)) Directory.CreateDirectory(options.PropertyDefinitionDirectory);
        string pptyPath = Path.Combine(options.PropertyDefinitionDirectory, $"{propertyName}.ppty");
        await using FileStream fileStream = File.Create(pptyPath);
        await using GZipStream gzipStream = new(fileStream, CompressionLevel.Optimal);
        await using TarWriter tarWriter = new(gzipStream, TarEntryFormat.Ustar);

        // Tar root directory entry
        string rootDirectoryName = $"{propertyName}_property";
        var rootDirectoryEntry = new UstarTarEntry(TarEntryType.Directory, $"{rootDirectoryName}/");
        await tarWriter.WriteEntryAsync(rootDirectoryEntry);

        // Serialize PropertyDetails to JSON
        var propertyDetailsJsonStream = new MemoryStream();
        JsonSerializer.Serialize(propertyDetailsJsonStream, propertyDetails, _jsonOptions);
        propertyDetailsJsonStream.Position = 0;

        // Property details JSON entry
        var propertyDetailsJsonEntry = new UstarTarEntry(TarEntryType.RegularFile, $"{rootDirectoryName}/{propertyName}.json") { DataStream = propertyDetailsJsonStream };
        await tarWriter.WriteEntryAsync(propertyDetailsJsonEntry);

        // Structures directory entry
        var structuresDirectoryEntry = new UstarTarEntry(TarEntryType.Directory, $"{rootDirectoryName}/structures/");
        await tarWriter.WriteEntryAsync(structuresDirectoryEntry);

        // Write each structure
        foreach (StructureInfo structureInfo in structureNameStructureInfoMap.Values)
        {
            await WriteStructureEntries(tarWriter, structureInfo, $"{rootDirectoryName}/structures/{structureInfo.Name}_structure", options);
        }

        Console.WriteLine($"Generated {pptyPath}");
        Console.WriteLine($".ppty generation duration: {(DateTime.Now - currentTime).TotalSeconds} s");
    }

    private static async Task WriteStructureEntries(TarWriter tarWriter, StructureInfo structureInfo, string directoryPath, Options options)
    {
        // Directory entry
        var directoryEntry = new UstarTarEntry(TarEntryType.Directory, $"{directoryPath}/");
        await tarWriter.WriteEntryAsync(directoryEntry);

        // Create StructureDetails
        string name = structureInfo.Name;
        Cuboid structurePictoriaLocation = structureInfo.ShapeInfo.PictoriaLocation;
        var structureDetails = new StructureDetails(1, name,
            (int)structureInfo.VolumeType,
            [structurePictoriaLocation.MinX, structurePictoriaLocation.MinY, structurePictoriaLocation.MinZ, structurePictoriaLocation.XLength, structurePictoriaLocation.YLength, structurePictoriaLocation.ZLength],
            "", []);

        // Serialize StructureDetails to JSON
        var structureDetailsJsonStream = new MemoryStream();
        JsonSerializer.Serialize(structureDetailsJsonStream, structureDetails, _jsonOptions);
        structureDetailsJsonStream.Position = 0;

        // Structure details JSON entry
        var structureDetailsJsonEntry = new UstarTarEntry(TarEntryType.RegularFile, $"{directoryPath}/{name}.json") { DataStream = structureDetailsJsonStream };
        await tarWriter.WriteEntryAsync(structureDetailsJsonEntry);

        // Image entry (Vox2Pictoria does not support multiple frames, so there is only one image per structure)
        string imagePath = Path.Combine(options.ImagesDirectory, $"{name}.png");
        if (!File.Exists(imagePath)) throw new FileNotFoundException($"Image not found: '{imagePath}'. Ensure that structure images have been rendered.");
        await using var imageStream = File.OpenRead(imagePath);
        var imageEntry = new UstarTarEntry(TarEntryType.RegularFile, $"{directoryPath}/{name}_1.png") { DataStream = imageStream };
        await tarWriter.WriteEntryAsync(imageEntry);
    }
}
