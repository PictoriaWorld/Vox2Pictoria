using System.Text;

namespace Vox2Pictoria;

public static class VoxWriter
{
    public static void WriteCombinedVox(string outputPath, CombinedVox combinedVox)
    {
        using var stream = new FileStream(outputPath, FileMode.Create, FileAccess.Write);
        using var writer = new BinaryWriter(stream);

        // Header: "VOX " + version
        writer.Write(Encoding.ASCII.GetBytes("VOX "));
        writer.Write(combinedVox.Version);

        // MAIN chunk header (children size patched after writing all children)
        WriteChunkHeader(writer, "MAIN", 0);
        long childrenSizePosition = stream.Position - 4;

        // Write all model chunks (SIZE+XYZI pairs)
        foreach (var input in combinedVox.Inputs)
        {
            foreach (var (sizeChunk, xyziChunk) in input.ModelChunks)
            {
                writer.Write(sizeChunk.FullChunkBytes.Span);
                writer.Write(xyziChunk.FullChunkBytes.Span);
            }
        }

        // Write combined scene graph
        //
        // New root: nTRN(0) → nGRP(1) → [each input's remapped nTRN(0)]
        WriteNTrnChunk(writer, 0, 1, "_name", "root", null);
        WriteNGrpChunk(writer, 1, combinedVox.InputStartNodeIDs);

        for (int i = 0; i < combinedVox.Inputs.Count; i++)
        {
            int inputStartNodeID = combinedVox.InputStartNodeIDs[i];
            int inputModelChunkStartIndex = combinedVox.InputModelChunkStartIndices[i];
            int inputCenterX = combinedVox.InputCenterTranslations[i].CenterX;
            int inputCenterY = combinedVox.InputCenterTranslations[i].CenterY;
            ParsedVox input = combinedVox.Inputs[i];

            foreach (RawVoxChunk chunk in input.SceneGraphChunks)
            {
                ReadOnlySpan<byte> content = chunk.ChunkContentBytes.Span;

                if (chunk.Id == "nTRN") WriteRemappedNTrn(writer, content, inputStartNodeID, inputCenterX, inputCenterY);
                else if (chunk.Id == "nGRP") WriteRemappedNGrp(writer, content, inputStartNodeID);
                else if (chunk.Id == "nSHP") WriteRemappedNShp(writer, content, inputStartNodeID, inputModelChunkStartIndex);
            }
        }

        // Write RGBA
        if (combinedVox.RgbaChunk != null) writer.Write(combinedVox.RgbaChunk.Value.Span);

        // Write MATL chunks
        foreach (var matlChunk in combinedVox.MergedMatlChunks) writer.Write(matlChunk.Span);

        // Patch MAIN children size
        long endPosition = stream.Position;
        int childrenSize = (int)(endPosition - childrenSizePosition - 4);
        stream.Position = childrenSizePosition;
        writer.Write(childrenSize);
        stream.Position = endPosition;

        Console.WriteLine($"Combined .vox written to: {outputPath}. Number of inputs: {combinedVox.Inputs.Count}");
    }

    private static void WriteRemappedNTrn(BinaryWriter writer, ReadOnlySpan<byte> content, int idOffset, int centerX, int centerY)
    {
        // nTRN layout:
        //   int32 node_id
        //   DICT  node_attributes
        //   int32 child_node_id
        //   int32 reserved_id
        //   int32 layer_id
        //   int32 num_frames
        //   DICT  frame_attributes (contains _t and optionally _r)

        int bytePosition = 0;

        // Update node ID
        int nodeId = ReadInt32(content, ref bytePosition);
        int newNodeId = nodeId + idOffset;

        // Record node attributes start and end for raw copying
        int nodeAttributesStart = bytePosition;
        SkipDictionary(content, ref bytePosition);
        int nodeAttributesEnd = bytePosition;

        // Update child node ID
        int newChildId = ReadInt32(content, ref bytePosition) + idOffset;

        // Record reserved/layer/frames start for raw copying
        int reservedLayerFramesStart = bytePosition;
        bytePosition += 12; // reserved_id + layer_id + num_frames

        // Update translation for input root nTRN
        int frameAttributesStart = bytePosition;
        int contentsByteSize;
        Dictionary<string, string>? frameAttributes = null;
        if (nodeId == 0)
        {
            // Root nTRN: apply center offset to frame attributes
            frameAttributes = ReadDictionary(content, ref bytePosition);

            if (frameAttributes.TryGetValue("_t", out string? tValue))
            {
                string[] parts = tValue.Split(' ');
                int tx = int.Parse(parts[0]) + centerX;
                int ty = int.Parse(parts[1]) + centerY;
                int tz = int.Parse(parts[2]);
                frameAttributes["_t"] = $"{tx} {ty} {tz}";
            }
            else frameAttributes["_t"] = $"{centerX} {centerY} 0";

            contentsByteSize = frameAttributesStart + GetDictionaryByteSize(frameAttributes);
        }
        else contentsByteSize = content.Length;

        // Write to file
        WriteChunkHeader(writer, "nTRN", contentsByteSize);
        writer.Write(newNodeId);
        writer.Write(content[nodeAttributesStart..nodeAttributesEnd]);
        writer.Write(newChildId);
        if (nodeId == 0)
        {
            writer.Write(content[reservedLayerFramesStart..frameAttributesStart]);
            WriteDictionary(writer, frameAttributes!);
        }
        else writer.Write(content[reservedLayerFramesStart..]);
    }

    private static void WriteRemappedNGrp(BinaryWriter writer, ReadOnlySpan<byte> content, int idOffset)
    {
        // nGRP layout:
        //   int32 node_id
        //   DICT  node_attributes
        //   int32 num_children
        //   int32[] child_ids

        // Content size unchanged (only int32 values remapped)
        WriteChunkHeader(writer, "nGRP", content.Length);

        int bytePosition = 0;

        // Update node ID
        writer.Write(ReadInt32(content, ref bytePosition) + idOffset);

        // Copy node attributes dict
        CopyDictionary(writer, content, ref bytePosition);

        // Update child IDs
        int numChildren = ReadInt32(content, ref bytePosition);
        writer.Write(numChildren);
        for (int i = 0; i < numChildren; i++) writer.Write(ReadInt32(content, ref bytePosition) + idOffset);
    }

    private static void WriteRemappedNShp(BinaryWriter writer, ReadOnlySpan<byte> content, int idOffset, int modelOffset)
    {
        // nSHP layout:
        //   int32 node_id
        //   DICT  node_attributes
        //   int32 num_models
        //   For each model:
        //     int32 model_id
        //     DICT  model_attributes

        // Content size unchanged (only int32 values remapped)
        WriteChunkHeader(writer, "nSHP", content.Length);

        int bytePosition = 0;

        // Update node ID
        writer.Write(ReadInt32(content, ref bytePosition) + idOffset);

        // Copy node attributes dict
        CopyDictionary(writer, content, ref bytePosition);

        // Models
        int numModels = ReadInt32(content, ref bytePosition);
        writer.Write(numModels);
        for (int i = 0; i < numModels; i++)
        {
            // Update model ID
            writer.Write(ReadInt32(content, ref bytePosition) + modelOffset);

            // Copy model attributes dict
            CopyDictionary(writer, content, ref bytePosition);
        }
    }

    private static void WriteNTrnChunk(BinaryWriter writer, int nodeId, int childId, string? attrKey, string? attrVal, string? translation)
    {
        Dictionary<string, string>? nodeAttributes = (attrKey != null && attrVal != null) ? new Dictionary<string, string> { [attrKey] = attrVal } : null;
        Dictionary<string, string>? frameAttributes = (translation != null) ? new Dictionary<string, string> { ["_t"] = translation } : null;

        WriteChunkHeader(writer, "nTRN", 20 /* nodeId + childId + reserved + layer + numFrames */ + GetDictionaryByteSize(nodeAttributes) + GetDictionaryByteSize(frameAttributes));
        writer.Write(nodeId);
        WriteDictionary(writer, nodeAttributes);
        writer.Write(childId);
        writer.Write(-1); // reserved
        writer.Write(-1); // layer
        writer.Write(1);  // num_frames
        WriteDictionary(writer, frameAttributes);
    }

    private static void WriteNGrpChunk(BinaryWriter writer, int nodeId, List<int> childIds)
    {
        WriteChunkHeader(writer, "nGRP", 12 /* nodeId + empty dict (4 bytes for count=0) + numChildren */ + 4 * childIds.Count);
        writer.Write(nodeId);
        WriteDictionary(writer, null);
        writer.Write(childIds.Count);
        foreach (int id in childIds) writer.Write(id);
    }

    #region Helpers
    private static void WriteChunkHeader(BinaryWriter writer, string chunkId, int contentByteSize)
    {
        writer.Write(Encoding.ASCII.GetBytes(chunkId));
        writer.Write(contentByteSize);
        writer.Write(0); // children size
    }

    private static int ReadInt32(ReadOnlySpan<byte> bytes, ref int bytePosition)
    {
        int value = BitConverter.ToInt32(bytes[bytePosition..]);
        bytePosition += 4;
        return value;
    }

    private static void CopyDictionary(BinaryWriter writer, ReadOnlySpan<byte> bytes, ref int bytePosition)
    {
        int start = bytePosition;
        SkipDictionary(bytes, ref bytePosition);
        writer.Write(bytes[start..bytePosition]);
    }

    private static void SkipDictionary(ReadOnlySpan<byte> bytes, ref int bytePosition)
    {
        int numPairs = BitConverter.ToInt32(bytes[bytePosition..]);
        bytePosition += 4;
        for (int i = 0; i < numPairs; i++)
        {
            int keyLength = BitConverter.ToInt32(bytes[bytePosition..]);
            bytePosition += 4 + keyLength;
            int valueLength = BitConverter.ToInt32(bytes[bytePosition..]);
            bytePosition += 4 + valueLength;
        }
    }

    private static Dictionary<string, string> ReadDictionary(ReadOnlySpan<byte> bytes, ref int bytePosition)
    {
        var dictionary = new Dictionary<string, string>();
        int numPairs = BitConverter.ToInt32(bytes[bytePosition..]);
        bytePosition += 4;
        for (int i = 0; i < numPairs; i++)
        {
            int keyLength = BitConverter.ToInt32(bytes[bytePosition..]);
            bytePosition += 4;
            string key = Encoding.UTF8.GetString(bytes.Slice(bytePosition, keyLength));
            bytePosition += keyLength;
            int valueLength = BitConverter.ToInt32(bytes[bytePosition..]);
            bytePosition += 4;
            string value = Encoding.UTF8.GetString(bytes.Slice(bytePosition, valueLength));
            bytePosition += valueLength;

            dictionary[key] = value;
        }
        return dictionary;
    }

    private static int GetDictionaryByteSize(Dictionary<string, string>? pairs)
    {
        if (pairs == null) return 4; // empty dict: just numPairs=0
        int size = 4;
        foreach (var kvp in pairs)
        {
            size += 4 + Encoding.UTF8.GetByteCount(kvp.Key);
            size += 4 + Encoding.UTF8.GetByteCount(kvp.Value);
        }
        return size;
    }

    private static void WriteDictionary(BinaryWriter writer, Dictionary<string, string>? pairs)
    {
        if (pairs == null) { writer.Write(0); return; }
        writer.Write(pairs.Count);
        Span<byte> buffer = stackalloc byte[256];
        foreach (var kvp in pairs)
        {
            int keyLen = Encoding.UTF8.GetBytes(kvp.Key, buffer);
            writer.Write(keyLen);
            writer.Write(buffer[..keyLen]);

            int valLen = Encoding.UTF8.GetBytes(kvp.Value, buffer);
            writer.Write(valLen);
            writer.Write(buffer[..valLen]);
        }
    }
    #endregion
}
