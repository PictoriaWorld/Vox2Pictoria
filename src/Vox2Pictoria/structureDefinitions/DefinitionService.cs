using System.Formats.Tar;
using System.IO.Compression;
using System.Security.Cryptography;
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
        (int tileXLength, int tileZLength) = VoxDataService.ComputeTileLengths(maxPictoriaX, maxPictoriaZ);

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

        // Read image and compute normalized MD5 hash
        string name = structureInfo.Name;
        string imagePath = Path.Combine(options.ImagesDirectory, $"{name}.png");
        if (!File.Exists(imagePath)) throw new FileNotFoundException($"Image not found: '{imagePath}'. Ensure that structure images have been rendered.");
        byte[] imageBytes = await File.ReadAllBytesAsync(imagePath);
        string imageNormalizedMd5Base64 = GetImageNormalizedMd5Base64(imageBytes);

        // Create StructureDetails
        Cuboid structurePictoriaLocation = structureInfo.ShapeInfo.PictoriaLocation;
        var structureDetails = new StructureDetails(1, name,
            (int)structureInfo.VolumeType,
            [structurePictoriaLocation.MinX, structurePictoriaLocation.MinY, structurePictoriaLocation.MinZ, structurePictoriaLocation.XLength, structurePictoriaLocation.YLength, structurePictoriaLocation.ZLength],
            imageNormalizedMd5Base64, []);

        // Serialize StructureDetails to JSON
        var structureDetailsJsonStream = new MemoryStream();
        JsonSerializer.Serialize(structureDetailsJsonStream, structureDetails, _jsonOptions);
        structureDetailsJsonStream.Position = 0;

        // Structure details JSON entry
        var structureDetailsJsonEntry = new UstarTarEntry(TarEntryType.RegularFile, $"{directoryPath}/{name}.json") { DataStream = structureDetailsJsonStream };
        await tarWriter.WriteEntryAsync(structureDetailsJsonEntry);

        // Image entry (Vox2Pictoria does not support multiple frames, so there is only one image per structure)
        var imageStream = new MemoryStream(imageBytes);
        var imageEntry = new UstarTarEntry(TarEntryType.RegularFile, $"{directoryPath}/{name}_1.png") { DataStream = imageStream };
        await tarWriter.WriteEntryAsync(imageEntry);
    }

    /// <summary>
    /// Computes the normalized MD5 base64 hash for an image. Mirrors Pictoria.Server's ImageDataService.GetImageNormalizedMd5Base64.
    /// </summary>
    private static string GetImageNormalizedMd5Base64(byte[] imageBytes)
    {
        byte[] hash = MD5.HashData(imageBytes);
        string base64 = Convert.ToBase64String(hash);

        // Take first 22 chars, replace '+' with '_' and '/' with '-'
        Span<char> result = stackalloc char[22];
        for (int i = 0; i < 22; i++)
        {
            char c = base64[i];
            if (c == '+') result[i] = '_';
            else if (c == '/') result[i] = '-';
            else result[i] = c;
        }

        return new string(result);
    }
}
