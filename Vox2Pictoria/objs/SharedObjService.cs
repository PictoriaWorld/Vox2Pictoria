using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using FileToVoxCore.Schematics.Tools;

namespace Vox2Pictoria;

public class SharedObjService
{
    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static void AddVerticesAndFacesForDirection(ref GeneralObjInfo objInfo, ref Vector3 v1, ref Vector3 v2, ref Vector3 v3, ref Vector3 v4, int texCoordsNumber = 0, int normalNumber = 0, object? objInfoLock = null)
    {
        bool lockTaken = false;
        try
        {
            // We have to lock because VertexListNumberMap and QuadFaces are not thread safe
            if (objInfoLock != null) Monitor.Enter(objInfoLock, ref lockTaken);

            // Add vertices
            Dictionary<Vector3, int> vertexListNumberMap = objInfo.VertexListNumberMap;
            int indexV1 = TryAddVertexAndGetNumber(vertexListNumberMap, ref v1);
            int indexV2 = TryAddVertexAndGetNumber(vertexListNumberMap, ref v2);
            int indexV3 = TryAddVertexAndGetNumber(vertexListNumberMap, ref v3);
            int indexV4 = TryAddVertexAndGetNumber(vertexListNumberMap, ref v4);

            // Add faces
            //
            // Note that each voxel face corresponds to two triangular obj faces
            objInfo.QuadFaces.Add(new QuadFace { VertexIndex1 = indexV1, VertexIndex2 = indexV2, VertexIndex3 = indexV3, VertexIndex4 = indexV4, TextureCoordsNumber = texCoordsNumber, NormalNumber = normalNumber });
        }
        finally
        {
            if (lockTaken) Monitor.Exit(objInfoLock!);
        }
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static int TryAddVertexAndGetNumber(Dictionary<Vector3, int> targetVertexListNumberMap, ref Vector3 vertex)
    {
        if (targetVertexListNumberMap.TryGetValue(vertex, out int existingListNumber))
        {
            return existingListNumber;
        }
        else
        {
            return targetVertexListNumberMap[vertex] = targetVertexListNumberMap.Count + 1;
        }
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static bool CheckIfFaceObscuredByAdjacentShape(ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, int neighbourTransformedMinX, int neighbourTransformedMinY,
        int neighbourTransformedMinZ)
    {
        // Visible if neighbour is empty
        return transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap.ContainsKey(new Vector3Int(neighbourTransformedMinX, neighbourTransformedMinY, neighbourTransformedMinZ));
    }
}