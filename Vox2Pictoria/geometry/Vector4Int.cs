namespace Vox2Pictoria;

public struct Vector4Int(int x, int y, int z, int w) : IEquatable<Vector4Int>
{
    public int X = x;
    public int Y = y;
    public int Z = z;
    public int W = w;

    public override readonly bool Equals(object? obj) => obj is Vector4Int other && Equals(other);

    public readonly bool Equals(Vector4Int other) => X == other.X && Y == other.Y && Z == other.Z && W == other.W;

    public override readonly int GetHashCode() => HashCode.Combine(X, Y, Z, W);

    public static bool operator ==(Vector4Int left, Vector4Int right) => left.Equals(right);

    public static bool operator !=(Vector4Int left, Vector4Int right) => !(left == right);
}