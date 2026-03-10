using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public record PropertyDetails([property: JsonPropertyName("formatVersion")] int FormatVersion,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("tileXLength")] int TileXLength,
    [property: JsonPropertyName("tileZLength")] int TileZLength);
