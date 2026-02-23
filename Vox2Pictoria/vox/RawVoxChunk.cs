namespace Vox2Pictoria;

public record RawVoxChunk(string Id, Memory<byte> FullChunkBytes)
{
    public Memory<byte> ChunkContentBytes => FullChunkBytes[12..];
}