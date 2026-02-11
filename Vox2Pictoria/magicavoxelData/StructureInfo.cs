using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public class StructureInfo(ShapeInfo shapeInfo, string name, VolumeType volumeType)
{
    private ImageDimensions _imageDimensions;
    private ShapeInfo _shapeInfo = shapeInfo;
    private VolumeType _volumeType = volumeType;

    [JsonPropertyName("name")]
    public string Name { get; set; } = name;

    [JsonPropertyName("imageDimensions")]
    public ImageDimensions ImageDimensions
    {
        get => _imageDimensions;
        private set => _imageDimensions = value;
    }

    [JsonPropertyName("volumeType")]
    [JsonConverter(typeof(JsonStringEnumConverter))]
    public VolumeType VolumeType
    {
        get => _volumeType;
        private set => _volumeType = value;
    }

    [JsonPropertyName("shapeInfo")]
    public ShapeInfo ShapeInfo
    {
        get => _shapeInfo;
        private set => _shapeInfo = value;
    }

    [JsonIgnore]
    public BlenderRenderParameters? BlenderRenderParameters { get; private set; }

    [JsonIgnore()]
    public IsometricPolygon? IsometricPolygon
    {
        get;
        private set;
    }

    public void SetIsometricPolygon(IsometricPolygon isometricPolygon)
    {
        IsometricPolygon = isometricPolygon;
        _imageDimensions = new(isometricPolygon.GetRoundedIsometricBoundingRectangleWidth(), isometricPolygon.GetRoundedIsometricBoundingRectangleHeight());
    }

    public void SetBlenderRenderParameters(BlenderRenderParameters blenderRenderParameters)
    {
        BlenderRenderParameters = blenderRenderParameters;
    }
}