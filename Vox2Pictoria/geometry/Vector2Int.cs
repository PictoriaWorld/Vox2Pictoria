namespace Vox2Pictoria;

public readonly struct Vector2Int(int x, int y) : IEquatable<Vector2Int>
{
    public int X { get; } = x;
    public int Y { get; } = y;

    public override bool Equals(object? obj) => obj is Vector2Int other && Equals(other);

    public bool Equals(Vector2Int other) => X == other.X && Y == other.Y;

    public override int GetHashCode() => HashCode.Combine(X, Y);

    public static bool operator ==(Vector2Int left, Vector2Int right) => left.Equals(right);

    public static bool operator !=(Vector2Int left, Vector2Int right) => !(left == right);

    public static Vector2Int operator +(Vector2Int a, Vector2Int b) => new Vector2Int(a.X + b.X, a.Y + b.Y);
}