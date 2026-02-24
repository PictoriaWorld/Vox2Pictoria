using System.Text;

namespace Vox2Pictoria;

public static class VoxParser
{
    // MagicaVoxel .vox file format references:
    //   https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox.txt
    //   https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox-extension.txt
    //
    // .vox format summary:
    //
    //   File Header: 'VOX ' (4 bytes) + version int32 (150)
    //   Chunk []: 
    //     Chunk Header: Each chunk has a 4-char ID, int32 content byte size (N), int32 children byte size (M)
    //     Chunk Contents: N bytes content, M bytes children
    //
    //   MAIN chunk (root, no content, all other chunks are children in this order):
    //     Model chunks [] - a pair of SIZE+XYZI chunks:
    //       SIZE   - Model dimensions: int32 x, y, z. Model index = order of appearance.
    //       XYZI   - Model voxels: int32 count (N), then N × (x, y, z, colorIndex) as 4 bytes each.
    //     Scene graph (nTRN/nGRP/nSHP form a tree, nTRN has one child, nGRP has N children which are all nTRN).
    //       Layout: nTRN(0) → nGRP(1) → nTRN → nGRP/nSHP
    //                            nTRN → nGRP/nSHP
    //                            ...
    //       Chunks:
    //         nTRN - Transform node: int32 nodeId, DICT attrs, int32 childId, int32 reserved (-1),
    //                int32 layerId, int32 numFrames, then per-frame DICT (_r rotation, _t translation).
    //         nGRP - Group node: int32 nodeId, DICT attrs, int32 numChildren, then int32[] childIds.
    //         nSHP - Shape node: int32 nodeId, DICT attrs, int32 numModels (must be 1), int32 modelId, DICT modelAttrs. modelId maps to models in the model data [].
    //     RGBA     - Palette (1×): 256 × (R,G,B,A). Color[0-254] maps to palette index [1-255].
    //     MATL[]   - Material (per special material): int32 id, DICT properties (_type, _weight, _rough, _spec, _ior, _att, _flux, _plastic).
    //     LAYR[]   - Layer (per layer): int32 id, DICT attrs (_name, _hidden), int32 reserved (-1).
    //
    //   Data types used in chunks listed above:
    //     DICT     - int32 numPairs, then per-pair: STRING key, STRING value.
    //     STRING   - int32 bufferSize, then bufferSize bytes (no null terminator).
    //     ROTATION - single byte encoding a row-major rotation matrix via bit fields.
    public static ParsedVox ParseVoxFile(byte[] bytes, string path)
    {
        // Validate file header: "VOX " + version
        if (bytes.Length < 8 || Encoding.ASCII.GetString(bytes, 0, 4) != "VOX ") throw new InvalidOperationException($"Invalid .vox header in '{path}'.");
        int version = BitConverter.ToInt32(bytes, 4);
        if (version < 150) throw new InvalidOperationException($"Unsupported .vox version {version} in '{path}'. Minimum supported version is 0.99.7.2."); // 0.99.7.2 = 150

        // Container for the entire parsed .vox file's data
        var parsedVox = new ParsedVox(bytes, version);

        // MAIN chunk 
        // 
        // Starts at byte position 8
        int bytePosition = 8;
        var (mainChunkId, mainContentByteSize, mainChildrenByteSize) = ReadChunkHeader(bytes, ref bytePosition);
        if (mainChunkId != "MAIN") throw new InvalidOperationException($"Expected MAIN chunk in '{path}', got '{mainChunkId}'.");

        // Parse children of MAIN
        bytePosition += mainContentByteSize; // skip MAIN content (always 0, but be correct)
        int mainChildrenEndBytePosition = bytePosition + mainChildrenByteSize;

        // Read all child chunks of MAIN into a list
        var allMainChildChunks = new List<(string Id, int ContentByteSize, int ChunkStart, int ChunkFullByteSize)>();
        while (bytePosition < mainChildrenEndBytePosition)
        {
            int chunkStart = bytePosition;
            var (chunkId, contentByteSize, childrenByteSize) = ReadChunkHeader(bytes, ref bytePosition);
            int chunkFullByteSize = 12 /* Header */ + contentByteSize + childrenByteSize;
            allMainChildChunks.Add((chunkId, contentByteSize, chunkStart, chunkFullByteSize));
            bytePosition += contentByteSize + childrenByteSize;
        }

        // Extract chunks by type
        //
        // Note that we discard LAYR chunks since they aren't needed for rendering
        for (int i = 0; i < allMainChildChunks.Count; i++)
        {
            var (id, _, chunkStart, chunkFullByteSize) = allMainChildChunks[i];
            var fullChunkBytes = new Memory<byte>(bytes, chunkStart, chunkFullByteSize);

            if (id == "SIZE" && i + 1 < allMainChildChunks.Count && allMainChildChunks[i + 1].Id == "XYZI")
            {
                var (_, _, xyziChunkStart, xyziChunkFullByteSize) = allMainChildChunks[++i];
                parsedVox.ModelChunks.Add((new RawVoxChunk("SIZE", fullChunkBytes), new RawVoxChunk("XYZI", new Memory<byte>(bytes, xyziChunkStart, xyziChunkFullByteSize))));
            }
            else if (id is "nTRN" or "nGRP" or "nSHP") parsedVox.SceneGraphChunks.Add(new RawVoxChunk(id, fullChunkBytes));
            else if (id == "RGBA") parsedVox.RgbaChunk = fullChunkBytes;
            else if (id == "MATL") parsedVox.MatlChunks.Add(fullChunkBytes);
        }

        return parsedVox;
    }

    private static (string Id, int ContentByteSize, int ChildrenByteSize) ReadChunkHeader(byte[] bytes, ref int offset)
    {
        string id = Encoding.ASCII.GetString(bytes, offset, 4);
        int contentByteSize = BitConverter.ToInt32(bytes, offset + 4);
        int childrenByteSize = BitConverter.ToInt32(bytes, offset + 8);
        offset += 12;
        return (id, contentByteSize, childrenByteSize);
    }
}