using FileToVoxCore.Schematics.Tools;

namespace Vox2Pictoria;

public struct Vector3Int(int x, int y, int z) : IEquatable<Vector3Int>
{
    public int X = x;
    public int Y = y;
    public int Z = z;

    public Vector3Int(Vector3 vector) : this((int)Math.Round(vector.X), (int)Math.Round(vector.Y), (int)Math.Round(vector.Z)) { }

    public override readonly bool Equals(object? obj) => obj is Vector3Int other && Equals(other);

    public readonly bool Equals(Vector3Int other) => X == other.X && Y == other.Y && Z == other.Z;

    public override readonly int GetHashCode() => HashCode.Combine(X, Y, Z);

    public static bool operator ==(Vector3Int left, Vector3Int right) => left.Equals(right);

    public static bool operator !=(Vector3Int left, Vector3Int right) => !(left == right);

    public static Vector3Int operator +(Vector3Int a, Vector3Int b) => new Vector3Int(a.X + b.X, a.Y + b.Y, a.Z + b.Z);
}