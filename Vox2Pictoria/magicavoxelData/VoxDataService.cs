using FileToVoxCore.Vox;
using FileToVoxCore.Vox.Chunks;

namespace Vox2Pictoria;

public class VoxDataService
{
    // Resources:
    //
    // - https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox-extension.txt
    // - https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox.txt
    public static async Task<Dictionary<string, StructureInfo>> ExtractStructureDataFromVox(VoxModel model, Options options)
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

        // Set structure image dimensions
        SetStructureImageDimensions(structureNameStructureInfoMap);

        // Set Pictoria locations
        SetPictoriaLocations(structureNameStructureInfoMap, options);

        return structureNameStructureInfoMap;
    }

    static void SetPictoriaLocations(Dictionary<string, StructureInfo> structureNameStructureInfoMap, Options options)
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

        // Offset structures so the bounding mins are at the property mins
        (int propertyMinCartesianLocationX, int propertyMinCartesianLocationZ) = CoordinatesService.TileXZToMinCartesianXZ(options.PropertyMinTileX, options.PropertyMinTileZ);
        int xOffset = propertyMinCartesianLocationX - (int)minX;
        int zOffset = propertyMinCartesianLocationZ - (int)minZ;
        Console.WriteLine($"Scene to Pictoria offsets: X Offset: {xOffset}, Z Offset: {zOffset}");
        foreach (StructureInfo structureInfo in structureNameStructureInfoMap.Values)
        {
            structureInfo.ShapeInfo.PictoriaLocation.Offset(xOffset, zOffset);
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
                throw new InvalidOperationException("PictoriaDimension exceeds 512");
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
        VolumeType volumeType = VolumeType.Cuboid;

        if (!string.IsNullOrWhiteSpace(shapeInfo.ParentTransformNodeName) &&
            Enum.TryParse(shapeInfo.ParentTransformNodeName.Split('_')[^1], true, out VolumeType parsedVolumeType))
        {
            volumeType = parsedVolumeType;
        }

        return (structureName, volumeType);
    }
}