using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using FileToVoxCore.Vox;

namespace Vox2Pictoria;

public class VoxelGridService
{
    public static Dictionary<int, Dictionary<int, VisibleVoxelInfo>> CreateVoxelFrameVisibleVoxelInfoMap(VoxModel model)
    {
        DateTime currentTime = DateTime.Now;

        // Create voxelFrameVisibleVoxelInfoMap
        Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap = [];
        for (int i = 0; i < model.VoxelFrames.Count; i++)
        {
            voxelFrameVisibleVoxelInfoMap[i] = [];
        }

        // Process voxel frames
        Parallel.ForEach(model.VoxelFrames, (voxelFrame, state, index) => CreateVoxelIndexVisibleVoxelInfoMap(voxelFrame, voxelFrameVisibleVoxelInfoMap[(int)index]));

        Console.WriteLine($"Create voxel-frame visible-face-info map duration: {(DateTime.Now - currentTime).TotalSeconds} s");
        return voxelFrameVisibleVoxelInfoMap;
    }

    public static void CreateVoxelIndexVisibleVoxelInfoMap(VoxelData voxelFrame, Dictionary<int, VisibleVoxelInfo> voxelIndexVisibleVoxelInfoMap)
    {
        int untransformedXLength = voxelFrame.VoxelsWide;
        int untransformedYLength = voxelFrame.VoxelsTall;
        int untransformedZLength = voxelFrame.VoxelsDeep;
        int untransformedXAndYLengthsProduct = untransformedXLength * untransformedYLength;
        // Minus 2 (untransformedXLength - 2) because frame *data* has extra, empty cells as maxs.
        int untransformedMaxMinXCoordinate = untransformedXLength - 2;
        int untransformedMaxMinYCoordinate = untransformedYLength - 2;
        int untransformedMaxMinZCoordinate = untransformedZLength - 2;

        foreach (KeyValuePair<int, byte> voxelIndexPaletteNumber in voxelFrame.Colors)
        {
            // Get untransformed coordinates
            Cuboid untransformedVoxelBoundingBox = VoxelCoordinatesService.VoxelIndexToUntransformedVoxelBoundingBox(voxelIndexPaletteNumber.Key, untransformedXLength, untransformedXAndYLengthsProduct);

            CuboidFaceVisibilities cuboidFaceVisibilities = new(GetMinusFaceVisibility(VoxelCoordinatesService.CheckIfUntransformedNeighbourOccupied(untransformedVoxelBoundingBox.MinX - 1, untransformedVoxelBoundingBox.MinY,
                    untransformedVoxelBoundingBox.MinZ, untransformedXLength, untransformedXAndYLengthsProduct, voxelFrame), untransformedVoxelBoundingBox.MinX),
                GetPlusFaceVisibility(VoxelCoordinatesService.CheckIfUntransformedNeighbourOccupied(untransformedVoxelBoundingBox.MaxX, untransformedVoxelBoundingBox.MinY, untransformedVoxelBoundingBox.MinZ, untransformedXLength,
                    untransformedXAndYLengthsProduct, voxelFrame), untransformedVoxelBoundingBox.MinX, untransformedMaxMinXCoordinate),
                GetMinusFaceVisibility(VoxelCoordinatesService.CheckIfUntransformedNeighbourOccupied(untransformedVoxelBoundingBox.MinX, untransformedVoxelBoundingBox.MinY - 1, untransformedVoxelBoundingBox.MinZ,
                    untransformedXLength, untransformedXAndYLengthsProduct, voxelFrame), untransformedVoxelBoundingBox.MinY),
                GetPlusFaceVisibility(VoxelCoordinatesService.CheckIfUntransformedNeighbourOccupied(untransformedVoxelBoundingBox.MinX, untransformedVoxelBoundingBox.MaxY, untransformedVoxelBoundingBox.MinZ, untransformedXLength,
                    untransformedXAndYLengthsProduct, voxelFrame), untransformedVoxelBoundingBox.MinY, untransformedMaxMinYCoordinate),
                GetMinusFaceVisibility(VoxelCoordinatesService.CheckIfUntransformedNeighbourOccupied(untransformedVoxelBoundingBox.MinX, untransformedVoxelBoundingBox.MinY, untransformedVoxelBoundingBox.MinZ - 1,
                    untransformedXLength, untransformedXAndYLengthsProduct, voxelFrame), untransformedVoxelBoundingBox.MinZ),
                GetPlusFaceVisibility(VoxelCoordinatesService.CheckIfUntransformedNeighbourOccupied(untransformedVoxelBoundingBox.MinX, untransformedVoxelBoundingBox.MinY, untransformedVoxelBoundingBox.MaxZ, untransformedXLength,
                    untransformedXAndYLengthsProduct, voxelFrame), untransformedVoxelBoundingBox.MinZ, untransformedMaxMinZCoordinate));

            if (cuboidFaceVisibilities.AnyVisible())
            {
                // Get untransformed face visibility
                VisibleVoxelInfo visibleVoxelInfo = new(ref cuboidFaceVisibilities, ref untransformedVoxelBoundingBox, voxelIndexPaletteNumber.Value);

                // Add to map
                voxelIndexVisibleVoxelInfoMap[voxelIndexPaletteNumber.Key] = visibleVoxelInfo;
            }
        }
    }

    public static void GetVisibleVoxelsGrid(Dictionary<string, StructureInfo> structureNameStructureInfoMap, VoxModel model, Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap,
        ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap)
    {
        // Populate transformed voxel grid
        //
        // We use this collection to determine which faces can be omitted as well as to create occluded faces objs
        DateTime currentTime = DateTime.Now;
        Parallel.ForEach(structureNameStructureInfoMap.Values, structureInfo => AddStructureVoxels(structureInfo, model, voxelFrameVisibleVoxelInfoMap, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap));
        Console.WriteLine($"Populate transformed voxel grid duration: {(DateTime.Now - currentTime).TotalSeconds} s");
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    static void AddStructureVoxels(StructureInfo structureInfo, VoxModel model, Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap,
        ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap)
    {
        if (structureInfo.ShapeInfo.ChildShapeInfos.Count == 0)
        {
            AddShapeVoxels(structureInfo.ShapeInfo, model, voxelFrameVisibleVoxelInfoMap, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap);
        }
        else
        {
            Parallel.ForEach(structureInfo.ShapeInfo.ChildShapeInfos, childShapeInfo => AddShapeVoxels(childShapeInfo, model, voxelFrameVisibleVoxelInfoMap, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap));
        }
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private static void AddShapeVoxels(ShapeInfo shapeInfo, VoxModel model, Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap,
        ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap)
    {
        if (shapeInfo.FrameInfo == null || shapeInfo.FrameInfo.VoxelFrameIndex < 0)
        {
            throw new InvalidOperationException("FrameInfo should not be null and VoxelFrameIndex of FrameInfo belonging to structure with only one shape must not be less than 0");
        }
        Dictionary<int, VisibleVoxelInfo> voxelIndexVisibleVoxelInfoMap = voxelFrameVisibleVoxelInfoMap[shapeInfo.FrameInfo.VoxelFrameIndex];
        Matrix4x4Int transformMatrix = shapeInfo.TransformMatrix;

        // Get pre-rotataion directions
        Direction[] postPreRotationDirectionsMap = shapeInfo.PostPreRotationDirectionsMap;
        Direction minusXPreRotatationDirection = postPreRotationDirectionsMap[(int)Direction.MinusX];
        Direction plusXPreRotatationDirection = postPreRotationDirectionsMap[(int)Direction.PlusX];
        Direction minusYPreRotatationDirection = postPreRotationDirectionsMap[(int)Direction.MinusY];
        Direction plusYPreRotatationDirection = postPreRotationDirectionsMap[(int)Direction.PlusY];
        Direction minusZPreRotatationDirection = postPreRotationDirectionsMap[(int)Direction.MinusZ];
        Direction plusZPreRotatationDirection = postPreRotationDirectionsMap[(int)Direction.PlusZ];

        // Add voxels
        foreach (KeyValuePair<int, VisibleVoxelInfo> voxelIndexFaceInfo in voxelIndexVisibleVoxelInfoMap)
        {
            // Get face visibilities after transforms
            CuboidFaceVisibilities untransformedCuboidFaceVisibilities = voxelIndexFaceInfo.Value.CuboidFaceVisibilities;
            CuboidFaceVisibilities cuboidFaceVisibilities = new(untransformedCuboidFaceVisibilities.GetFaceVisibility(minusXPreRotatationDirection),
                untransformedCuboidFaceVisibilities.GetFaceVisibility(plusXPreRotatationDirection),
                untransformedCuboidFaceVisibilities.GetFaceVisibility(minusYPreRotatationDirection),
                untransformedCuboidFaceVisibilities.GetFaceVisibility(plusYPreRotatationDirection),
                untransformedCuboidFaceVisibilities.GetFaceVisibility(minusZPreRotatationDirection),
                untransformedCuboidFaceVisibilities.GetFaceVisibility(plusZPreRotatationDirection)); // Unused

            // Get untransformed coordinates
            Cuboid untransformedVoxelBoundingBox = voxelIndexFaceInfo.Value.UntransformedVoxelBoundingBox;

            // Get transformed coordinates
            Vector3Int transformedMinCoordinates = VoxelCoordinatesService.UntransformedToTransformedVoxelMinCoordinates(ref untransformedVoxelBoundingBox, ref transformMatrix);

            // Add
            transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap[transformedMinCoordinates] = cuboidFaceVisibilities;
        }
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private static FaceVisibility GetPlusFaceVisibility(bool neighbourOccupied, float axisUntransformedMinCoordinate, int axisUntransformedMaxCoordinate)
    {
        if (neighbourOccupied)
        {
            return FaceVisibility.Hidden;
        }

        return axisUntransformedMinCoordinate == axisUntransformedMaxCoordinate ? FaceVisibility.VisibleAtFrameEdge : FaceVisibility.Visible;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private static FaceVisibility GetMinusFaceVisibility(bool neighbourOccupied, float axisUntransformedMinCoordinate)
    {
        if (neighbourOccupied)
        {
            return FaceVisibility.Hidden;
        }

        return axisUntransformedMinCoordinate == 0 ? FaceVisibility.VisibleAtFrameEdge : FaceVisibility.Visible;
    }
}