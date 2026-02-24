namespace Vox2Pictoria;

public struct Cuboid(int minX, int maxX, int minY, int maxY, int minZ, int maxZ) : IEquatable<Cuboid>
{
    public int MinX { get; private set; } = minX;
    public int MaxX { get; private set; } = maxX;
    public int MinY { get; private set; } = minY;
    public int MaxY { get; private set; } = maxY;
    public int MinZ { get; private set; } = minZ;
    public int MaxZ { get; private set; } = maxZ;

    public readonly int XLength => MaxX - MinX;
    public readonly int YLength => MaxY - MinY;
    public readonly int ZLength => MaxZ - MinZ;

    public void Update(int newMinX, int newMaxX, int newMinY, int newMaxY, int newMinZ, int newMaxZ)
    {
        MinX = newMinX;
        MaxX = newMaxX;
        MinY = newMinY;
        MaxY = newMaxY;
        MinZ = newMinZ;
        MaxZ = newMaxZ;
    }

    public readonly Vector3Int GetMins()
    {
        return new Vector3Int(MinX, MinY, MinZ);
    }

    public readonly Vector3Int GetMaxs()
    {
        return new Vector3Int(MaxX, MaxY, MaxZ);
    }

    public void Offset(int deltaX, int deltaZ)
    {
        MinX += deltaX;
        MaxX += deltaX;
        MinZ += deltaZ;
        MaxZ += deltaZ;
    }

    public readonly bool Equals(Cuboid other)
    {
        return MinX == other.MinX &&
               MaxX == other.MaxX &&
               MinY == other.MinY &&
               MaxY == other.MaxY &&
               MinZ == other.MinZ &&
               MaxZ == other.MaxZ;
    }

    public override readonly int GetHashCode()
    {
        return HashCode.Combine(MinX, MaxX, MinY, MaxY, MinZ, MaxZ);
    }

    public override readonly bool Equals(object? obj)
    {
        return obj is Cuboid cuboid && Equals(cuboid);
    }

    public override readonly string ToString()
    {
        return $"({MinX}, {MaxX}, {MinY}, {MaxY}, {MinZ}, {MaxZ})";
    }

    public static bool operator ==(Cuboid left, Cuboid right)
    {
        return left.Equals(right);
    }

    public static bool operator !=(Cuboid left, Cuboid right)
    {
        return !(left == right);
    }
}