namespace Vox2Pictoria;

/// <summary>
/// Stored in the global transformed voxel grid (keyed by world-space min coordinates). Used for:
/// 1. Determining what to include in OBJs - face visibilities is checked when generating structure OBJs.
/// 2. Determining whether a model's voxels are occluded by neighbouring model voxels - key existence in the global transformed voxel grid and the IsGlass property are used for this.
/// </summary>
public readonly record struct TransformedVoxelInfo(CuboidFaceVisibilities FaceVisibilities, bool IsGlass);
