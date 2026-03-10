using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public record StructureDetails([property: JsonPropertyName("formatVersion")] int FormatVersion,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("volumeType")] int VolumeType,
    [property: JsonPropertyName("cartesianCuboid")] int[] CartesianCuboid,
    [property: JsonPropertyName("imageNormalizedMd5Base64")] string ImageNormalizedMd5Base64,
    [property: JsonPropertyName("frameDurations")] int[] FrameDurations);
