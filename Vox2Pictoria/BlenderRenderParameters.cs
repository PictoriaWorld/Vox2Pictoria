using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public record BlenderRenderParameters([property: JsonPropertyName("orthoScale")] double OrthoScale,
    [property: JsonPropertyName("resolutionWidth")] int ResolutionWidth,
    [property: JsonPropertyName("resolutionHeight")] int ResolutionHeight,
    [property: JsonPropertyName("cameraX")] double CameraX,
    [property: JsonPropertyName("cameraY")] double CameraY,
    [property: JsonPropertyName("cameraZ")] double CameraZ);
