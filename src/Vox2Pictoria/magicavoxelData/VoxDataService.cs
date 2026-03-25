using FileToVoxCore.Vox;
using FileToVoxCore.Vox.Chunks;

namespace Vox2Pictoria;

public class VoxDataService
{
    private static readonly int[] HeightLimits = ComputeHeightLimits();

    private static int[] ComputeHeightLimits()
    {
        var limits = new int[15];
        limits[0] = 1;
        double sqrt2048 = Math.Sqrt(2048);
        double sqrt3 = Math.Sqrt(3);
        for (int i = 1; i < limits.Length; i++)
        {
            limits[i] = Math.Min(Constants.ChunkCartesianHeight, (int)Math.Floor((i + 1) * sqrt2048 / sqrt3));
        }
        return limits;
    }

    public static (int tileXLength, int tileZLength) ComputeTileLengths(int maxPictoriaX, int maxPictoriaZ)
    {
        int tileXLength = (int)Math.Ceiling(2 * maxPictoriaX / (double)Constants.TileCartesianWidth);
        int tileZLength = (int)Math.Ceiling(2 * maxPictoriaZ / (double)Constants.TileCartesianWidth);
        return (tileXLength, tileZLength);
    }

    // Resources:
    //
    // - https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox-extension.txt
    // - https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox.txt
    public static Dictionary<string, StructureInfo> ExtractStructureDataFromVox(VoxModel model, bool noValidation = false)
    {
        // Get frame infos
        //
        // Each shape has an associated "frame". The frame's dimensions are the dimensions of the shape. Multiple shapes may have the same frame.
        List<FrameInfo> frameInfoList = GetFrameInfos(model);

        // Get shape infos
        //
        // The ShapeNodeChunk's ID is the child ID of the associated TransformNodeChunk. We need this ID to get the shape's location.
        Dictionary<int, ShapeInfo> shapeIDShapeInfoMap = GetShapeIDInfoMap(model, frameInfoList);

        // Apply transforms to shapes
        //
        // Each TransformNodeChunk's child ID is either a ShapeNodeChunk's ID or a GroupNodeChunk's ID. Here we deal with the former. We deal with the latter in a later loop.
        (Dictionary<int, ShapeInfo> transformNodeChunkIDShapeInfoMap, int transformNodeIndex) = ApplyTransformsToShapesAndGetTransformNodeChunkIDShapeInfoMap(shapeIDShapeInfoMap, model);

        // Get group infos
        //
        // A group is a set of shapes that form a structure. The GroupNodeChunk's ID is the child ID of the associated TransformNodeChunk.
        Dictionary<int, int[]> groupIDChildIDsMap = GetGroupIDChildIDsMap(model);

        // Handle structures formed by a group of shapes
        ProcessGroupTransformNodes(model, groupIDChildIDsMap, transformNodeChunkIDShapeInfoMap, ref transformNodeIndex);

        // Create StructureInfos
        Dictionary<string, StructureInfo> structureNameStructureInfoMap = CreateStructureInfos(transformNodeChunkIDShapeInfoMap);

        // Validate no intersecting bounding boxes
        if (!noValidation) ValidateNoIntersectingBoundingBoxes(structureNameStructureInfoMap);

        // Set structure image dimensions
        SetStructureImageDimensions(structureNameStructureInfoMap);

        // Set Pictoria locations
        SetPictoriaLocations(structureNameStructureInfoMap);

        // Validate property bounds and height limits
        if (!noValidation) ValidatePropertyBoundsAndHeightLimits(structureNameStructureInfoMap);

        return structureNameStructureInfoMap;
    }

    static void SetPictoriaLocations(Dictionary<string, StructureInfo> structureNameStructureInfoMap)
    {
        // Get bounding box
        double minX = double.MaxValue;
        double maxX = double.MinValue;
        double minZ = double.MaxValue;
        double maxZ = double.MinValue;
        foreach (StructureInfo structureInfo in structureNameStructureInfoMap.Values)
        {
            minX = Math.Min(minX, structureInfo.ShapeInfo.PictoriaLocation.MinX);
            maxX = Math.Max(maxX, structureInfo.ShapeInfo.PictoriaLocation.MaxX);
            minZ = Math.Min(minZ, structureInfo.ShapeInfo.PictoriaLocation.MinZ);
            maxZ = Math.Max(maxZ, structureInfo.ShapeInfo.PictoriaLocation.MaxZ);
        }
        if (minX + maxX != 0 || minZ + maxZ != 0)
        {
            throw new InvalidOperationException($"Bounding box is not centered around origin (0, 0). Current bounds are minX: {minX}, maxX: {maxX}, minZ: {minZ}, maxZ: {maxZ}.");
        }

        // Get bounding box lengths
        int xLength = (int)(maxX - minX);
        int zLength = (int)(maxZ - minZ);
        if (xLength % 2 != 0 || zLength % 2 != 0)
        {
            throw new InvalidOperationException($"Both xLength and zLength must be even. Current lengths are xLength: {xLength}, zLength: {zLength}.");
        }
    }

    static void ValidatePropertyBoundsAndHeightLimits(Dictionary<string, StructureInfo> structureNameStructureInfoMap)
    {
        // Compute scene bounds
        int maxPictoriaX = int.MinValue;
        int maxPictoriaZ = int.MinValue;
        foreach (StructureInfo structureInfo in structureNameStructureInfoMap.Values)
        {
            Cuboid location = structureInfo.ShapeInfo.PictoriaLocation;
            maxPictoriaX = Math.Max(maxPictoriaX, location.MaxX);
            maxPictoriaZ = Math.Max(maxPictoriaZ, location.MaxZ);
        }

        // Compute tile dimensions and property rect
        (int tileXLength, int tileZLength) = ComputeTileLengths(maxPictoriaX, maxPictoriaZ);
        int propertyHalfX = tileXLength * Constants.TileCartesianWidth / 2;
        int propertyHalfZ = tileZLength * Constants.TileCartesianWidth / 2;

        var violations = new List<string>();

        foreach ((string structureName, StructureInfo structureInfo) in structureNameStructureInfoMap)
        {
            Cuboid location = structureInfo.ShapeInfo.PictoriaLocation;

            // Check below ground
            if (location.MinY < 0)
            {
                violations.Add($"  '{structureName}': extends below ground (minY = {location.MinY})");
            }

            // Check absolute height limit
            if (location.MaxY > Constants.ChunkCartesianHeight)
            {
                violations.Add($"  '{structureName}': exceeds max height {Constants.ChunkCartesianHeight} (maxY = {location.MaxY})");
            }

            // Find required inset from height limit table
            int maxY = location.MaxY;
            int insetIndex = -1;
            for (int i = 0; i < HeightLimits.Length; i++)
            {
                if (maxY <= HeightLimits[i])
                {
                    insetIndex = i;
                    break;
                }
            }

            if (insetIndex == -1)
            {
                // Height exceeds all entries — already caught by ChunkCartesianHeight check above
                continue;
            }

            int inset = insetIndex * Constants.TileCartesianWidth;
            int allowedMinX = -propertyHalfX + inset;
            int allowedMaxX = propertyHalfX - inset;
            int allowedMinZ = -propertyHalfZ + inset;
            int allowedMaxZ = propertyHalfZ - inset;

            if (location.MinX < allowedMinX || location.MaxX > allowedMaxX ||
                location.MinZ < allowedMinZ || location.MaxZ > allowedMaxZ)
            {
                violations.Add(
                    $"  '{structureName}': height {maxY} requires inset {inset} (height limit index {insetIndex}), " +
                    $"allowed XZ bounds [{allowedMinX}, {allowedMaxX}] x [{allowedMinZ}, {allowedMaxZ}], " +
                    $"but structure XZ bounds [{location.MinX}, {location.MaxX}) x [{location.MinZ}, {location.MaxZ})");
            }
        }

        if (violations.Count > 0)
        {
            throw new InvalidOperationException(
                $"Property bounds / height limit violations detected (property: {tileXLength}x{tileZLength} tiles, " +
                $"rect [{-propertyHalfX}, {propertyHalfX}] x [{-propertyHalfZ}, {propertyHalfZ}]):\n" +
                string.Join("\n", violations));
        }
    }

    static void SetStructureImageDimensions(Dictionary<string, StructureInfo> structureNameStructureInfoMap)
    {
        foreach (StructureInfo structureInfo in structureNameStructureInfoMap.Values)
        {
            var isometricPolygon = new IsometricPolygon();

            if (structureInfo.VolumeType == VolumeType.PlusXPrism)
            {
                Cuboid location = structureInfo.ShapeInfo.PictoriaLocation;
                isometricPolygon.AddCartesianPoint(location.MinX, location.MinY, location.MinZ);
                isometricPolygon.AddCartesianPoint(location.MinX, location.MinY, location.MaxZ);
                isometricPolygon.AddCartesianPoint(location.MaxX, location.MinY, location.MaxZ);
                isometricPolygon.AddCartesianPoint(location.MaxX, location.MinY, location.MinZ);
                isometricPolygon.AddCartesianPoint(location.MaxX, location.MaxY, location.MinZ);
                isometricPolygon.AddCartesianPoint(location.MaxX, location.MaxY, location.MaxZ);
            }
            else if (structureInfo.VolumeType == VolumeType.PlusZPrism)
            {
                Cuboid location = structureInfo.ShapeInfo.PictoriaLocation;
                isometricPolygon.AddCartesianPoint(location.MinX, location.MinY, location.MinZ);
                isometricPolygon.AddCartesianPoint(location.MinX, location.MinY, location.MaxZ);
                isometricPolygon.AddCartesianPoint(location.MaxX, location.MinY, location.MaxZ);
                isometricPolygon.AddCartesianPoint(location.MaxX, location.MinY, location.MinZ);
                isometricPolygon.AddCartesianPoint(location.MinX, location.MaxY, location.MaxZ);
                isometricPolygon.AddCartesianPoint(location.MaxX, location.MaxY, location.MaxZ);
            }
            else
            {
                isometricPolygon.SetCuboid(structureInfo.ShapeInfo.PictoriaLocation);
            }

            structureInfo.SetIsometricPolygon(isometricPolygon);
        }
    }

    private static List<FrameInfo> GetFrameInfos(VoxModel model)
    {
        var frameInfoList = new List<FrameInfo>(model.VoxelFrames.Count);
        for (int i = 0; i < model.VoxelFrames.Count; i++)
        {
            var frameInfo = new FrameInfo(i);

            // Get frame dimensions
            VoxelData voxelFrame = model.VoxelFrames[i];
            frameInfo.SetMagicaVoxelDimensions(voxelFrame.VoxelsWide - 1, voxelFrame.VoxelsTall - 1, voxelFrame.VoxelsDeep - 1);

            // Add to list
            frameInfoList.Add(frameInfo);
        }

        return frameInfoList;
    }

    private static Dictionary<int, ShapeInfo> GetShapeIDInfoMap(VoxModel model, List<FrameInfo> frameInfoList)
    {
        var shapeIDShapeInfoMap = new Dictionary<int, ShapeInfo>(model.ShapeNodeChunks.Count);
        foreach (ShapeNodeChunk shapeNodeChunk in model.ShapeNodeChunks)
        {
            // Get model ID, this corresponds to the index of the structure's frame in the frame list
            int modelId = shapeNodeChunk.Models[0].ModelId;
            if (modelId < 0 || modelId >= frameInfoList.Count)
            {
                throw new Exception($"No VoxelFrame exists for ModelId: {modelId}");
            }

            // Get frame info
            FrameInfo frameInfo = frameInfoList[modelId];

            // Create structure info
            var shapeInfo = new ShapeInfo(frameInfo);

            // Add to map
            shapeIDShapeInfoMap.Add(shapeNodeChunk.Id, shapeInfo);
        }

        return shapeIDShapeInfoMap;
    }

    private static (Dictionary<int, ShapeInfo>, int) ApplyTransformsToShapesAndGetTransformNodeChunkIDShapeInfoMap(Dictionary<int, ShapeInfo> shapeIDShapeInfoMap, VoxModel model)
    {
        var transformNodeChunkIDShapeInfoMap = new Dictionary<int, ShapeInfo>();
        int transformNodeIndex = 0;
        foreach (TransformNodeChunk transformNodeChunk in model.TransformNodeChunks)
        {
            // Transform node may be parent of a group node
            if (!shapeIDShapeInfoMap.TryGetValue(transformNodeChunk.ChildId, out ShapeInfo? shapeInfo) || shapeInfo == null)
            {
                continue;
            }

            // In this case the structure consists of a single shape.

            // Apply transformations
            shapeInfo.ApplyTransformationsToFrame(transformNodeChunk);

            // Set parent transform node name
            shapeInfo.SetParentTransformNodeNameAndIndex(transformNodeChunk.Name, transformNodeIndex++);

            // Add shapeInfo to map
            transformNodeChunkIDShapeInfoMap.Add(transformNodeChunk.Id, shapeInfo);
        }

        return (transformNodeChunkIDShapeInfoMap, transformNodeIndex);
    }

    private static Dictionary<int, int[]> GetGroupIDChildIDsMap(VoxModel model)
    {
        var groupIDChildIDsMap = new Dictionary<int, int[]>(model.GroupNodeChunks.Count);
        foreach (GroupNodeChunk? groupNodeChunk in model.GroupNodeChunks)
        {
            if (groupNodeChunk.Id == 1) // Ignore scene group
            {
                continue;
            }

            groupIDChildIDsMap.Add(groupNodeChunk.Id, groupNodeChunk.ChildIds);
        }

        return groupIDChildIDsMap;
    }

    private static void ProcessGroupTransformNodes(VoxModel model, Dictionary<int, int[]> groupIDChildIDsMap, Dictionary<int, ShapeInfo> transformNodeChunkIDShapeInfoMap, ref int transformNodeIndex)
    {
        foreach (TransformNodeChunk transformNodeChunk in model.TransformNodeChunks)
        {
            // Skip
            if (transformNodeChunk.Id == 0 || // Ignore scene transform node
                !groupIDChildIDsMap.TryGetValue(transformNodeChunk.ChildId, out int[]? childIDs) || childIDs == null)
            {
                continue;
            }

            // Combine shapes
            var parentShapeInfo = new ShapeInfo();
            foreach (int childID in childIDs)
            {
                if (!transformNodeChunkIDShapeInfoMap.TryGetValue(childID, out ShapeInfo? childShapeInfo) || childShapeInfo == null)
                {
                    continue;
                }

                // Combine shapes
                parentShapeInfo.AddChildShapeInfo(childShapeInfo);

                // Remove childShapeInfo from transformNodeChunkIDShapeInfoMap
                transformNodeChunkIDShapeInfoMap.Remove(childID);
            }

            // Apply transformations
            parentShapeInfo.ApplyTransformationsToExistingMagicaVoxelLocation(transformNodeChunk);
            foreach (ShapeInfo childShapeInfo in parentShapeInfo.ChildShapeInfos)
            {
                Matrix4x4Int transformMatrix = parentShapeInfo.TransformMatrix * childShapeInfo.TransformMatrix;
                childShapeInfo.ApplyTransformationsToFrame(ref transformMatrix);
            }

            // Set parent transform node name
            parentShapeInfo.SetParentTransformNodeNameAndIndex(transformNodeChunk.Name, transformNodeIndex++);

            // Add shapeInfo to map
            transformNodeChunkIDShapeInfoMap.Add(transformNodeChunk.Id, parentShapeInfo);
        }
    }

    // Sweep-and-prune on the X axis: O(N log N) sort + O(N + K) sweep where K is the number of X-overlapping pairs.
    private static void ValidateNoIntersectingBoundingBoxes(Dictionary<string, StructureInfo> structureNameStructureInfoMap)
    {
        // Sort structure name - structure info pairs by minX
        var structureNameStructureInfoArray = structureNameStructureInfoMap.ToArray();
        Array.Sort(structureNameStructureInfoArray, CompareStructureInfoByMinX);

        // Iterate over structure name - structure info pairs
        //
        // Compare each structure info to structure infos that overlap along the X axis
        for (int i = 0; i < structureNameStructureInfoArray.Length; i++)
        {
            Cuboid structure1Location = structureNameStructureInfoArray[i].Value.ShapeInfo.MagicaVoxelLocation;

            for (int j = i + 1; j < structureNameStructureInfoArray.Length; j++)
            {
                Cuboid structure2Location = structureNameStructureInfoArray[j].Value.ShapeInfo.MagicaVoxelLocation;

                // No more X overlap with structure1
                if (structure2Location.MinX >= structure1Location.MaxX) break;

                // No intersection
                if (!structure1Location.Intersects(structure2Location)) continue;

                // Intersection found
                string structure1Name = structureNameStructureInfoArray[i].Key;
                string structure2Name = structureNameStructureInfoArray[j].Key;
                throw new InvalidOperationException(
                    $"Structure bounding boxes must not intersect, but '{structure1Name}' and '{structure2Name}' overlap.\n" +
                    $"  {structure1Name}: MagicaVoxel bounds X [{structure1Location.MinX}, {structure1Location.MaxX}), Y [{structure1Location.MinY}, {structure1Location.MaxY}), Z [{structure1Location.MinZ}, {structure1Location.MaxZ})\n" +
                    $"  {structure2Name}: MagicaVoxel bounds X [{structure2Location.MinX}, {structure2Location.MaxX}), Y [{structure2Location.MinY}, {structure2Location.MaxY}), Z [{structure2Location.MinZ}, {structure2Location.MaxZ})\n" +
                    "Ensure top-level models/groups in MagicaVoxel do not overlap.");
            }
        }
    }

    private static int CompareStructureInfoByMinX(KeyValuePair<string, StructureInfo> structureNameStructureInfo1, KeyValuePair<string, StructureInfo> structureNameStructureInfo2)
    {
        return structureNameStructureInfo1.Value.ShapeInfo.MagicaVoxelLocation.MinX.CompareTo(structureNameStructureInfo2.Value.ShapeInfo.MagicaVoxelLocation.MinX);
    }

    private static Dictionary<string, StructureInfo> CreateStructureInfos(Dictionary<int, ShapeInfo> transformNodeChunkIDShapeInfoMap)
    {
        var structureNameStructureInfoMap = new Dictionary<string, StructureInfo>();
        int structureIndex = 0;
        foreach (ShapeInfo shapeInfo in transformNodeChunkIDShapeInfoMap.Values)
        {
            if (shapeInfo.PictoriaLocation.XLength > 512 ||
                shapeInfo.PictoriaLocation.YLength > 512 ||
                shapeInfo.PictoriaLocation.ZLength > 512)
            {
                Cuboid location = shapeInfo.PictoriaLocation;
                throw new InvalidOperationException($"Structure '{shapeInfo.ParentTransformNodeName}' (index {structureIndex}) exceeds 512 in at least one dimension.\n" +
                    $"  PictoriaLocation: X [{location.MinX}, {location.MaxX}) = {location.XLength}, Y [{location.MinY}, {location.MaxY}) = {location.YLength}, Z [{location.MinZ}, {location.MaxZ}) = {location.ZLength}");
            }

            (string structureName, VolumeType volumeType) = GetStructureNameAndVolumeType(shapeInfo, structureIndex++);

            var structureInfo = new StructureInfo(shapeInfo, structureName, volumeType);

            structureNameStructureInfoMap.Add(structureName, structureInfo);
        }
        return structureNameStructureInfoMap;
    }

    // Get structure name and volume type from shapeInfo.ParentTransformNodeName and shapeInfo.ParentTransformNodeIndex.
    //
    // shapeInfo.ParentTransformNodeName can be an empty string, "<volume type as a string>", "<shape name>" or "<shape name>_<volume type as a string>".
    //
    // Volume type: in cases where <volume type as a string> is not specified, volumeType is VolumeType.Cuboid. Otherwise, it is whatever is specified.
    //
    // Name is always "structure<shapeInfo.ParentTransformNodeIndex>".
    static (string name, VolumeType volumeType) GetStructureNameAndVolumeType(ShapeInfo shapeInfo, int structureIndex)
    {
        if (shapeInfo.ParentTransformNodeName == null)
        {
            throw new Exception("ParentTransformNodeName cannot be null");
        }

        // Determine structure name and volume type
        string structureName = $"structure{structureIndex}";

        // Validate structure name (should always pass for auto-generated names, but guards against future regressions)
        string? structureNameError = NameValidationService.Validate(structureName, "Structure");
        if (structureNameError != null) throw new InvalidOperationException(structureNameError);

        VolumeType volumeType = VolumeType.Cuboid;

        string lastSegment = shapeInfo.ParentTransformNodeName.Split('_')[^1];
        if (!string.IsNullOrWhiteSpace(lastSegment) &&
            !char.IsDigit(lastSegment[0]) &&
            Enum.TryParse(lastSegment, true, out VolumeType parsedVolumeType) &&
            Enum.IsDefined(parsedVolumeType))
        {
            volumeType = parsedVolumeType;
        }

        return (structureName, volumeType);
    }
}