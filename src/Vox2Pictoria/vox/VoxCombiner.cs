namespace Vox2Pictoria;

/// <summary>
/// Combines multiple multi-model .vox files into a single .vox by merging their models and scene graphs. Each input's models are offset by the user-specified center position for the input.
/// </summary>
/// <remarks>
/// TODO add validation to ensure that after translations, inputs do not overlap and form a perfect rectangle on the XY plane.
/// </remarks>
public static class VoxCombiner
{
    public static void Combine(Options options)
    {
        // Not combining
        List<(string voxRelativePath, int centerX, int centerY)> inputs = options.CombineInputs;
        if (inputs.Count == 0) throw new ArgumentException("No combine inputs specified.");

        // Parse each input .vox file at the raw chunk level
        var parsedInputs = new List<ParsedVox>(inputs.Count);
        for (int i = 0; i < inputs.Count; i++)
        {
            var (path, centerX, centerY) = inputs[i];

            // Get absolute file path
            string absolutePath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), path));
            if (!File.Exists(absolutePath)) throw new FileNotFoundException($"Input .vox file not found: {absolutePath}");

            // Read file bytes
            byte[] bytes = File.ReadAllBytes(absolutePath);

            // Parse .vox file into raw chunk data
            ParsedVox parsed = VoxParser.ParseVoxFile(bytes, path);
            parsedInputs.Add(parsed);

            Console.WriteLine($"Loaded: {path} ({parsed.ModelChunks.Count} models, center=({centerX},{centerY}))");
        }

        // Validate
        ValidateVersions(parsedInputs, inputs);
        ValidatePalettes(parsedInputs, inputs);

        // Build combined vox data
        CombinedVox combinedVox = CreateCombinedVox(parsedInputs, inputs);

        // Write combined .vox
        if (!Directory.Exists(options.TempDirectory)) Directory.CreateDirectory(options.TempDirectory);
        VoxWriter.WriteCombinedVox(options.VoxAbsolutePath, combinedVox);
    }

    private static CombinedVox CreateCombinedVox(List<ParsedVox> parsedInputs, List<(string Path, int CenterX, int CenterY)> combineInputs)
    {
        // Compute input model chunk start indices for model ID remapping in nSHP chunks
        int totalModels = 0;
        var inputModelChunkStartIndices = new List<int>(parsedInputs.Count);
        foreach (var input in parsedInputs)
        {
            inputModelChunkStartIndices.Add(totalModels);
            totalModels += input.ModelChunks.Count;
        }

        // Compute start scene graph node IDs for each input
        //
        // IDs 0 and 1 are reserved for the new root nTRN(0) and its child nGRP(1).
        // MagicaVoxel assigns node IDs sequentially 0..N-1, so each input needs SceneGraphChunks.Count slots.
        int nextNodeId = 2;
        var inputStartNodeIDs = new List<int>(parsedInputs.Count);
        for (int i = 0; i < parsedInputs.Count; i++)
        {
            inputStartNodeIDs.Add(nextNodeId);
            nextNodeId += parsedInputs[i].SceneGraphChunks.Count;
        }

        // Extract the node IDs of the root group of each input
        //
        // Why? VoxCombiner produces a .vox that the rest of Vox2Pictoria processes. The rest of Vox2Pictoria converts top level models/groups to Pictoria structures.
        // If we just put the root group of each input under the new root nGRP(1) of the combined .vox, then Vox2Pictoria tries to convert the root group of each input into a Pictoria structure!
        // That isn't what we want - we need to extract the child nodes of each input's root group, and put those child nodes under the new root nGRP(1) of the combined .vox.
        //
        // There is a potential complication - if an input's root group has transforms, they need to be applied to its child nodes. However, MagicaVoxel does not seem to allow transforms on the root nTRN(0) (nGRP(1)'s parent 
        // transform node), so we just check for them and throw if we find them (ValidateRootIsIdentity).
        var combinedRootGroupChildNodeIDs = new HashSet<int>();
        for (int i = 0; i < parsedInputs.Count; i++)
        {
            ParsedVox parsedInput = parsedInputs[i];
            (string Path, int CenterX, int CenterY) combineInput = combineInputs[i];

            // Validate that input root nTRN(0) has no transforms
            ValidateRootIsIdentity(parsedInput, combineInput.Path);

            // Extract child node IDs of root nGRP(1), applying the node ID offset for the combined file
            int idOffset = inputStartNodeIDs[i];
            foreach (int childId in GetSceneGroupChildNodeIDs(parsedInput, combineInput.Path)) combinedRootGroupChildNodeIDs.Add(childId + idOffset);
        }

        // Merge MATL chunks from all inputs, deduplicating by palette ID
        List<Memory<byte>> mergedMatlChunks = MergeMatlChunks(parsedInputs, combineInputs);

        // Build center translations list
        var inputCenterTranslations = new List<(int CenterX, int CenterY)>(combineInputs.Count);
        for (int i = 0; i < combineInputs.Count; i++)
        {
            (string Path, int CenterX, int CenterY) input = combineInputs[i];
            inputCenterTranslations.Add((input.CenterX, input.CenterY));
        }

        return new CombinedVox
        {
            Version = parsedInputs[0].Version, // Already validated that all inputs have the same version
            Inputs = parsedInputs,
            InputModelChunkStartIndices = inputModelChunkStartIndices,
            InputStartNodeIDs = inputStartNodeIDs,
            CombinedRootGroupChildNodeIDs = combinedRootGroupChildNodeIDs,
            InputCenterTranslations = inputCenterTranslations,
            RgbaChunk = parsedInputs[0].RgbaChunk, // Already validated that all inputs have the same palette
            MergedMatlChunks = mergedMatlChunks,
        };
    }

    private static List<Memory<byte>> MergeMatlChunks(List<ParsedVox> parsedInputs, List<(string Path, int CenterX, int CenterY)> combineInputs)
    {
        // Each input may define materials for different palette indices. We merge them, throwing if
        // two inputs define different properties for the same palette index.
        var matlChunksByPaletteId = new Dictionary<int, Memory<byte>>();
        for (int i = 0; i < parsedInputs.Count; i++)
        {
            foreach (Memory<byte> inputMatlChunk in parsedInputs[i].MatlChunks)
            {
                // MATL chunk content starts at byte 12 (after chunk header). First int32 is the palette ID.
                int paletteId = BitConverter.ToInt32(inputMatlChunk.Span[12..]);

                if (!matlChunksByPaletteId.TryGetValue(paletteId, out var existing))
                {
                    matlChunksByPaletteId[paletteId] = inputMatlChunk;
                    continue;
                }

                if (!existing.Span.SequenceEqual(inputMatlChunk.Span))
                    throw new InvalidOperationException($"MATL conflict for palette index {paletteId}: '{combineInputs[i].Path}' defines different material properties than a previous input.");
            }
        }

        return [.. matlChunksByPaletteId.Values];
    }

    private static void ValidateVersions(List<ParsedVox> inputs, List<(string Path, int CenterX, int CenterY)> combineInputs)
    {
        if (inputs.Count < 2) return;

        int referenceVersion = inputs[0].Version;
        for (int i = 1; i < inputs.Count; i++)
        {
            if (inputs[i].Version != referenceVersion)
                throw new InvalidOperationException($"Version mismatch: '{combineInputs[0].Path}' is version {referenceVersion} but '{combineInputs[i].Path}' is version {inputs[i].Version}.");
        }
    }

    private static HashSet<int> GetSceneGroupChildNodeIDs(ParsedVox parsedVox, string inputPath)
    {
        foreach (RawVoxChunk chunk in parsedVox.SceneGraphChunks)
        {
            // Not nGRP node
            if (chunk.Id != "nGRP") continue;

            // Not root nGRP(1)
            ReadOnlySpan<byte> content = chunk.ChunkContentBytes.Span;
            int bytePosition = 0;
            int nodeId = VoxBytesReader.ReadInt32(content, ref bytePosition);
            if (nodeId != 1) continue;

            // Skip attributes
            VoxBytesReader.SkipDictionary(content, ref bytePosition);

            // Read child IDs
            int numChildren = VoxBytesReader.ReadInt32(content, ref bytePosition);
            var childIds = new HashSet<int>(numChildren);
            for (int i = 0; i < numChildren; i++) childIds.Add(VoxBytesReader.ReadInt32(content, ref bytePosition));

            return childIds;
        }

        throw new InvalidOperationException($"Scene group (nGRP nodeId=1) not found in '{inputPath}'.");
    }

    private static void ValidateRootIsIdentity(ParsedVox parsedVox, string inputPath)
    {
        foreach (RawVoxChunk chunk in parsedVox.SceneGraphChunks)
        {
            // Not nTRN node
            if (chunk.Id != "nTRN") continue;

            // Not root nTRN(0)
            ReadOnlySpan<byte> content = chunk.ChunkContentBytes.Span;
            int bytePosition = 0;
            int nodeId = VoxBytesReader.ReadInt32(content, ref bytePosition);
            if (nodeId != 0) continue;

            // Skip node_attributes, child_id, reserved, layer, num_frames
            VoxBytesReader.SkipDictionary(content, ref bytePosition);
            bytePosition += 16; // child_id + reserved + layer + num_frames

            // Read frame attributes and check for _r or _t
            int numPairs = VoxBytesReader.ReadInt32(content, ref bytePosition);
            for (int i = 0; i < numPairs; i++)
            {
                // Read key
                string key = VoxBytesReader.ReadString(content, ref bytePosition);

                // Check for transformations
                if (key == "_r") throw new InvalidOperationException($"Input '{inputPath}' has a rotation on its root nTRN(0). Combined inputs must not have root rotations.");
                if (key == "_t") throw new InvalidOperationException($"Input '{inputPath}' has a translation on its root nTRN(0). Combined inputs must not have root translations.");

                // Skip value
                VoxBytesReader.SkipString(content, ref bytePosition);
            }
            return;
        }
        throw new InvalidOperationException($"Root transform (nTRN nodeId=0) not found in '{inputPath}'.");
    }

    private static void ValidatePalettes(List<ParsedVox> inputs, List<(string Path, int CenterX, int CenterY)> combineInputs)
    {
        if (inputs.Count < 2) return;

        Memory<byte>? referenceMemory = inputs[0].RgbaChunk;
        if (referenceMemory == null) return;
        ReadOnlySpan<byte> reference = referenceMemory.Value.Span;

        for (int i = 1; i < inputs.Count; i++)
        {
            Memory<byte>? otherMemory = inputs[i].RgbaChunk ?? throw new InvalidOperationException($"Palette missing in '{combineInputs[i].Path}'.");
            ReadOnlySpan<byte> other = otherMemory.Value.Span;

            if (reference.Length != other.Length) throw new InvalidOperationException($"Palette size mismatch between '{combineInputs[0].Path}' and '{combineInputs[i].Path}'.");

            // Compare RGBA content (after 12-byte chunk header). Each palette entry is 4 bytes (R, G, B, A).
            ReadOnlySpan<byte> refContent = reference[12..];
            ReadOnlySpan<byte> otherContent = other[12..];
            for (int j = 0; j < refContent.Length; j++)
            {
                if (refContent[j] == otherContent[j]) continue;

                int paletteIndex = j / 4 + 1; // 1-based palette index
                throw new InvalidOperationException($"Palette mismatch between '{combineInputs[0].Path}' and '{combineInputs[i].Path}' at palette index {paletteIndex} (byte offset {j}).");
            }
        }
    }
}
