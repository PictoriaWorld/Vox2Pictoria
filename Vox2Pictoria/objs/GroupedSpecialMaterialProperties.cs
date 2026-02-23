using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public class GroupedSpecialMaterialProperties
{
    [JsonPropertyName("emissive")]
    public Dictionary<string, EmissiveMaterialProperties> Emissive { get; init; } = [];

    [JsonPropertyName("glass")]
    public Dictionary<string, GlassMaterialProperties> Glass { get; init; } = [];

    [JsonPropertyName("metal")]
    public Dictionary<string, MetalMaterialProperties> Metal { get; init; } = [];
}
