using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using System.Text;
using FileToVoxCore.Schematics.Tools;

namespace Vox2Pictoria;

// We could save a couple of seconds / build if we combine this class with StructureObjService, specifically the AddVerticesAndFacesForShape methods. But the convenience of having a separate method outweighs the couple seconds speed up.
public class OccludedFacesObjService
{
    public static async Task GenerateOccludedFacesObjsAsync(Dictionary<string, StructureInfo> structureNameStructureInfoMap,
        ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
        Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap, Options options)
    {
        Console.WriteLine("Generating occluded faces objs...");

        // Generate structure objs
        DateTime currentTime = DateTime.Now;
        await Parallel.ForEachAsync(structureNameStructureInfoMap.Values, (structureInfo, CancellationToken) => GenerateOccludedFacesObjAsync(structureInfo, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
            voxelFrameVisibleVoxelInfoMap, options.ObjOutputDirectory));
        Console.WriteLine($"Occluded faces obj generation duration: {(DateTime.Now - currentTime).TotalSeconds} s");
    }

    private static async ValueTask GenerateOccludedFacesObjAsync(StructureInfo structureInfo, ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
        Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap, string outputDirectory)
    {
        GeneralObjInfo objInfo = new();

        // Create obj info
        if (structureInfo.ShapeInfo.ChildShapeInfos.Count == 0)
        {
            AddVerticesAndFacesForShape(structureInfo.ShapeInfo, null, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, voxelFrameVisibleVoxelInfoMap, null, ref objInfo);
        }
        else
        {
            object objInfoLock = new();
            Parallel.ForEach(structureInfo.ShapeInfo.ChildShapeInfos, childShapeInfo => AddVerticesAndFacesForShape(childShapeInfo, structureInfo.ShapeInfo, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
                voxelFrameVisibleVoxelInfoMap, objInfoLock, ref objInfo));
        }

        // No occluded faces
        if (objInfo.VertexListNumberMap.Count == 0)
        {
            return;
        }

        // Generate obj content
        StringBuilder stringBuilder = new();
        GenerateObjContent(stringBuilder, ref objInfo);

        // Write obj file
        //
        // <outputDirectory>/<structureInfo.Name>_occludedFaces.obj
        string objPath = Path.Combine(outputDirectory, structureInfo.Name + "_occludedFaces.obj");
        await File.WriteAllTextAsync(objPath, stringBuilder.ToString());
        Console.WriteLine($"Obj generated for occluded faces of structure '{structureInfo.Name}' at path: {objPath}");
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private static void AddVerticesAndFacesForShape(ShapeInfo shapeInfo, ShapeInfo? parentShapeInfo, ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
        Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap, object? objInfoLock, ref GeneralObjInfo target)
    {
        FrameInfo? frameInfo = shapeInfo.FrameInfo;
        if (frameInfo == null || frameInfo.VoxelFrameIndex < 0)
        {
            throw new InvalidOperationException("FrameInfo should not be null and VoxelFrameIndex of FrameInfo belonging to structure with only one shape must not be less than 0");
        }

        Dictionary<int, VisibleVoxelInfo> voxelIndexVisibleVoxelInfoMap = voxelFrameVisibleVoxelInfoMap[frameInfo.VoxelFrameIndex];
        Matrix4x4Int transformMatrix = shapeInfo.TransformMatrix;

        // Generate vertices and faces
        // Iterate through the voxel data
        float objMinX, objMinY, objMinZ, objMaxX, objMaxY, objMaxZ;
        Vector3 voxelVertices0, voxelVertices1, voxelVertices2, voxelVertices3, voxelVertices4, voxelVertices5, voxelVertices6, voxelVertices7;
        foreach (KeyValuePair<int, VisibleVoxelInfo> voxelIndexVisibleVoxelInfo in voxelIndexVisibleVoxelInfoMap)
        {
            int index = voxelIndexVisibleVoxelInfo.Key;

            // Get transformed voxel bounding box
            //
            // Note that minX, minY and minZ correspond to voxel coordinate x, y and z respectively
            Cuboid untransformedVoxelBoundingBox = voxelIndexVisibleVoxelInfo.Value.UntransformedVoxelBoundingBox;
            Cuboid transformedVoxelBoundingBox = VoxelCoordinatesService.UntransformedToTransformedBoundingBox(ref untransformedVoxelBoundingBox, ref transformMatrix);

            // Convert transformed voxel bounding box coordinates to obj coordinates
            objMinX = (float)Math.Round(transformedVoxelBoundingBox.MinX / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMinY = (float)Math.Round(transformedVoxelBoundingBox.MinY / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMinZ = (float)Math.Round(transformedVoxelBoundingBox.MinZ / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMaxX = (float)Math.Round(transformedVoxelBoundingBox.MaxX / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMaxY = (float)Math.Round(transformedVoxelBoundingBox.MaxY / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMaxZ = (float)Math.Round(transformedVoxelBoundingBox.MaxZ / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);

            // Get vertices
            //
            // Note that they are ordered like so: starts from the vertex at min obj x, y and z, then goes around the lower square (// to the x-y plane), then moves to the min obj x and y at max z and goes around the upper square.
            voxelVertices0 = new Vector3 { X = objMinX, Y = objMinY, Z = objMinZ };
            voxelVertices1 = new Vector3 { X = objMaxX, Y = objMinY, Z = objMinZ };
            voxelVertices2 = new Vector3 { X = objMaxX, Y = objMaxY, Z = objMinZ };
            voxelVertices3 = new Vector3 { X = objMinX, Y = objMaxY, Z = objMinZ };
            voxelVertices4 = new Vector3 { X = objMinX, Y = objMinY, Z = objMaxZ };
            voxelVertices5 = new Vector3 { X = objMaxX, Y = objMinY, Z = objMaxZ };
            voxelVertices6 = new Vector3 { X = objMaxX, Y = objMaxY, Z = objMaxZ };
            voxelVertices7 = new Vector3 { X = objMinX, Y = objMaxY, Z = objMaxZ };

            // Get frame face visibility
            //
            // This is the visibility of the face before considering other shapes (frames) and structures
            CuboidFaceVisibilities frameFaceVisibility = transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap[new Vector3Int(transformedVoxelBoundingBox.MinX, transformedVoxelBoundingBox.MinY,
                transformedVoxelBoundingBox.MinZ)]; // Should not throw

            // TODO how do we ignore if shape is from same structure?

            // Add vertices and faces
            //
            // Note that if within the frame, we've already ascertained that the voxel is obscurred in a direction, we can skip it. Also, if voxel is not at edge of frame, we do not need to check whether 
            // it is obscured by an adjacent shape.
            if (frameFaceVisibility.MinusX == FaceVisibility.VisibleAtFrameEdge &&
                (parentShapeInfo == null || transformedVoxelBoundingBox.MinX == parentShapeInfo.MagicaVoxelLocation.MinX) &&
                SharedObjService.CheckIfFaceObscuredByAdjacentShape(transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, transformedVoxelBoundingBox.MinX - 1, transformedVoxelBoundingBox.MinY, transformedVoxelBoundingBox.MinZ)) // -x face
            {
                SharedObjService.AddVerticesAndFacesForDirection(ref target, ref voxelVertices0, ref voxelVertices4, ref voxelVertices7, ref voxelVertices3, 0, 0, objInfoLock);
            }
            if (frameFaceVisibility.MinusY == FaceVisibility.VisibleAtFrameEdge &&
                (parentShapeInfo == null || transformedVoxelBoundingBox.MinY == parentShapeInfo.MagicaVoxelLocation.MinY) &&
                SharedObjService.CheckIfFaceObscuredByAdjacentShape(transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, transformedVoxelBoundingBox.MinX, transformedVoxelBoundingBox.MinY - 1, transformedVoxelBoundingBox.MinZ)) // -y face
            {
                SharedObjService.AddVerticesAndFacesForDirection(ref target, ref voxelVertices0, ref voxelVertices1, ref voxelVertices5, ref voxelVertices4, 0, 0, objInfoLock);
            }
            if (frameFaceVisibility.PlusZ == FaceVisibility.VisibleAtFrameEdge &&
                (parentShapeInfo == null || transformedVoxelBoundingBox.MaxZ == parentShapeInfo.MagicaVoxelLocation.MaxZ) &&
                SharedObjService.CheckIfFaceObscuredByAdjacentShape(transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, transformedVoxelBoundingBox.MinX, transformedVoxelBoundingBox.MinY, transformedVoxelBoundingBox.MaxZ)) // +z face
            {
                SharedObjService.AddVerticesAndFacesForDirection(ref target, ref voxelVertices4, ref voxelVertices5, ref voxelVertices6, ref voxelVertices7, 0, 0, objInfoLock);
            }
        }
    }

    private static void GenerateObjContent(StringBuilder stringBuilder, ref GeneralObjInfo objInfo)
    {
        // Material
        stringBuilder.AppendLine("# material");
        stringBuilder.AppendLine("mtllib shared.mtl");

        // Vertices
        stringBuilder.AppendLine("\n# vertices");
        foreach (Vector3 vertex in objInfo.VertexListNumberMap.Keys)
        {
            // Blender swaps and negates some axes when it imports objs (https://projects.blender.org/blender/blender/issues/31693). We need to compensate for that here.
            stringBuilder.Append("v ");
            stringBuilder.Append(vertex.X);
            stringBuilder.Append(' ');
            stringBuilder.Append(vertex.Z);
            stringBuilder.Append(' ');
            stringBuilder.Append(-vertex.Y);
            stringBuilder.AppendLine();
        }

        // Faces
        stringBuilder.AppendLine("\n# faces");
        stringBuilder.AppendLine("usemtl red_mtl");
        foreach (QuadFace face in objInfo.QuadFaces)
        {
            // Triangle 1
            stringBuilder.Append("f ");
            stringBuilder.Append(face.VertexIndex1);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex2);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex3);
            stringBuilder.AppendLine();

            // Triangle 2
            stringBuilder.Append("f ");
            stringBuilder.Append(face.VertexIndex1);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex3);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex4);
            stringBuilder.AppendLine();
        }
    }
}