using FileToVoxCore.Schematics.Tools;
using System.Runtime.CompilerServices;

namespace Vox2Pictoria;

public struct Matrix4x4Int : IEquatable<Matrix4x4Int>
{
    public int m00;

    public int m10;

    public int m20;

    public int m30;

    public int m01;

    public int m11;

    public int m21;

    public int m31;

    public int m02;

    public int m12;

    public int m22;

    public int m32;

    public int m03;

    public int m13;

    public int m23;

    public int m33;

    private static readonly Matrix4x4Int zeroMatrix = new(new Vector4Int(0, 0, 0, 0), new Vector4Int(0, 0, 0, 0), new Vector4Int(0, 0, 0, 0), new Vector4Int(0, 0, 0, 0));

    private static readonly Matrix4x4Int identityMatrix = new(new Vector4Int(1, 0, 0, 0), new Vector4Int(0, 1, 0, 0), new Vector4Int(0, 0, 1, 0), new Vector4Int(0, 0, 0, 1));

    public int this[int row, int column]
    {
        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        get
        {
            return this[row + column * 4];
        }
        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        set
        {
            this[row + column * 4] = value;
        }
    }

    public int this[int index]
    {
        get
        {
            return index switch
            {
                0 => m00,
                1 => m10,
                2 => m20,
                3 => m30,
                4 => m01,
                5 => m11,
                6 => m21,
                7 => m31,
                8 => m02,
                9 => m12,
                10 => m22,
                11 => m32,
                12 => m03,
                13 => m13,
                14 => m23,
                15 => m33,
                _ => throw new IndexOutOfRangeException("Invalid matrix index!"),
            };
        }
        set
        {
            switch (index)
            {
                case 0:
                    m00 = value;
                    break;
                case 1:
                    m10 = value;
                    break;
                case 2:
                    m20 = value;
                    break;
                case 3:
                    m30 = value;
                    break;
                case 4:
                    m01 = value;
                    break;
                case 5:
                    m11 = value;
                    break;
                case 6:
                    m21 = value;
                    break;
                case 7:
                    m31 = value;
                    break;
                case 8:
                    m02 = value;
                    break;
                case 9:
                    m12 = value;
                    break;
                case 10:
                    m22 = value;
                    break;
                case 11:
                    m32 = value;
                    break;
                case 12:
                    m03 = value;
                    break;
                case 13:
                    m13 = value;
                    break;
                case 14:
                    m23 = value;
                    break;
                case 15:
                    m33 = value;
                    break;
                default:
                    throw new IndexOutOfRangeException("Invalid matrix index!");
            }
        }
    }

    public static Matrix4x4Int Zero => zeroMatrix;

    public static Matrix4x4Int Identity
    {
        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        get
        {
            return identityMatrix;
        }
    }

    public Matrix4x4Int(Vector4Int column0, Vector4Int column1, Vector4Int column2, Vector4Int column3)
    {
        m00 = column0.X;
        m01 = column1.X;
        m02 = column2.X;
        m03 = column3.X;
        m10 = column0.Y;
        m11 = column1.Y;
        m12 = column2.Y;
        m13 = column3.Y;
        m20 = column0.Z;
        m21 = column1.Z;
        m22 = column2.Z;
        m23 = column3.Z;
        m30 = column0.W;
        m31 = column1.W;
        m32 = column2.W;
        m33 = column3.W;
    }

    public Matrix4x4Int(Matrix4x4 matrix)
    {
        m00 = (int)Math.Round(matrix.m00);
        m01 = (int)Math.Round(matrix.m01);
        m02 = (int)Math.Round(matrix.m02);
        m03 = (int)Math.Round(matrix.m03);
        m10 = (int)Math.Round(matrix.m10);
        m11 = (int)Math.Round(matrix.m11);
        m12 = (int)Math.Round(matrix.m12);
        m13 = (int)Math.Round(matrix.m13);
        m20 = (int)Math.Round(matrix.m20);
        m21 = (int)Math.Round(matrix.m21);
        m22 = (int)Math.Round(matrix.m22);
        m23 = (int)Math.Round(matrix.m23);
        m30 = (int)Math.Round(matrix.m30);
        m31 = (int)Math.Round(matrix.m31);
        m32 = (int)Math.Round(matrix.m32);
        m33 = (int)Math.Round(matrix.m33);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public override readonly int GetHashCode()
    {
        int hashCode = GetColumn(0).GetHashCode();
        int num = GetColumn(1).GetHashCode() << 2;
        int num2 = hashCode ^ num;
        int num3 = GetColumn(2).GetHashCode() >> 2;
        int num4 = num2 ^ num3;
        int num5 = GetColumn(3).GetHashCode() >> 1;
        return num4 ^ num5;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public override readonly bool Equals(object? other)
    {
        if (other is Matrix4x4Int other2) return Equals(other2);

        return false;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public readonly bool Equals(Matrix4x4Int other)
    {
        int num = ((GetColumn(0).Equals(other.GetColumn(0)) && GetColumn(1).Equals(other.GetColumn(1)) && GetColumn(2).Equals(other.GetColumn(2))) ? (GetColumn(3).Equals(other.GetColumn(3)) ? 1 : 0) : 0);
        return num != 0;
    }

    public static Matrix4x4Int operator *(Matrix4x4Int lhs, Matrix4x4Int rhs)
    {
        var result = default(Matrix4x4Int);
        result.m00 = (int)(lhs.m00 * (double)rhs.m00 + lhs.m01 * (double)rhs.m10 + lhs.m02 * (double)rhs.m20 + lhs.m03 * (double)rhs.m30);
        result.m01 = (int)(lhs.m00 * (double)rhs.m01 + lhs.m01 * (double)rhs.m11 + lhs.m02 * (double)rhs.m21 + lhs.m03 * (double)rhs.m31);
        result.m02 = (int)(lhs.m00 * (double)rhs.m02 + lhs.m01 * (double)rhs.m12 + lhs.m02 * (double)rhs.m22 + lhs.m03 * (double)rhs.m32);
        result.m03 = (int)(lhs.m00 * (double)rhs.m03 + lhs.m01 * (double)rhs.m13 + lhs.m02 * (double)rhs.m23 + lhs.m03 * (double)rhs.m33);
        result.m10 = (int)(lhs.m10 * (double)rhs.m00 + lhs.m11 * (double)rhs.m10 + lhs.m12 * (double)rhs.m20 + lhs.m13 * (double)rhs.m30);
        result.m11 = (int)(lhs.m10 * (double)rhs.m01 + lhs.m11 * (double)rhs.m11 + lhs.m12 * (double)rhs.m21 + lhs.m13 * (double)rhs.m31);
        result.m12 = (int)(lhs.m10 * (double)rhs.m02 + lhs.m11 * (double)rhs.m12 + lhs.m12 * (double)rhs.m22 + lhs.m13 * (double)rhs.m32);
        result.m13 = (int)(lhs.m10 * (double)rhs.m03 + lhs.m11 * (double)rhs.m13 + lhs.m12 * (double)rhs.m23 + lhs.m13 * (double)rhs.m33);
        result.m20 = (int)(lhs.m20 * (double)rhs.m00 + lhs.m21 * (double)rhs.m10 + lhs.m22 * (double)rhs.m20 + lhs.m23 * (double)rhs.m30);
        result.m21 = (int)(lhs.m20 * (double)rhs.m01 + lhs.m21 * (double)rhs.m11 + lhs.m22 * (double)rhs.m21 + lhs.m23 * (double)rhs.m31);
        result.m22 = (int)(lhs.m20 * (double)rhs.m02 + lhs.m21 * (double)rhs.m12 + lhs.m22 * (double)rhs.m22 + lhs.m23 * (double)rhs.m32);
        result.m23 = (int)(lhs.m20 * (double)rhs.m03 + lhs.m21 * (double)rhs.m13 + lhs.m22 * (double)rhs.m23 + lhs.m23 * (double)rhs.m33);
        result.m30 = (int)(lhs.m30 * (double)rhs.m00 + lhs.m31 * (double)rhs.m10 + lhs.m32 * (double)rhs.m20 + lhs.m33 * (double)rhs.m30);
        result.m31 = (int)(lhs.m30 * (double)rhs.m01 + lhs.m31 * (double)rhs.m11 + lhs.m32 * (double)rhs.m21 + lhs.m33 * (double)rhs.m31);
        result.m32 = (int)(lhs.m30 * (double)rhs.m02 + lhs.m31 * (double)rhs.m12 + lhs.m32 * (double)rhs.m22 + lhs.m33 * (double)rhs.m32);
        result.m33 = (int)(lhs.m30 * (double)rhs.m03 + lhs.m31 * (double)rhs.m13 + lhs.m32 * (double)rhs.m23 + lhs.m33 * (double)rhs.m33);
        return result;
    }

    public static Vector4Int operator *(Matrix4x4Int lhs, Vector4Int vector)
    {
        var result = default(Vector4Int);
        result.X = (int)(lhs.m00 * (double)vector.X + lhs.m01 * (double)vector.Y + lhs.m02 * (double)vector.Z + lhs.m03 * (double)vector.W);
        result.Y = (int)(lhs.m10 * (double)vector.X + lhs.m11 * (double)vector.Y + lhs.m12 * (double)vector.Z + lhs.m13 * (double)vector.W);
        result.Z = (int)(lhs.m20 * (double)vector.X + lhs.m21 * (double)vector.Y + lhs.m22 * (double)vector.Z + lhs.m23 * (double)vector.W);
        result.W = (int)(lhs.m30 * (double)vector.X + lhs.m31 * (double)vector.Y + lhs.m32 * (double)vector.Z + lhs.m33 * (double)vector.W);
        return result;
    }

    public static bool operator ==(Matrix4x4Int lhs, Matrix4x4Int rhs)
    {
        if (lhs.GetColumn(0) == rhs.GetColumn(0) && lhs.GetColumn(1) == rhs.GetColumn(1) && lhs.GetColumn(2) == rhs.GetColumn(2))
        {
            return lhs.GetColumn(3) == rhs.GetColumn(3);
        }

        return false;
    }

    public static bool operator !=(Matrix4x4Int lhs, Matrix4x4Int rhs)
    {
        return !(lhs == rhs);
    }

    public readonly Vector4Int GetColumn(int index)
    {
        return index switch
        {
            0 => new Vector4Int(m00, m10, m20, m30),
            1 => new Vector4Int(m01, m11, m21, m31),
            2 => new Vector4Int(m02, m12, m22, m32),
            3 => new Vector4Int(m03, m13, m23, m33),
            _ => throw new IndexOutOfRangeException("Invalid column index!"),
        };
    }

    public readonly Vector4Int GetRow(int index)
    {
        return index switch
        {
            0 => new Vector4Int(m00, m01, m02, m03),
            1 => new Vector4Int(m10, m11, m12, m13),
            2 => new Vector4Int(m20, m21, m22, m23),
            3 => new Vector4Int(m30, m31, m32, m33),
            _ => throw new IndexOutOfRangeException("Invalid row index!"),
        };
    }

    public readonly Vector3Int GetPosition()
    {
        return new Vector3Int(m03, m13, m23);
    }

    public void SetColumn(int index, Vector4Int column)
    {
        this[0, index] = column.X;
        this[1, index] = column.Y;
        this[2, index] = column.Z;
        this[3, index] = column.W;
    }

    public void SetRow(int index, Vector4Int row)
    {
        this[index, 0] = row.X;
        this[index, 1] = row.Y;
        this[index, 2] = row.Z;
        this[index, 3] = row.W;
    }

    public readonly Vector3Int MultiplyPoint(Vector3Int point)
    {
        var result = default(Vector3Int);
        result.X = (int)(m00 * (double)point.X + m01 * (double)point.Y + m02 * (double)point.Z) + m03;
        result.Y = (int)(m10 * (double)point.X + m11 * (double)point.Y + m12 * (double)point.Z) + m13;
        result.Z = (int)(m20 * (double)point.X + m21 * (double)point.Y + m22 * (double)point.Z) + m23;
        int num = 1 / ((int)(m30 * (double)point.X + m31 * (double)point.Y + m32 * (double)point.Z) + m33);
        result.X *= num;
        result.Y *= num;
        result.Z *= num;
        return result;
    }

    public readonly Vector3Int MultiplyPoint3x4(Vector3Int point)
    {
        var result = default(Vector3Int);
        result.X = (int)(m00 * (double)point.X + m01 * (double)point.Y + m02 * (double)point.Z) + m03;
        result.Y = (int)(m10 * (double)point.X + m11 * (double)point.Y + m12 * (double)point.Z) + m13;
        result.Z = (int)(m20 * (double)point.X + m21 * (double)point.Y + m22 * (double)point.Z) + m23;
        return result;
    }

    public readonly Vector3Int MultiplyVector(Vector3Int vector)
    {
        var result = default(Vector3Int);
        result.X = (int)(m00 * (double)vector.X + m01 * (double)vector.Y + m02 * (double)vector.Z);
        result.Y = (int)(m10 * (double)vector.X + m11 * (double)vector.Y + m12 * (double)vector.Z);
        result.Z = (int)(m20 * (double)vector.X + m21 * (double)vector.Y + m22 * (double)vector.Z);
        return result;
    }

    public static Matrix4x4Int Scale(Vector3Int vector)
    {
        var result = default(Matrix4x4Int);
        result.m00 = vector.X;
        result.m01 = 0;
        result.m02 = 0;
        result.m03 = 0;
        result.m10 = 0;
        result.m11 = vector.Y;
        result.m12 = 0;
        result.m13 = 0;
        result.m20 = 0;
        result.m21 = 0;
        result.m22 = vector.Z;
        result.m23 = 0;
        result.m30 = 0;
        result.m31 = 0;
        result.m32 = 0;
        result.m33 = 1;
        return result;
    }

    public static Matrix4x4Int Translate(Vector3Int vector)
    {
        var result = default(Matrix4x4Int);
        result.m00 = 1;
        result.m01 = 0;
        result.m02 = 0;
        result.m03 = vector.X;
        result.m10 = 0;
        result.m11 = 1;
        result.m12 = 0;
        result.m13 = vector.Y;
        result.m20 = 0;
        result.m21 = 0;
        result.m22 = 1;
        result.m23 = vector.Z;
        result.m30 = 0;
        result.m31 = 0;
        result.m32 = 0;
        result.m33 = 1;
        return result;
    }
}