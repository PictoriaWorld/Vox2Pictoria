namespace Vox2Pictoria;

/// <summary>
/// Pre-computed data for writing a combined .vox file.
/// Built by VoxCombiner, consumed by VoxWriter.
/// </summary>
public class CombinedVox
{
    public required int Version { get; init; }

    // Per-input data (parallel lists, indexed by input index)
    public required List<ParsedVox> Inputs { get; init; }
    public required List<int> InputModelChunkStartIndices { get; init; }
    public required List<int> InputStartNodeIDs { get; init; }
    public required HashSet<int> CombinedRootGroupChildNodeIDs { get; init; }
    public required List<(int CenterX, int CenterY)> InputCenterTranslations { get; init; }

    // Merged data
    public required Memory<byte>? RgbaChunk { get; init; }
    public required List<Memory<byte>> MergedMatlChunks { get; init; }
}
