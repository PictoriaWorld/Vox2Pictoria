using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public class EmissiveMaterialProperties(double[] ke)
{
    [JsonPropertyName("ke")]
    public double[] Ke { get; } = ke;
}
