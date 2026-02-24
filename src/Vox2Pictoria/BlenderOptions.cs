using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public class BlenderOptions
{
    [JsonPropertyName("objDirectory")]
    public required string ObjDirectory { get; init; }

    [JsonPropertyName("rendersDirectory")]
    public required string RendersDirectory { get; init; }

    [JsonPropertyName("binDirectory")]
    public required string BinDirectory { get; init; }

    [JsonPropertyName("skipIndividualRenders")]
    public required bool SkipIndividualRenders { get; init; }

    [JsonPropertyName("fullSamples")]
    public required bool FullSamples { get; init; }

    [JsonPropertyName("orthoScale")]
    public required double OrthoScale { get; init; }

    [JsonPropertyName("resolutionWidth")]
    public required int ResolutionWidth { get; init; }

    [JsonPropertyName("resolutionHeight")]
    public required int ResolutionHeight { get; init; }

    [JsonPropertyName("cameraX")]
    public required double CameraX { get; init; }

    [JsonPropertyName("cameraY")]
    public required double CameraY { get; init; }

    [JsonPropertyName("cameraZ")]
    public required double CameraZ { get; init; }

    [JsonPropertyName("sunEnergy")]
    public required float SunEnergy { get; init; }

    [JsonPropertyName("sunColor")]
    public required float[] SunColor { get; init; }

    [JsonPropertyName("ambientStrength")]
    public required float AmbientStrength { get; init; }

    [JsonPropertyName("ambientLightColor")]
    public required float[] AmbientLightColor { get; init; }

    [JsonPropertyName("emissionCameraCap")]
    public required float EmissionCameraCap { get; init; }

    [JsonPropertyName("emissionBounceMultiplier")]
    public required float EmissionBounceMultiplier { get; init; }

    [JsonPropertyName("viewTransform")]
    public required string ViewTransform { get; init; }

    [JsonPropertyName("structureRenderParameters")]
    public required Dictionary<string, BlenderRenderParameters> StructureRenderParameters { get; init; }
}
