using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public readonly struct ImageDimensions(int width, int height)
{
    [JsonPropertyName("Width")]
    public int Width { get; } = width;
    [JsonPropertyName("Height")]
    public int Height { get; } = height;
}