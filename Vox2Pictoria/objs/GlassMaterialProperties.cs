using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public class GlassMaterialProperties(double d, double ior, double rough, double[] rgb)
{
    [JsonPropertyName("d")]
    public double D { get; } = d;

    [JsonPropertyName("ior")]
    public double Ior { get; } = ior;

    [JsonPropertyName("rough")]
    public double Rough { get; } = rough;

    [JsonPropertyName("rgb")]
    public double[] Rgb { get; } = rgb;
}
