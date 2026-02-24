using System.Text.Json.Serialization;

namespace Vox2Pictoria;

public class FrameInfo(int voxelFrameIndex)
{
    [JsonIgnore]
    public Vector3Int MagicaVoxelDimensions
    {
        get => _magicaVoxelDimensions;
        private set => _magicaVoxelDimensions = value;
    }

    [JsonPropertyName("dimensions")]
    public Vector3Int PictoriaDimensions
    {
        // Note that magicavoxel x-axis = pictoria z-axis, magicavoxel z-axis = pictoria y-axis, magicavoxel y-axis = pictoria x-axis
        get => new(_magicaVoxelDimensions.Y, _magicaVoxelDimensions.Z, _magicaVoxelDimensions.X);
    }

    [JsonIgnore]
    public int VoxelFrameIndex { get; } = voxelFrameIndex;

    private Vector3Int _magicaVoxelDimensions;

    public void SetMagicaVoxelDimensions(int x, int y, int z)
    {
        _magicaVoxelDimensions = new(x, y, z);
    }
}