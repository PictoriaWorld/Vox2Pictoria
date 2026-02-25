namespace Vox2Pictoria;

public class ParsedVox(byte[] fullFileBytes, int version)
{
    // The raw bytes of each chunk for the full file
    public byte[] FullFileBytes { get; } = fullFileBytes;

    // .vox format version (e.g. 200 = MagicaVoxel 0.99.7.2+)
    public int Version { get; } = version;

    // SIZE+XYZI pairs in order (model index = list index)
    public List<(RawVoxChunk SizeChunk, RawVoxChunk XyziChunk)> ModelChunks { get; } = [];

    // Scene graph: all nTRN, nGRP, nSHP chunks (raw content bytes)
    public List<RawVoxChunk> SceneGraphChunks { get; } = [];

    // RGBA chunk (full chunk including header) — slice of FullFileBytes
    public Memory<byte>? RgbaChunk { get; set; }

    // MATL chunks (full chunks including headers) — slices of FullFileBytes
    public List<Memory<byte>> MatlChunks { get; } = [];
}