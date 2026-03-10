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

        // Tar directory entry
        string innerDirectoryName = $"{structureInfo.Name}_structure";
        var innerDirectoryEntry = new UstarTarEntry(TarEntryType.Directory, $"{innerDirectoryName}/");
        await tarWriter.WriteEntryAsync(innerDirectoryEntry);

        // Create StructureDetails
        string name = structureInfo.Name;
        Cuboid structurePictoriaLocation = structureInfo.ShapeInfo.PictoriaLocation;
        var structureDetails = new StructureDetails(name,
            (int)structureInfo.VolumeType,
            [structurePictoriaLocation.MinX, structurePictoriaLocation.MinY, structurePictoriaLocation.MinZ, structurePictoriaLocation.XLength, structurePictoriaLocation.YLength, structurePictoriaLocation.ZLength],
            "", []);

        // Serialize StructureDetails to JSON
        var structureDetailsJsonStream = new MemoryStream();
        JsonSerializer.Serialize(structureDetailsJsonStream, structureDetails, _jsonOptions);
        structureDetailsJsonStream.Position = 0;

        // Structure details JSON entry
        var structureDetailsJsonEntry = new UstarTarEntry(TarEntryType.RegularFile, $"{innerDirectoryName}/{structureInfo.Name}.json") { DataStream = structureDetailsJsonStream };
        await tarWriter.WriteEntryAsync(structureDetailsJsonEntry);

        // Image entry
        //
        // Note that Vox2Pictoria does not support multiple frames, so there is only one image per structure
        string imagePath = Path.Combine(options.ImagesDirectory, $"{structureInfo.Name}.png");
        if (!File.Exists(imagePath)) throw new FileNotFoundException($"Image not found: '{imagePath}'. Ensure that structure images have been rendered.");
        await using var imageStream = File.OpenRead(imagePath);
        var imageEntry = new UstarTarEntry(TarEntryType.RegularFile, $"{innerDirectoryName}/{structureInfo.Name}_1.png") { DataStream = imageStream };
        await tarWriter.WriteEntryAsync(imageEntry);

        Console.WriteLine($"Generated {pstrPath}");
    }
}
