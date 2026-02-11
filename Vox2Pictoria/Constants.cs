namespace Vox2Pictoria;

public static class Constants
{
    /// <summary>
    /// Pictoria cartesian coordinates (= MagicaVoxel voxel coordinates) are divided by this value
    /// when writing OBJ vertices to keep Blender geometry at a manageable scale.
    /// blenderWorldUnit = pictoriaCartesianUnit / PictoriaCartesianToBlenderWorldDivisor
    /// </summary>
    public const float PictoriaCartesianToBlenderWorldDivisor = 10f;
}
