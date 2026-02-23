using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public class MetalMaterialProperties(double metallic, double rough, double spec, double ior, double[] rgb)
{
    [JsonPropertyName("metallic")]
    public double Metallic { get; } = metallic;

    [JsonPropertyName("rough")]
    public double Rough { get; } = rough;

    [JsonPropertyName("spec")]
    public double Spec { get; } = spec;

    [JsonPropertyName("ior")]
    public double Ior { get; } = ior;

    [JsonPropertyName("rgb")]
    public double[] Rgb { get; } = rgb;
}
