namespace Vox2Pictoria;

public static class Matrix4x4IntExtension
{
    public static void Print(this Matrix4x4Int matrix)
    {
        Console.WriteLine($"[{matrix.m00}, {matrix.m01}, {matrix.m02}, {matrix.m03}]\n" +
$"[{matrix.m10}, {matrix.m11}, {matrix.m12}, {matrix.m13}]\n" +
$"[{matrix.m20}, {matrix.m21}, {matrix.m22}, {matrix.m23}]\n" +
$"[{matrix.m30}, {matrix.m31}, {matrix.m32}, {matrix.m33}]");
    }
}