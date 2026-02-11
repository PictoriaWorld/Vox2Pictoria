namespace Vox2Pictoria;

public struct VisibleVoxelInfo(ref CuboidFaceVisibilities cuboidFaceVisibilities, ref Cuboid untransformedVoxelBoundingBox, int paletteNumber)
{
    public CuboidFaceVisibilities CuboidFaceVisibilities = cuboidFaceVisibilities;
    public Cuboid UntransformedVoxelBoundingBox = untransformedVoxelBoundingBox;
    public readonly int PaletteNumber = paletteNumber;
}