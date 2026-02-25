using System.Text;

namespace Vox2Pictoria;

/// <summary>
/// Helpers for reading .vox binary data from a <see cref="ReadOnlySpan{T}"/> with a moving byte position cursor.
/// </summary>
public static class VoxBytesReader
{
    public static int ReadInt32(ReadOnlySpan<byte> bytes, ref int bytePosition)
    {
        int value = BitConverter.ToInt32(bytes[bytePosition..]);
        bytePosition += 4;
        return value;
    }

    public static string ReadString(ReadOnlySpan<byte> bytes, ref int bytePosition)
    {
        int length = BitConverter.ToInt32(bytes[bytePosition..]);
        bytePosition += 4;
        string value = Encoding.UTF8.GetString(bytes.Slice(bytePosition, length));
        bytePosition += length;
        return value;
    }

    public static void SkipString(ReadOnlySpan<byte> bytes, ref int bytePosition)
    {
        int length = BitConverter.ToInt32(bytes[bytePosition..]);
        bytePosition += 4 + length;
    }

    public static void SkipDictionary(ReadOnlySpan<byte> bytes, ref int bytePosition)
    {
        int numPairs = BitConverter.ToInt32(bytes[bytePosition..]);
        bytePosition += 4;
        for (int i = 0; i < numPairs; i++)
        {
            SkipString(bytes, ref bytePosition);
            SkipString(bytes, ref bytePosition);
        }
    }

    public static Dictionary<string, string> ReadDictionary(ReadOnlySpan<byte> bytes, ref int bytePosition)
    {
        var dictionary = new Dictionary<string, string>();
        int numPairs = BitConverter.ToInt32(bytes[bytePosition..]);
        bytePosition += 4;
        for (int i = 0; i < numPairs; i++)
        {
            string key = ReadString(bytes, ref bytePosition);
            string value = ReadString(bytes, ref bytePosition);
            dictionary[key] = value;
        }
        return dictionary;
    }
}
