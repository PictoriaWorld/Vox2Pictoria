using System.Text;
using FileToVoxCore.Schematics.Tools;

namespace Vox2Pictoria;

public class VolumeObjService
{
    public static async Task GenerateVolumeObjsAsync(Dictionary<string, StructureInfo> structureNameStructureInfoMap, string outputDirectory)
    {
        Console.WriteLine("Generating volume objs...");

        // Generate volume objs
        DateTime currentTime = DateTime.Now;
        await Parallel.ForEachAsync(structureNameStructureInfoMap.Values, (structureInfo, CancellationToken) => GenerateVolumeObjAsync(structureInfo, outputDirectory));
        Console.WriteLine($"Volume obj generation duration: {(DateTime.Now - currentTime).TotalSeconds} s");
    }

    static async ValueTask GenerateVolumeObjAsync(StructureInfo structureInfo, string outputDirectory)
    {
        StringBuilder stringBuilder = new();
        VolumeObjInfo objInfo = new();

        // Get obj min/max x/y/z
        float minX = (float)Math.Round(structureInfo.ShapeInfo.MagicaVoxelLocation.MinX / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
        float maxX = (float)Math.Round(structureInfo.ShapeInfo.MagicaVoxelLocation.MaxX / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
        float minY = (float)Math.Round(structureInfo.ShapeInfo.MagicaVoxelLocation.MinY / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
        float maxY = (float)Math.Round(structureInfo.ShapeInfo.MagicaVoxelLocation.MaxY / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
        float minZ = (float)Math.Round(structureInfo.ShapeInfo.MagicaVoxelLocation.MinZ / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
        float maxZ = (float)Math.Round(structureInfo.ShapeInfo.MagicaVoxelLocation.MaxZ / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);

        // Create obj info
        //
        // Note that that obj info creation methods compensate for different coordinate systems: In magica voxel, the z-axis is the vertical axis and all axes point away from the screen. In Pictoria,
        // the y-axis is the vertical axis and the x and z-axes point toward the screen. Hence a minus-x prism in pictoria is a "plus-y prism" in magica voxel. In the create methods,
        // when we mention axes, we're referring to pictoria axes.
        switch (structureInfo.VolumeType)
        {
            case VolumeType.Cuboid:
                CreateCuboidVerticesAndFaces(minX, minY, minZ, maxX, maxY, maxZ, ref objInfo);
                break;
            case VolumeType.MinusXPrism:
                CreateMinusXPrismVerticesAndFaces(minX, minY, minZ, maxX, maxY, maxZ, ref objInfo);
                break;
            case VolumeType.MinusZPrism:
                CreateMinusZPrismVerticesAndFaces(minX, minY, minZ, maxX, maxY, maxZ, ref objInfo); // x and z axes are swapped, and the x axis is flipped
                break;
            case VolumeType.PlusXPrism:
                CreatePlusXPrismVerticesAndFaces(minX, minY, minZ, maxX, maxY, maxZ, ref objInfo); // x and z axes are swapped
                break;
            case VolumeType.PlusZPrism:
                CreatePlusZPrismVerticesAndFaces(minX, minY, minZ, maxX, maxY, maxZ, ref objInfo); // x and z axes are swapped, and the x axis is flipped
                break;
            default:
                throw new InvalidOperationException($"Unsupported volume type: {structureInfo.VolumeType}");
        }

        // Generate obj content
        stringBuilder.Clear();
        GenerateObjContent(stringBuilder, ref objInfo);

        // Write obj file
        //
        // <outputDirectory>/<structureInfo.Name>_volume.obj
        string objPath = Path.Combine(outputDirectory, structureInfo.Name + "_volume.obj");
        await File.WriteAllTextAsync(objPath, stringBuilder.ToString());
        Console.WriteLine($"Volume obj generated for structure '{structureInfo.Name}' at path: {objPath}");
    }

    private static void CreateMinusXPrismVerticesAndFaces(float minX, float minY, float minZ, float maxX, float maxY, float maxZ, ref VolumeObjInfo objInfo)
    {
        // Create obj vertices for pictoria minus-x prism
        //
        // Lower rectangle p1x, p1y, p1z, p2x, p2y... p4x, p4y, p4z. Upper rectangle p5x, p5y, p5z, p6x, p6y... p8x, p8y, p8z
        // Where p1s are at min x, y, z of their respective rectangles and subsequent points are ordered clockwise from the user's perspective
        objInfo.VertexList.Add(new Vector3(maxX, maxY, minZ)); // Vertex 1 - point 1
        objInfo.VertexList.Add(new Vector3(maxX, minY, minZ)); // Vertex 2 - point 2
        objInfo.VertexList.Add(new Vector3(minX, minY, minZ)); // Vertex 3 - point 3
        objInfo.VertexList.Add(new Vector3(minX, maxY, minZ)); // Vertex 4 - point 4
        objInfo.VertexList.Add(new Vector3(maxX, maxY, maxZ)); // Vertex 5 - point 5
        objInfo.VertexList.Add(new Vector3(minX, maxY, maxZ)); // Vertex 6 - point 8

        // Create faces for the minus-x prism, breaking quads into tris
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 2, VertexIndex3 = 3 }); // -y face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 3, VertexIndex3 = 4 }); // -y face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 2, VertexIndex2 = 3, VertexIndex3 = 6 }); // +y face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 2, VertexIndex2 = 6, VertexIndex3 = 5 }); // +y face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 5, VertexIndex3 = 6 }); // -x face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 6, VertexIndex3 = 4 }); // -x face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 5, VertexIndex3 = 2 }); // -z face
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 4, VertexIndex2 = 6, VertexIndex3 = 3 }); // +z face
    }

    private static void CreateMinusZPrismVerticesAndFaces(float minX, float minY, float minZ, float maxX, float maxY, float maxZ, ref VolumeObjInfo objInfo)
    {
        // Create obj vertices for pictoria minus-z prism
        //
        // Lower rectangle p1x, p1y, p1z, p2x, p2y... p4x, p4y, p4z. Upper rectangle p5x, p5y, p5z, p6x, p6y... p8x, p8y, p8z
        // Where p1s are at min x, y, z of their respective rectangles and subsequent points are ordered clockwise from the user's perspective
        objInfo.VertexList.Add(new Vector3(maxX, maxY, minZ)); // Vertex 1 - point 1
        objInfo.VertexList.Add(new Vector3(maxX, minY, minZ)); // Vertex 2 - point 2
        objInfo.VertexList.Add(new Vector3(minX, minY, minZ)); // Vertex 3 - point 3
        objInfo.VertexList.Add(new Vector3(minX, maxY, minZ)); // Vertex 4 - point 4
        objInfo.VertexList.Add(new Vector3(maxX, maxY, maxZ)); // Vertex 5 - point 5
        objInfo.VertexList.Add(new Vector3(maxX, minY, maxZ)); // Vertex 6 - point 6

        // Create faces for the minus-z prism, breaking quads into tris
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 2, VertexIndex3 = 3 }); // -y face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 3, VertexIndex3 = 4 }); // -y face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 3, VertexIndex2 = 4, VertexIndex3 = 5 }); // +y face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 3, VertexIndex2 = 5, VertexIndex3 = 6 }); // +y face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 6, VertexIndex3 = 2 }); // -z face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 5, VertexIndex3 = 6 }); // -z face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 4, VertexIndex3 = 5 }); // -x face
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 2, VertexIndex2 = 3, VertexIndex3 = 6 }); // +x face
    }

    private static void CreatePlusXPrismVerticesAndFaces(float minX, float minY, float minZ, float maxX, float maxY, float maxZ, ref VolumeObjInfo objInfo)
    {
        // Create obj vertices for pictoria plus-x prism
        //
        // Lower rectangle p1x, p1y, p1z, p2x, p2y... p4x, p4y, p4z. upper rectangle p5x, p5y, p5z, p6x, p6y... p8x, p8y, p8z
        // Where p1s are at min x, y, z of their respective rectangles and subsequent points are ordered clockwise from the user's perspective
        objInfo.VertexList.Add(new Vector3(maxX, maxY, minZ)); // Vertex 1 - point 1
        objInfo.VertexList.Add(new Vector3(maxX, minY, minZ)); // Vertex 2 - point 2
        objInfo.VertexList.Add(new Vector3(minX, minY, minZ)); // Vertex 3 - point 3
        objInfo.VertexList.Add(new Vector3(minX, maxY, minZ)); // Vertex 4 - point 4
        objInfo.VertexList.Add(new Vector3(maxX, minY, maxZ)); // Vertex 5 - point 6
        objInfo.VertexList.Add(new Vector3(minX, minY, maxZ)); // Vertex 6 - point 7

        // Create faces for the plus-x prism, breaking quads into tris
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 2, VertexIndex3 = 3 }); // -y face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 3, VertexIndex3 = 4 }); // -y face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 5, VertexIndex3 = 6 }); // +y face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 6, VertexIndex3 = 4 }); // +y face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 2, VertexIndex2 = 3, VertexIndex3 = 6 }); // +x face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 2, VertexIndex2 = 6, VertexIndex3 = 5 }); // +x face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 5, VertexIndex3 = 2 }); // -z face
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 4, VertexIndex2 = 6, VertexIndex3 = 3 }); // +z face
    }

    private static void CreatePlusZPrismVerticesAndFaces(float minX, float minY, float minZ, float maxX, float maxY, float maxZ, ref VolumeObjInfo objInfo)
    {
        // Create obj vertices for pictoria plus-z prism
        //
        // Lower rectangle p1x, p1y, p1z, p2x, p2y... p4x, p4y, p4z. upper rectangle p5x, p5y, p5z, p6x, p6y... p8x, p8y, p8z
        // Where p1s are at min x, y, z of their respective rectangles and subsequent points are ordered clockwise from the user's perspective
        objInfo.VertexList.Add(new Vector3(maxX, maxY, minZ)); // Vertex 1 - point 1
        objInfo.VertexList.Add(new Vector3(maxX, minY, minZ)); // Vertex 2 - point 2
        objInfo.VertexList.Add(new Vector3(minX, minY, minZ)); // Vertex 3 - point 3
        objInfo.VertexList.Add(new Vector3(minX, maxY, minZ)); // Vertex 4 - point 4
        objInfo.VertexList.Add(new Vector3(minX, minY, maxZ)); // Vertex 5 - point 7
        objInfo.VertexList.Add(new Vector3(minX, maxY, maxZ)); // Vertex 6 - point 8

        // Create faces for the plus-z prism, breaking quads into tris
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 2, VertexIndex3 = 3 }); // -y face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 3, VertexIndex3 = 4 }); // -y face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 2, VertexIndex3 = 5 }); // +y face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 5, VertexIndex3 = 6 }); // +y face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 3, VertexIndex2 = 4, VertexIndex3 = 6 }); // +z face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 3, VertexIndex2 = 6, VertexIndex3 = 5 }); // +z face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 4, VertexIndex3 = 6 }); // -x face
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 2, VertexIndex2 = 3, VertexIndex3 = 5 }); // +x face
    }

    private static void CreateCuboidVerticesAndFaces(float minX, float minY, float minZ, float maxX, float maxY, float maxZ, ref VolumeObjInfo objInfo)
    {
        // Create vertices
        objInfo.VertexList.Add(new Vector3(maxX, maxY, minZ)); // Vertex 1 - point 1
        objInfo.VertexList.Add(new Vector3(maxX, minY, minZ)); // Vertex 2 - point 2
        objInfo.VertexList.Add(new Vector3(minX, minY, minZ)); // Vertex 3 - point 3
        objInfo.VertexList.Add(new Vector3(minX, maxY, minZ)); // Vertex 4 - point 4
        objInfo.VertexList.Add(new Vector3(maxX, maxY, maxZ)); // Vertex 5 - point 5
        objInfo.VertexList.Add(new Vector3(maxX, minY, maxZ)); // Vertex 6 - point 6
        objInfo.VertexList.Add(new Vector3(minX, minY, maxZ)); // Vertex 7 - point 7
        objInfo.VertexList.Add(new Vector3(minX, maxY, maxZ)); // Vertex 8 - point 8

        // Create faces, breaking quads into tris
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 2, VertexIndex3 = 3 }); // Bottom face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 3, VertexIndex3 = 4 }); // Bottom face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 5, VertexIndex2 = 8, VertexIndex3 = 7 }); // Top face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 5, VertexIndex2 = 7, VertexIndex3 = 6 }); // Top face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 5, VertexIndex3 = 6 }); // Front face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 1, VertexIndex2 = 6, VertexIndex3 = 2 }); // Front face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 2, VertexIndex2 = 6, VertexIndex3 = 7 }); // Right face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 2, VertexIndex2 = 7, VertexIndex3 = 3 }); // Right face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 3, VertexIndex2 = 7, VertexIndex3 = 8 }); // Back face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 3, VertexIndex2 = 8, VertexIndex3 = 4 }); // Back face, part 2
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 5, VertexIndex2 = 1, VertexIndex3 = 4 }); // Left face, part 1
        objInfo.TriFaces.Add(new TriFace { VertexIndex1 = 5, VertexIndex2 = 4, VertexIndex3 = 8 }); // Left face, part 2
    }

    private static void GenerateObjContent(StringBuilder stringBuilder, ref VolumeObjInfo objInfo)
    {
        // Material
        stringBuilder.AppendLine("# material");
        stringBuilder.AppendLine("mtllib shared.mtl");

        // Vertices
        stringBuilder.AppendLine("\n# vertices");
        foreach (Vector3 vertex in objInfo.VertexList)
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
        foreach (TriFace face in objInfo.TriFaces)
        {
            stringBuilder.Append("f ");
            stringBuilder.Append(face.VertexIndex1);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex2);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex3);
            stringBuilder.AppendLine();
        }
    }
}