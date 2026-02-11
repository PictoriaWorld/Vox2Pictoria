using System.Runtime.CompilerServices;
using FileToVoxCore.Vox;

namespace Vox2Pictoria;

public class VoxelCoordinatesService
{
    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static bool CheckIfUntransformedNeighbourOccupied(float neighbourUntransformedMinX, float neighbourUntransformedMinY, float neighbourUntransformedMinZ, int untransformedXLength, int untransformedXAndYLengthsProduct,
        VoxelData voxelFrame)
    {
        int adjacentVoxelIndex = UntransformedVoxelMinCoordinatesToVoxelIndex(neighbourUntransformedMinX, neighbourUntransformedMinY, neighbourUntransformedMinZ, untransformedXLength, untransformedXAndYLengthsProduct);
        return voxelFrame.Colors.ContainsKey(adjacentVoxelIndex);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static int UntransformedVoxelMinCoordinatesToVoxelIndex(float untransformedMinX, float untransformedMinY, float untransformedMinZ, int untransformedXLength, int untransformedXAndYLengthsProduct)
    {
        return (int)(untransformedMinZ * untransformedXAndYLengthsProduct + untransformedMinY * untransformedXLength + untransformedMinX);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static Cuboid VoxelIndexToUntransformedVoxelBoundingBox(int index, int untransformedXLength, int untransformedXAndYLengthsProduct)
    {
        int untransformedMinZ = index / untransformedXAndYLengthsProduct;
        index -= untransformedMinZ * untransformedXAndYLengthsProduct;
        int untransformedMinY = index / untransformedXLength;
        int untransformedMinX = index % untransformedXLength;
        return new(untransformedMinX, untransformedMinX + 1, untransformedMinY, untransformedMinY + 1, untransformedMinZ, untransformedMinZ + 1);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static Vector3Int UntransformedToTransformedVoxelMinCoordinates(ref Cuboid untransformedCoordinates, ref Matrix4x4Int transformMatrix)
    {
        Vector3Int transformedMins = transformMatrix.MultiplyPoint(untransformedCoordinates.GetMins());
        Vector3Int transformedMaxs = transformMatrix.MultiplyPoint(untransformedCoordinates.GetMaxs());

        return new(transformedMins.X < transformedMaxs.X ? transformedMins.X : transformedMaxs.X,
            transformedMins.Y < transformedMaxs.Y ? transformedMins.Y : transformedMaxs.Y,
            transformedMins.Z < transformedMaxs.Z ? transformedMins.Z : transformedMaxs.Z);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static Cuboid UntransformedToTransformedBoundingBox(ref Cuboid untransformedCoordinates, ref Matrix4x4Int transformMatrix)
    {
        Vector3Int transformedMins = transformMatrix.MultiplyPoint(untransformedCoordinates.GetMins());
        Vector3Int transformedMaxs = transformMatrix.MultiplyPoint(untransformedCoordinates.GetMaxs());

        int minX, maxX, minY, maxY, minZ, maxZ;
        if (transformedMins.X < transformedMaxs.X)
        {
            minX = transformedMins.X;
            maxX = transformedMaxs.X;
        }
        else
        {
            minX = transformedMaxs.X;
            maxX = transformedMins.X;
        }
        if (transformedMins.Y < transformedMaxs.Y)
        {
            minY = transformedMins.Y;
            maxY = transformedMaxs.Y;
        }
        else
        {
            minY = transformedMaxs.Y;
            maxY = transformedMins.Y;
        }

        if (transformedMins.Z < transformedMaxs.Z)
        {
            minZ = transformedMins.Z;
            maxZ = transformedMaxs.Z;
        }
        else
        {
            minZ = transformedMaxs.Z;
            maxZ = transformedMins.Z;
        }

        return new(minX, maxX, minY, maxY, minZ, maxZ);
    }
}