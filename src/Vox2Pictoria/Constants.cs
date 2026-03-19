namespace Vox2Pictoria;

public static class Constants
{
    /// <summary>
    /// Pictoria cartesian coordinates (= MagicaVoxel voxel coordinates) are divided by this value
    /// when writing OBJ vertices to keep Blender geometry at a manageable scale.
    /// blenderWorldUnit = pictoriaCartesianUnit / PictoriaCartesianToBlenderWorldDivisor
    /// </summary>
    public const float PictoriaCartesianToBlenderWorldDivisor = 10f;

    /// <summary>
    /// Width of a single tile in Pictoria cartesian units.
    /// </summary>
    public const int TileCartesianWidth = 32;

    /// <summary>
    /// Maximum allowed height for a chunk/property in Pictoria cartesian units.
    /// </summary>
    public const int ChunkCartesianHeight = 384;
}
